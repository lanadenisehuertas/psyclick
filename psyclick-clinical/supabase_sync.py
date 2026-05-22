"""
supabase_sync.py — PsyClick Clinical Edition: Background Cloud Sync

Offline-first design:
  - The app runs 100% on local SQLite with no internet requirement.
  - When Supabase is configured AND internet is available, unsynced
    session records are uploaded automatically in the background.
  - Safe no-op when supabase_url / supabase_key are absent from config.json.

config.json fields used (all optional):
  {
    "supabase_url": "https://xxxx.supabase.co",
    "supabase_key": "<anon-or-service-role-key>"
  }
"""

import json
import logging
import os
import socket
import sys
import threading
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter('[PsyClick Sync] %(levelname)s: %(message)s'))
logger.addHandler(_handler)

# ── Internal state ─────────────────────────────────────────────────────────────
_sync_status = {
    "enabled":    False,   # True once valid Supabase config is found
    "connected":  False,   # Last connectivity check result
    "last_sync":  None,    # ISO timestamp of last successful upload
    "pending":    0,       # Unsynced record count
    "error":      None,    # Last error string (None if clean)
    "syncing":    False,   # Currently uploading
}

_stop_event   = threading.Event()
_sync_thread  = None
_SYNC_INTERVAL = 60        # seconds between sync attempts
_CONN_TIMEOUT  = 5         # seconds for connectivity probe


# ── Config loading ─────────────────────────────────────────────────────────────

def _config_paths():
    """Return candidate config.json paths in priority order."""
    paths = []
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))

    if getattr(sys, 'frozen', False):
        # Packaged (PyInstaller): check alongside the exe and in %APPDATA%\PsyClick
        if hasattr(sys, '_MEIPASS'):
            paths.append(os.path.join(sys._MEIPASS, 'config.json'))
        paths.append(os.path.join(appdata, 'PsyClick', 'config.json'))
    else:
        # Development: project directory
        paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'))
        paths.append(os.path.join(appdata, 'PsyClick', 'config.json'))

    return paths


def _load_supabase_config():
    """Return (supabase_url, supabase_key) or (None, None) if not configured."""
    for path in _config_paths():
        try:
            if not os.path.exists(path):
                continue
            with open(path, 'r', encoding='utf-8-sig') as fh:
                cfg = json.load(fh)
            url = cfg.get('supabase_url', '').strip()
            key = cfg.get('supabase_key', '').strip()
            if url and key:
                logger.info(f'Supabase config loaded from {path}')
                return url, key
        except Exception as exc:
            logger.warning(f'Could not read {path}: {exc}')
    return None, None


# ── Connectivity check ─────────────────────────────────────────────────────────

def _is_online(url):
    """Return True if we can resolve the Supabase host DNS."""
    try:
        host = url.replace('https://', '').replace('http://', '').split('/')[0]
        socket.setdefaulttimeout(_CONN_TIMEOUT)
        socket.getaddrinfo(host, 443)
        return True
    except Exception:
        return False


# ── Sync logic ─────────────────────────────────────────────────────────────────

def _do_sync(supabase_url, supabase_key):
    """Upload all pending unsynced sessions to Supabase."""
    from database_manager import get_unsynced_sessions, mark_session_synced

    try:
        from supabase import create_client  # type: ignore
    except ImportError:
        _sync_status['error'] = 'supabase-py not installed — run: pip install supabase'
        logger.warning(_sync_status['error'])
        return

    try:
        client = create_client(supabase_url, supabase_key)
    except Exception as exc:
        _sync_status['error'] = f'Supabase client error: {exc}'
        _sync_status['connected'] = False
        return

    sessions = get_unsynced_sessions(limit=100)
    _sync_status['pending'] = len(sessions)

    if not sessions:
        _sync_status['connected']  = True
        _sync_status['last_sync']  = time.strftime('%Y-%m-%d %H:%M:%S')
        _sync_status['error']      = None
        return

    _sync_status['syncing'] = True
    synced = 0

    for row in sessions:
        try:
            # Upsert using local session_id as the conflict key.
            # Your Supabase intake_sessions table should have session_id as PK
            # (or a unique index) to accept upserts from multiple devices.
            client.table('intake_sessions').upsert(
                row, on_conflict='session_id'
            ).execute()
            mark_session_synced(row['session_id'])
            synced += 1
        except Exception as exc:
            logger.error(f"Failed to sync session {row.get('session_id')}: {exc}")
            _sync_status['error'] = str(exc)
            break   # stop on first error; retry next cycle

    _sync_status['pending']   = max(0, _sync_status['pending'] - synced)
    _sync_status['connected'] = True
    _sync_status['last_sync'] = time.strftime('%Y-%m-%d %H:%M:%S')
    if synced == len(sessions):
        _sync_status['error'] = None
    _sync_status['syncing'] = False

    if synced:
        logger.info(f'Synced {synced} session(s) to Supabase.')


# ── Background loop ────────────────────────────────────────────────────────────

