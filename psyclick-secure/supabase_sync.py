"""
supabase_sync.py — PsyClick offline-first cloud sync (Supabase Postgres).

The app always works on the local SQLite database; nothing here is needed to
assess, score or report. When a sync connection is configured and the
computer is online, a background thread:

  1. uploads changed accounts (newest change wins, keyed by clinician ID),
  2. uploads deletions and new sessions (keyed by a device-independent uid),
  3. downloads everything other devices changed since the last download.

So any account can sign in on any device that has synced once, and sees its
own clients there. Syncing wakes immediately after a change and otherwise
every 60 s; it simply waits while offline.

Configuration (config.json next to the app, or %APPDATA%\\PsyClick\\config.json):
    {"sync_url": "postgresql://psyclick_app.<project>:<password>@<host>:5432/postgres"}
The role in sync_url only needs the psyclick schema created by
scripts/setup_cloud_sync.py; it cannot read anything else in the project.
"""

import json
import logging
import os
import socket
import sys
import threading
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter('[PsyClick Sync] %(levelname)s: %(message)s'))
logger.addHandler(_handler)

SCHEMA = os.environ.get("PSYCLICK_SYNC_SCHEMA", "psyclick")   # tests use a scratch schema
_SYNC_INTERVAL = 60      # seconds between routine sync attempts
_CONN_TIMEOUT  = 5       # seconds for the connectivity probe and connect
_PULL_OVERLAP  = 200     # re-read recent changes in case a slower upload committed late

_sync_status = {
    "enabled":   False,   # a sync connection is configured
    "connected": False,   # last attempt reached the cloud
    "last_sync": None,    # local time of the last complete sync
    "pending":   0,       # local changes waiting for upload
    "error":     None,
    "syncing":   False,
}
_lock        = threading.Lock()     # one sync at a time
_wake        = threading.Event()
_stop_event  = threading.Event()
_sync_thread = None


# ── Configuration ─────────────────────────────────────────────────────────────

def _config_paths():
    here = os.path.dirname(os.path.abspath(__file__))
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    paths = []
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            paths.append(os.path.join(sys._MEIPASS, 'config.json'))
        # Electron ships config.json in resources/, one level above the API folder
        paths += [os.path.join(exe_dir, 'config.json'), os.path.join(os.path.dirname(exe_dir), 'config.json')]
    else:
        paths.append(os.path.join(here, 'config.json'))
    paths += [os.path.join(appdata, 'PsyClickSecure', 'config.json'),
              os.path.join(appdata, 'PsyClick', 'config.json')]
    return paths


def _load_sync_url():
    override = os.environ.get('PSYCLICK_SYNC_URL')
    if override is not None:
        return override.strip() or None
    for path in _config_paths():
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8-sig') as fh:
                    url = (json.load(fh).get('sync_url') or '').strip()
                if url:
                    return url
        except Exception as exc:
            logger.warning(f'Could not read {path}: {exc}')
    return None


def _is_online(url):
    try:
        host = urlparse(url).hostname
        socket.getaddrinfo(host, urlparse(url).port or 5432)
        with socket.create_connection((host, urlparse(url).port or 5432), timeout=_CONN_TIMEOUT):
            return True
    except Exception:
        return False


def _connect(url):
    import psycopg2  # type: ignore
    return psycopg2.connect(url, connect_timeout=_CONN_TIMEOUT)


# ── One sync pass ─────────────────────────────────────────────────────────────