def _sync_loop():
    """Runs on a daemon thread; checks for work every _SYNC_INTERVAL seconds."""
    # Brief startup delay so the Flask server and DB are ready first
    _stop_event.wait(5)

    while not _stop_event.is_set():
        try:
            from database_manager import get_unsynced_count
            _sync_status['pending'] = get_unsynced_count()

            supabase_url, supabase_key = _load_supabase_config()

            if supabase_url and supabase_key:
                _sync_status['enabled'] = True
                if _is_online(supabase_url):
                    _do_sync(supabase_url, supabase_key)
                else:
                    _sync_status['connected'] = False
            else:
                _sync_status['enabled'] = False

        except Exception as exc:
            logger.error(f'Sync loop error: {exc}')

        _stop_event.wait(_SYNC_INTERVAL)


# ── Public API ─────────────────────────────────────────────────────────────────

def start_sync_service():
    """Start the background sync service. Idempotent — safe to call multiple times."""
    global _sync_thread
    if _sync_thread and _sync_thread.is_alive():
        return
    _stop_event.clear()
    _sync_thread = threading.Thread(
        target=_sync_loop, daemon=True, name='psyclick-supabase-sync'
    )
    _sync_thread.start()
    logger.info('Background sync service started.')


def stop_sync_service():
    """Signal the background sync thread to stop."""
    _stop_event.set()


def get_sync_status():
    """Return a snapshot of the current sync status for the /api/sync/status endpoint."""
    try:
        from database_manager import get_unsynced_count
        _sync_status['pending'] = get_unsynced_count()
    except Exception:
        pass
    return dict(_sync_status)


def trigger_sync_now():
    """Attempt an immediate sync (blocking). Returns updated status dict."""
    supabase_url, supabase_key = _load_supabase_config()
    if not supabase_url or not supabase_key:
        return get_sync_status()
    if _is_online(supabase_url):
        _do_sync(supabase_url, supabase_key)
    return get_sync_status()


def pull_from_supabase():
    """
    One-time migration: pull existing sessions from Supabase into local SQLite.
    Only inserts rows that don't already exist locally (by session_id).
    Returns (pulled_count, error_message).
    """
    supabase_url, supabase_key = _load_supabase_config()

    # Also support legacy postgresql:// URL from config for the pull
    if not supabase_url or not supabase_key:
        supabase_url, supabase_key = _load_postgres_config()

    if not supabase_url:
        return 0, 'No Supabase credentials configured in config.json'

    if not _is_online(supabase_url if not supabase_url.startswith('postgresql') else supabase_url.split('@')[1].split('/')[0]):
        return 0, 'No internet connection'

    try:
        import psycopg2  # type: ignore
        from database_manager import _conn, _exec

        pg = psycopg2.connect(_load_postgres_config()[0], connect_timeout=10)
        pg_c = pg.cursor()

        # Fetch all sessions from Supabase
        pg_c.execute("""
            SELECT session_id, student_id, timestamp,
                   kbase_mean, kbase_std,
                   mbase_hv, mbase_vv, mbase_tv, mbase_ta, mbase_jerk, mbase_curve,
                   phq_score, phq_hv, phq_vv, phq_tv, phq_ta, phq_jerk, phq_curve,
                   gad_score, gad_hv, gad_vv, gad_tv, gad_ta, gad_jerk, gad_curve,
                   task_k_mean, task_k_std, k_z_score, m_z_score,
                   t2_score, t2_threshold, psi, pai,
                   fuzzy_label, fuzzy_confidence, flag, rationale,
                   domain_t2_json, question_snapshots_json
            FROM intake_sessions
            ORDER BY session_id
        """)
        remote_rows = pg_c.fetchall()
        pg.close()

        if not remote_rows:
            return 0, None

        local = _conn()
        # Get existing local session_ids to avoid duplicates
        existing = {r[0] for r in _exec(local, 'SELECT session_id FROM intake_sessions').fetchall()}

        pulled = 0
        for row in remote_rows:
            sid = row[0]
            if sid in existing:
                continue
            _exec(local, """
                INSERT INTO intake_sessions (
                    session_id, student_id, timestamp,
                    kbase_mean, kbase_std,
                    mbase_hv, mbase_vv, mbase_tv, mbase_ta, mbase_jerk, mbase_curve,
                    phq_score, phq_hv, phq_vv, phq_tv, phq_ta, phq_jerk, phq_curve,
                    gad_score, gad_hv, gad_vv, gad_tv, gad_ta, gad_jerk, gad_curve,
                    task_k_mean, task_k_std, k_z_score, m_z_score,
                    t2_score, t2_threshold, psi, pai,
                    fuzzy_label, fuzzy_confidence, flag, rationale,
                    domain_t2_json, question_snapshots_json,
                    synced_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (*row, time.strftime('%Y-%m-%d %H:%M:%S')))  # mark as already synced
            pulled += 1

        local.commit()
        local.close()
        logger.info(f'Pulled {pulled} session(s) from Supabase into local SQLite.')
        return pulled, None

    except Exception as exc:
        logger.error(f'pull_from_supabase error: {exc}')
        return 0, str(exc)


def _load_postgres_config():
    """Return the raw postgresql:// URL from config (for legacy pull migration)."""
    for path in _config_paths():
        try:
            if not os.path.exists(path):
                continue
            with open(path, 'r', encoding='utf-8-sig') as fh:
                cfg = json.load(fh)
            url = cfg.get('database_url', '').strip()
            if url.startswith('postgresql://') or url.startswith('postgres://'):
                return url, None
        except Exception:
            pass
    return None, None