def _push_accounts(cur, db):
    for acc in db.get_dirty_accounts():
        cur.execute(f"""
            INSERT INTO {SCHEMA}.accounts
                (clinician_id, account_uid, name, password_hash, role, status, created_at, updated_at, server_seq)
            VALUES (%(clinician_id)s, %(account_uid)s, %(name)s, %(password_hash)s, %(role)s, %(status)s,
                    %(created_at)s, %(updated_at)s, nextval('{SCHEMA}.change_seq'))
            ON CONFLICT (clinician_id) DO UPDATE SET
                name = EXCLUDED.name, password_hash = EXCLUDED.password_hash, role = EXCLUDED.role,
                status = EXCLUDED.status, updated_at = EXCLUDED.updated_at,
                server_seq = nextval('{SCHEMA}.change_seq')
            WHERE {SCHEMA}.accounts.account_uid = EXCLUDED.account_uid
              AND {SCHEMA}.accounts.updated_at < EXCLUDED.updated_at
            RETURNING account_uid""", acc)
        if cur.fetchone() is None:
            cur.execute(f"SELECT account_uid FROM {SCHEMA}.accounts WHERE clinician_id=%s", (acc["clinician_id"],))
            row = cur.fetchone()
            if row and row[0] != acc["account_uid"]:
                # Same ID made on two devices while offline: this one moves
                cur.execute(f"SELECT clinician_id FROM {SCHEMA}.accounts")
                new_id = db.reassign_clinician_id(acc["clinician_id"], [r[0] for r in cur.fetchall()])
                db.log_audit("security", "Account ID changed by sync",
                             f"{acc['name']}: {acc['clinician_id']} -> {new_id} (ID was taken on another device)")
                logger.warning(f"Account {acc['clinician_id']} moved to {new_id}: ID taken on another device")
                return True          # push again on the next pass with the new ID
        db.mark_account_synced(acc["clinician_id"], acc["updated_at"])
    return False


def _push_deletions(cur, db):
    for suid, deleted_at in db.get_pending_tombstones():
        cur.execute(f"""
            INSERT INTO {SCHEMA}.sessions (session_uid, clinician_id, data, deleted_at, server_seq)
            VALUES (%s, NULL, '{{}}'::jsonb, %s, nextval('{SCHEMA}.change_seq'))
            ON CONFLICT (session_uid) DO UPDATE SET
                data = '{{}}'::jsonb, deleted_at = EXCLUDED.deleted_at,
                server_seq = nextval('{SCHEMA}.change_seq')""", (suid, deleted_at))
        db.mark_tombstone_pushed(suid)


def _push_sessions(cur, db):
    while True:
        batch = db.get_unsynced_sessions(limit=50)
        if not batch:
            return
        for item in batch:
            data = item["data"]
            cur.execute(f"""
                INSERT INTO {SCHEMA}.sessions (session_uid, clinician_id, data, deleted_at, server_seq)
                VALUES (%s, %s, %s::jsonb, NULL, nextval('{SCHEMA}.change_seq'))
                ON CONFLICT (session_uid) DO NOTHING""",
                (data["session_uid"], data.get("clinician_id"), json.dumps(data, default=str)))
            db.mark_session_synced(item["session_id"])


def _pull(cur, db, accounts_only=False):
    since = int(db.get_sync_state("last_seq", "0") or 0)
    start = max(0, since - _PULL_OVERLAP)
    top = since
    cur.execute(f"""SELECT clinician_id, account_uid, name, password_hash, role, status, created_at,
                           updated_at, server_seq
                    FROM {SCHEMA}.accounts WHERE server_seq > %s ORDER BY server_seq""", (start,))
    for r in cur.fetchall():
        db.apply_remote_account({"clinician_id": r[0], "account_uid": r[1], "name": r[2], "password_hash": r[3],
                                 "role": r[4], "status": r[5], "created_at": r[6], "updated_at": r[7]})
        top = max(top, r[8])
    if accounts_only:
        return          # the shared watermark only moves once sessions are read too
    while True:
        cur.execute(f"""SELECT session_uid, data, deleted_at, server_seq FROM {SCHEMA}.sessions
                        WHERE server_seq > %s ORDER BY server_seq LIMIT 200""", (start,))
        rows = cur.fetchall()
        if not rows:
            break
        for suid, data, deleted_at, seq in rows:
            db.apply_remote_session(suid, data if isinstance(data, dict) else json.loads(data or "{}"),
                                    deleted_at.isoformat() if deleted_at else None)
            top = max(top, seq)
            start = seq
    db.set_sync_state("last_seq", top)


def _sync_once(url, pull_only=False, accounts_only=False):
    import database_manager as db
    with _lock:
        _sync_status['syncing'] = True
        try:
            conn = _connect(url)
            try:
                conn.autocommit = True
                cur = conn.cursor()
                if not pull_only:
                    # Pull accounts first so pushes see IDs taken elsewhere
                    _pull(cur, db)
                    while _push_accounts(cur, db):
                        pass
                    _push_deletions(cur, db)
                    _push_sessions(cur, db)
                _pull(cur, db, accounts_only=accounts_only)
            finally:
                conn.close()
            _sync_status.update(connected=True, error=None, last_sync=time.strftime('%Y-%m-%d %H:%M:%S'))
            return True
        except Exception as exc:
            _sync_status.update(connected=False, error=str(exc).strip().splitlines()[0][:200])
            logger.error(f'Sync failed: {exc}')
            return False
        finally:
            _sync_status['syncing'] = False
            _sync_status['pending'] = db.get_unsynced_count()


# ── Background service ────────────────────────────────────────────────────────

def _sync_loop():
    _stop_event.wait(3)   # let the API and database start first
    while not _stop_event.is_set():
        try:
            url = _load_sync_url()
            _sync_status['enabled'] = bool(url)
            if url:
                if _is_online(url):
                    _sync_once(url)
                else:
                    _sync_status['connected'] = False
                    from database_manager import get_unsynced_count
                    _sync_status['pending'] = get_unsynced_count()
        except Exception as exc:
            logger.error(f'Sync loop error: {exc}')
        _wake.wait(_SYNC_INTERVAL)
        _wake.clear()


def start_sync_service():
    """Start the background sync thread. Safe to call more than once."""
    global _sync_thread
    if _sync_thread and _sync_thread.is_alive():
        return
    _stop_event.clear()
    _sync_thread = threading.Thread(target=_sync_loop, daemon=True, name='psyclick-sync')
    _sync_thread.start()
    logger.info('Background sync service started.')


def stop_sync_service():
    _stop_event.set()
    _wake.set()


def request_sync():
    """Sync soon (after a local change). Never blocks."""
    _wake.set()


def pull_now(timeout=8):
    """
    Download accounts now, waiting at most `timeout` seconds, then let the
    background sync bring the sessions. Used before sign-in or first-time
    setup on a device that has not seen an account yet, so it stays quick.
    Returns True when the accounts arrived.
    """
    url = _load_sync_url()
    if not url or not _is_online(url):
        return False
    done = {}
    t = threading.Thread(target=lambda: done.setdefault('ok', _sync_once(url, pull_only=True, accounts_only=True)),
                         daemon=True)
    t.start()
    t.join(timeout)
    request_sync()
    return bool(done.get('ok'))


def pull_sessions_now(timeout=6):
    """Download accounts and sessions now (e.g. before suggesting a new client
    code, so codes used on other devices are known). Returns True when done."""
    url = _load_sync_url()
    if not url or not _is_online(url):
        return False
    done = {}
    t = threading.Thread(target=lambda: done.setdefault('ok', _sync_once(url, pull_only=True)), daemon=True)
    t.start()
    t.join(timeout)
    return bool(done.get('ok'))


def get_sync_status():
    try:
        from database_manager import get_unsynced_count
        _sync_status['pending'] = get_unsynced_count()
    except Exception:
        pass
    _sync_status['enabled'] = bool(_load_sync_url())
    return dict(_sync_status)


def trigger_sync_now():
    """Attempt an immediate full sync (blocking). Returns the status."""
    url = _load_sync_url()
    if url and _is_online(url):
        _sync_once(url)
    elif url:
        _sync_status['connected'] = False
    return get_sync_status()
