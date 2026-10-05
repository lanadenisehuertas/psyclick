"""
database_manager_offline.py — PsyClick v4 OFFLINE EDITION
SQLite ONLY — No Supabase/PostgreSQL/Cloud — Completely Local & Offline

This version uses ONLY local SQLite database.
No network connections, no configuration files, no external dependencies.
Perfect for air-gapped clinical environments and demo deployments.
"""
import sqlite3, math, json, os, re, sys, time, hashlib, secrets, threading, uuid
import logging
from datetime import datetime, timedelta

# Configure logging for database operations
logger = logging.getLogger(__name__)
_log_handler = logging.StreamHandler(sys.stderr)
_log_handler.setFormatter(logging.Formatter('[PsyClick DB] %(levelname)s: %(message)s'))
logger.addHandler(_log_handler)
logger.setLevel(logging.WARNING)


# ── OFFLINE: SQLite ONLY ──────────────────────────────────────────────────────

SECURE_HOME = os.environ.get(
    "PSYCLICK_SECURE_HOME",
    os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PsyClickSecure"),
)
DB_NAME = None   # SQLite file path (always used in offline mode)
_DB_STATUS = {
    "configured_backend": "sqlite",
    "active_backend": "sqlite",
    "fallback_active": False,
    "available": True,
    "last_error": None,
    "last_error_at": None,
}


class DatabaseUnavailableError(RuntimeError):
    """Raised when local database cannot be accessed (disk full, permissions, etc.)."""


def _resolve_defaults():
    global DB_NAME

    # Explicit override (used by the test suite to isolate its data).
    override = os.environ.get("PSYCLICK_DB_PATH")
    if override:
        os.makedirs(os.path.dirname(os.path.abspath(override)), exist_ok=True)
        DB_NAME = override
        return

    # Determine base directory
    if getattr(sys, 'frozen', False):
        base = SECURE_HOME
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secure-data")
    os.makedirs(base, exist_ok=True)
    DB_NAME = os.path.join(base, 'psyclick_data.db')

    logger.info(f'[DB] Using local SQLite database: {DB_NAME}')


_resolve_defaults()


def reapply_db_config():
    """Re-run database path resolution. Safe to call at startup."""
    global DB_NAME
    DB_NAME = None
    _resolve_defaults()


def get_db_mode():
    """Return ('sqlite', path) — always SQLite in offline mode."""
    return 'sqlite', {'path': DB_NAME, 'mode': 'offline'}


def _record_db_error(exc):
    _DB_STATUS.update({
        "active_backend": "sqlite",
        "available": False,
        "last_error": str(exc),
        "last_error_at": time.strftime('%Y-%m-%d %H:%M:%S'),
    })


def get_db_status():
    """Return runtime DB status for UI/API diagnostics."""
    mode, info = get_db_mode()
    status = dict(_DB_STATUS)
    status.update({"backend": mode, "info": info})
    return status


def configure_db(path_or_url=None):
    """
    OFFLINE: Ignored. Database is always local SQLite.
    This function exists for API compatibility only.
    """
    logger.warning('[DB] configure_db() called but ignored — offline mode uses local SQLite only')


# ── Connection / SQL helpers (SQLite only) ────────────────────────────────────

def _conn():
    """Return SQLite connection (only backend in offline mode)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        _DB_STATUS.update({
            "active_backend": "sqlite",
            "available": True,
            "fallback_active": False,
            "last_error": None,
            "last_error_at": None,
        })
        return conn
    except Exception as exc:
        _record_db_error(exc)
        raise DatabaseUnavailableError(
            f"Local SQLite database unavailable: {exc}. Check disk space and file permissions at {DB_NAME}"
        ) from exc


def _ph():
    """Parameter placeholder: ? (SQLite only)."""
    return '?'


def _sql(s):
    """SQL is already SQLite format — no adaptation needed in offline mode."""
    return s


def _exec(conn, sql, params=None):
    """Execute SQL; return cursor."""
    c = conn.cursor()
    c.execute(sql, params or ())
    return c


def _insert_returning(conn, sql, params, returning_col='id'):
    """Execute INSERT and return the new row's primary key (SQLite lastrowid)."""
    c = conn.cursor()
    c.execute(sql, params)
    return c.lastrowid


def _tables(conn):
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in c.fetchall()]


def _add_col(conn, table, col, coltype):
    try:
        c = conn.cursor()
        c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {coltype} DEFAULT NULL')
    except Exception:
        pass


# ── Schema creation ───────────────────────────────────────────────────────────

def init_db():
    conn = _conn()
    c    = conn.cursor()

    tables = _tables(conn)

    # ── Migrations on existing intake_sessions ────────────────────────────────
    if 'intake_sessions' in tables:
        _add_col(conn, 'intake_sessions', 'domain_t2_json',          'TEXT')
        _add_col(conn, 'intake_sessions', 'question_snapshots_json',  'TEXT')
        _add_col(conn, 'intake_sessions', 'clinician_id',             'INTEGER')
        _add_col(conn, 'intake_sessions', 'flight_times_json',        'TEXT')
        _add_col(conn, 'intake_sessions', 'synced_at',                'TEXT')
        _add_col(conn, 'intake_sessions', 'phq_item9',                'INTEGER')
        conn.commit()

    if 'clinicians' in tables:
        _add_col(conn, 'clinicians', 'password_hash',   'TEXT')
        _add_col(conn, 'clinicians', 'role',            'TEXT')
        _add_col(conn, 'clinicians', 'status',          'TEXT')
        _add_col(conn, 'clinicians', 'failed_attempts', 'INTEGER')
        _add_col(conn, 'clinicians', 'locked_until',    'TEXT')
        _add_col(conn, 'clinicians', 'last_login_at',   'TEXT')
        conn.commit()

    if 'audit_log' in tables:
        _add_col(conn, 'audit_log', 'actor_id',  'INTEGER')
        _add_col(conn, 'audit_log', 'outcome',   'TEXT')
        _add_col(conn, 'audit_log', 'prev_hash', 'TEXT')
        _add_col(conn, 'audit_log', 'entry_hash','TEXT')
        conn.commit()

    # Each table is created in its own try-except + commit
    _DDL_TABLES = [
        # ── Clinicians ────────────────────────────────────────────────────────
        ("clinicians", """
            CREATE TABLE IF NOT EXISTS clinicians (
                clinician_id     INTEGER PRIMARY KEY,
                name             TEXT NOT NULL UNIQUE,
                password         TEXT NOT NULL,
                password_hash    TEXT,
                role             TEXT DEFAULT 'clinician',
                status           TEXT DEFAULT 'active',
                failed_attempts  INTEGER DEFAULT 0,
                locked_until     TEXT,
                last_login_at    TEXT,
                created_at       TEXT DEFAULT (datetime('now')),
                account_uid      TEXT,
                updated_at       TEXT,
                sync_dirty       INTEGER DEFAULT 1
            )
        """),

        # ── Main clinical sessions ────────────────────────────────────────────
        ("intake_sessions", """
            CREATE TABLE IF NOT EXISTS intake_sessions (
                session_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id       TEXT,
                clinician_id     INTEGER,
                timestamp        TEXT DEFAULT (datetime('now')),
                kbase_mean REAL, kbase_std REAL,
                mbase_hv REAL, mbase_vv REAL, mbase_tv REAL,
                mbase_ta REAL, mbase_jerk REAL, mbase_curve REAL,
                phq_score INTEGER,
                phq_hv REAL, phq_vv REAL, phq_tv REAL,
                phq_ta REAL, phq_jerk REAL, phq_curve REAL,
                gad_score INTEGER,
                gad_hv REAL, gad_vv REAL, gad_tv REAL,
                gad_ta REAL, gad_jerk REAL, gad_curve REAL,
                task_k_mean REAL, task_k_std REAL,
                k_z_score REAL, m_z_score REAL,
                t2_score        REAL,
                t2_threshold    REAL,
                psi             REAL,
                pai             REAL,
                fuzzy_label     TEXT,
                fuzzy_confidence REAL,
                flag            TEXT,
                rationale       TEXT,
                domain_t2_json  TEXT,
                question_snapshots_json TEXT,
                flight_times_json TEXT,
                synced_at       TEXT DEFAULT NULL,
                phq_item9       INTEGER,
                session_uid     TEXT,
                updated_at      TEXT,
                quality_json    TEXT,
                phq_items_json  TEXT,
                gad_items_json  TEXT,
                context_json    TEXT,
                device_id       TEXT,
                first_visit     INTEGER
            )
        """),

        # ── Per-question snapshots ────────────────────────────────────────────
        ("question_snapshots", """
            CREATE TABLE IF NOT EXISTS question_snapshots (
                snap_id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id        INTEGER,
                item_id           TEXT,
                group_id          INTEGER,
                level             TEXT,
                domain_label      TEXT,
                t2_score          REAL,
                psi               REAL,
                pai               REAL,
                flag              TEXT,
                flight_time       REAL,
                pause_freq        REAL,
                response_len      INTEGER,
                hover_words_json  TEXT,
                question_shown_at REAL
            )
        """),

        # ── Audit log ─────────────────────────────────────────────────────────
        ("audit_log", """
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                actor     TEXT,
                actor_id  INTEGER,
                action    TEXT,
                detail    TEXT,
                outcome   TEXT DEFAULT 'success',
                prev_hash TEXT,
                entry_hash TEXT,
                timestamp TEXT DEFAULT (datetime('now','localtime'))
            )
        """),

        ("security_sessions", """
            CREATE TABLE IF NOT EXISTS security_sessions (
                session_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash  TEXT NOT NULL UNIQUE,
                clinician_id INTEGER NOT NULL,
                role        TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                expires_at  TEXT NOT NULL,
                revoked_at  TEXT,
                FOREIGN KEY (clinician_id) REFERENCES clinicians(clinician_id)
            )
        """),

        ("consent_records", """
            CREATE TABLE IF NOT EXISTS consent_records (
                consent_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id  TEXT NOT NULL,
                clinician_id INTEGER NOT NULL,
                consent_version TEXT NOT NULL,
                decision    TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                withdrawn_at TEXT,
                FOREIGN KEY (clinician_id) REFERENCES clinicians(clinician_id)
            )
        """),

        ("backup_records", """
            CREATE TABLE IF NOT EXISTS backup_records (
                backup_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT NOT NULL,
                created_by  INTEGER NOT NULL,
                file_path   TEXT NOT NULL,
                sha256      TEXT NOT NULL,
                encrypted   INTEGER NOT NULL DEFAULT 1,
                verified_at TEXT,
                status      TEXT NOT NULL DEFAULT 'created'
            )
        """),

        # ── Normative sessions ────────────────────────────────────────────────
        ("normative_sessions", """
            CREATE TABLE IF NOT EXISTS normative_sessions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                tester_id        TEXT,
                timestamp        TEXT DEFAULT (datetime('now')),
                t2_score         REAL,
                t2_threshold     REAL,
                psi              REAL,
                pai              REAL,
                phq_score        INTEGER,
                gad_score        INTEGER,
                kbase_mean       REAL,
                kbase_std        REAL,
                flight_time_mean REAL,
                domain_t2_json   TEXT,
                level_t2_json    TEXT
            )
        """),

        # ── Cloud sync bookkeeping ────────────────────────────────────────────
        ("sync_tombstones", """
            CREATE TABLE IF NOT EXISTS sync_tombstones (
                session_uid TEXT PRIMARY KEY,
                deleted_at  TEXT NOT NULL,
                pushed      INTEGER DEFAULT 0
            )
        """),
        ("sync_state", """
            CREATE TABLE IF NOT EXISTS sync_state (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """),

        # ── Normative population stats ────────────────────────────────────────
        ("normative_stats", """
            CREATE TABLE IF NOT EXISTS normative_stats (
                metric       TEXT PRIMARY KEY,
                norm_mean    REAL,
                norm_sd      REAL,
                count        INTEGER,
                computed_at  TEXT DEFAULT (datetime('now'))
            )
        """),
    ]

    for tbl_name, ddl in _DDL_TABLES:
        try:
            _exec(conn, ddl)
            conn.commit()
        except Exception as exc:
            logger.error(f"init_db: failed to create table '{tbl_name}': {exc}")
            try:
                conn.rollback()
            except Exception:
                pass

    # Security defaults for upgraded databases. The earliest account becomes
    # the bootstrap administrator when no administrator exists.
    try:
        c.execute("UPDATE clinicians SET role='clinician' WHERE role IS NULL OR role='' ")
        c.execute("UPDATE clinicians SET status='active' WHERE status IS NULL OR status='' ")
        c.execute("UPDATE clinicians SET failed_attempts=0 WHERE failed_attempts IS NULL")
        admin = c.execute("SELECT clinician_id FROM clinicians WHERE role='admin' LIMIT 1").fetchone()
        if not admin:
            first = c.execute("SELECT MIN(clinician_id) FROM clinicians").fetchone()
            if first and first[0] is not None:
                c.execute("UPDATE clinicians SET role='admin' WHERE clinician_id=?", (first[0],))
        conn.commit()
    except Exception as exc:
        logger.error(f"init_db: failed to apply security defaults: {exc}")

    # Migration guard for question_shown_at
    _add_col(conn, 'question_snapshots', 'question_shown_at', 'REAL')
    # A database created before a column existed, or by an older build, must
    # end up with the same columns as a fresh one (no-op when present).
    for col, coltype in (('domain_t2_json', 'TEXT'), ('question_snapshots_json', 'TEXT'),
                         ('clinician_id', 'INTEGER'), ('flight_times_json', 'TEXT'),
                         ('synced_at', 'TEXT'), ('phq_item9', 'INTEGER'),
                         ('session_uid', 'TEXT'), ('updated_at', 'TEXT'), ('quality_json', 'TEXT'),
                         ('phq_items_json', 'TEXT'), ('gad_items_json', 'TEXT'), ('context_json', 'TEXT'),
                         ('device_id', 'TEXT'), ('first_visit', 'INTEGER')):
        _add_col(conn, 'intake_sessions', col, coltype)
    # Sessions saved before the Repeat result existed (same meaning, old flag)
    _exec(conn, "UPDATE intake_sessions SET flag='REPEAT' WHERE fuzzy_label='Insufficient Data' AND flag='AMBER'")
    for col, coltype in (('account_uid', 'TEXT'), ('updated_at', 'TEXT'), ('sync_dirty', 'INTEGER')):
        _add_col(conn, 'clinicians', col, coltype)
    # Every account and session needs an identity that is unique across
    # devices; local integer ids are not.
    try:
        for (cid,) in c.execute("SELECT clinician_id FROM clinicians WHERE account_uid IS NULL").fetchall():
            c.execute("UPDATE clinicians SET account_uid=?, updated_at=COALESCE(updated_at, ?), sync_dirty=1 "
                      "WHERE clinician_id=?", (uuid.uuid4().hex, utc_now(), cid))
        for (sid,) in c.execute("SELECT session_id FROM intake_sessions WHERE session_uid IS NULL").fetchall():
            c.execute("UPDATE intake_sessions SET session_uid=? WHERE session_id=?", (uuid.uuid4().hex, sid))
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_sessions_uid ON intake_sessions(session_uid)")
        conn.commit()
    except Exception as exc:
        logger.error(f"init_db: failed to assign sync identities: {exc}")

    try:
        conn.commit()
    except Exception:
        pass
    conn.close()

    # Seed normative stats if the table is empty
    _seed_normative_stats()


def _load_normative_reference():
    """Healthy-tester reference built by scripts/build_normative_reference.py."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "normative_reference.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning(f"[DB] Normative reference unavailable: {exc}")
        return None


_LEGACY_SEED_COUNT = 102   # count stamped by the superseded hard-coded seed


def _reference_signature(ref):
    t = ref.get("thresholds", {}).get("session", {})
    return f'reference:{ref.get("counts", {}).get("healthy_reference_testers")}:{round(t.get("p95", 0), 3)}'


def _seed_normative_stats():
    """
    Seed normative_stats from normative_reference.json (healthy tester
    population: one valid session per tester, PHQ-9 and GAD-7 < 10; see the
    build script for the method).

    Re-seeds whenever the shipped reference changes, so an updated reference
    reaches existing installs. Statistics an administrator recomputed locally
    from collected normative sessions are kept.
    """
    ref = _load_normative_reference()
    if not ref:
        return
    sig = _reference_signature(ref)
    try:
        conn = _conn()
        row = _exec(conn, "SELECT value FROM sync_state WHERE key='normative_source'").fetchone()
        source = row[0] if row else None
        if source == "local" or source == sig:
            conn.close()
            return
        _exec(conn, "DELETE FROM normative_stats")
        for metric, m in ref["metrics"].items():
            _exec(conn, """
                INSERT OR REPLACE INTO normative_stats (metric, norm_mean, norm_sd, count)
                VALUES (?, ?, ?, ?)
            """, (metric, m["mean"], m["sd"], m["n"]))
        _exec(conn, "INSERT OR REPLACE INTO sync_state (key, value) VALUES ('normative_source', ?)", (sig,))
        conn.commit()
        conn.close()
        logger.info(f'[DB] Seeded normative_stats from {ref["counts"]["healthy_reference_testers"]} healthy testers.')
    except Exception as exc:
        logger.warning(f'[DB] Could not seed normative_stats: {exc}')


# ── Utility ───────────────────────────────────────────────────────────────────

def _clean(val):
    """Convert any value to clean float, handling numpy types and NaN."""
    if val is None:
        return 0.0
    try:
        val = float(val)  # Convert first (handles numpy.float64, etc.)
        if math.isnan(val):
            return 0.0
        return val
    except (ValueError, TypeError):
        return 0.0


def _flatten_ae(ae):
    """Normalise analysis-engine result to flat scalar fields."""
    if not ae:
        return {
            "t2_score": 0.0,
            "t2_threshold": 0.0,
            "psi": 0.0,
            "pai": 0.0,
            "label": "",
            "confidence": 0.0,
            "flag": "GREEN",
            "rationale": "",
        }
    t2s   = ae.get("t2_scores")     or {}
    t2t   = ae.get("t2_thresholds") or {}
    psi_v = ae.get("psi")
    pai_v = ae.get("pai")
    return {
        "t2_score":    float(ae["t2_score"]) if ae.get("t2_score") is not None
                       else float(t2s.get("hybrid", t2s.get("ipsative", 0.0))),
        "t2_threshold":float(ae["t2_threshold"]) if ae.get("t2_threshold") is not None
                       else float(t2t.get("adjusted", t2t.get("base", 0.0))),
        "psi":         float(psi_v.get("total", psi_v.get("adjusted", 0.0)))
                       if isinstance(psi_v, dict) else float(psi_v if psi_v is not None else 0.0),
        "pai":         float(pai_v.get("total", 0.0))
                       if isinstance(pai_v, dict) else float(pai_v if pai_v is not None else 0.0),
        "label":       str(ae.get("label", "")),
        "confidence":  float(ae.get("confidence", 0.0)),
        "flag":        str(ae.get("flag", "GREEN")),
        "rationale":   str(ae.get("rationale", "")),
    }


# ── Clinical session save ─────────────────────────────────────────────────────

def save_full_intake(data):
    conn = _conn()

    ae = _flatten_ae(data.get("analysis", {}) or {})

    clinician_id = data.get("clinician_id")
    if clinician_id is not None:
        try:
            clinician_id = int(clinician_id)
        except (ValueError, TypeError):
            clinician_id = None

    # Build parameter tuple in EXACT column order
    numeric_vals = [
        data["kbase"].get("mean_flight", 0), data["kbase"].get("std_flight", 0),
        data["mbase"].get("hv", 0), data["mbase"].get("vv", 0), data["mbase"].get("tv", 0),
        data["mbase"].get("ta", 0), data["mbase"].get("jerk", 0), data["mbase"].get("curvature", 0),
        data["phq"].get("score", 0),
        data["phq"]["mouse"].get("hv", 0), data["phq"]["mouse"].get("vv", 0),
        data["phq"]["mouse"].get("tv", 0), data["phq"]["mouse"].get("ta", 0),
        data["phq"]["mouse"].get("jerk", 0), data["phq"]["mouse"].get("curvature", 0),
        data["gad"].get("score", 0),
        data["gad"]["mouse"].get("hv", 0), data["gad"]["mouse"].get("vv", 0),
        data["gad"]["mouse"].get("tv", 0), data["gad"]["mouse"].get("ta", 0),
        data["gad"]["mouse"].get("jerk", 0), data["gad"]["mouse"].get("curvature", 0),
        data["task"].get("mean_flight", data["task"].get("flight_time", 0)),
        data["task"].get("std_flight", 0),
        data.get("k_z_score", 0), data.get("m_z_score", 0),
        ae.get("t2_score"), ae.get("t2_threshold"),
        ae.get("psi"), ae.get("pai"),
    ]

    safe = (
        data["student_id"],
        clinician_id,
        *tuple(_clean(v) for v in numeric_vals),
        ae.get("label", ""),                          # fuzzy_label
        _clean(ae.get("confidence", 0.0)),            # fuzzy_confidence
        ae.get("flag", "GREEN"),                      # flag
        ae.get("rationale", ""),                      # rationale
        json.dumps(data.get("visuals", {}).get("domain_t2", {})),
        json.dumps([
            {k: v for k, v in s.items() if k not in ("raw_flights", "pause_coords")}
            for s in data.get("visuals", {}).get("question_snapshots", [])
        ]),
        json.dumps(data.get("visuals", {}).get("flight_times", [])),
    )

    placeholders = ','.join(['?'] * len(safe))
    session_id = _insert_returning(conn, f"""
        INSERT INTO intake_sessions (
            student_id,
            clinician_id,
            kbase_mean, kbase_std,
            mbase_hv, mbase_vv, mbase_tv, mbase_ta, mbase_jerk, mbase_curve,
            phq_score, phq_hv, phq_vv, phq_tv, phq_ta, phq_jerk, phq_curve,
            gad_score, gad_hv, gad_vv, gad_tv, gad_ta, gad_jerk, gad_curve,
            task_k_mean, task_k_std,
            k_z_score, m_z_score,
            t2_score, t2_threshold, psi, pai,
            fuzzy_label, fuzzy_confidence, flag, rationale,
            domain_t2_json, question_snapshots_json, flight_times_json
        ) VALUES ({placeholders})
    """, safe)

    item9 = (data.get("phq") or {}).get("item9")
    if item9 is not None:
        _exec(conn, "UPDATE intake_sessions SET phq_item9=? WHERE session_id=?", (int(item9), session_id))
    phq_items = (data.get("phq") or {}).get("items")
    gad_items = (data.get("gad") or {}).get("items")
    _exec(conn, """UPDATE intake_sessions SET session_uid=?, updated_at=?, quality_json=?,
                   phq_items_json=?, gad_items_json=?, context_json=?, device_id=?, first_visit=?
                   WHERE session_id=?""",
          (uuid.uuid4().hex, utc_now(), json.dumps(data.get("quality") or {}),
           json.dumps(phq_items) if phq_items else None, json.dumps(gad_items) if gad_items else None,
           json.dumps(data.get("context") or {}), get_device_id(conn),
           None if data.get("first_visit") is None else int(bool(data.get("first_visit"))), session_id))
    conn.commit()
    note_client_code(clinician_id, data.get("student_id"))

    # Per-question snapshots
    for snap in data.get("visuals", {}).get("question_snapshots", []):
        try:
            hover_json = json.dumps(snap.get("hover_words", []) or [])
        except (TypeError, ValueError):
            hover_json = json.dumps([])

        _exec(conn, """
            INSERT INTO question_snapshots
              (session_id, item_id, group_id, level, domain_label,
               t2_score, psi, pai, flag, flight_time, pause_freq,
               response_len, hover_words_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            session_id,
            snap.get("item_id", "?"),
            snap.get("group_id", 0),
            snap.get("level", "A"),
            snap.get("domain_label", ""),
            _clean(snap.get("t2_score", 0) if not isinstance(snap.get("t2_score"), dict) else (snap.get("t2_score") or {}).get("hybrid", 0.0)),
            _clean(snap.get("psi", 0)      if not isinstance(snap.get("psi"),      dict) else (snap.get("psi")      or {}).get("total",  0.0)),
            _clean(snap.get("pai", 0)      if not isinstance(snap.get("pai"),      dict) else (snap.get("pai")      or {}).get("total",  0.0)),
            snap.get("flag", "GREEN"),
            _clean(snap.get("flight_time", 0)),
            _clean(snap.get("pause_freq", 0)),
            snap.get("response_len", 0),
            hover_json,
        ))

    conn.commit()
    conn.close()
    return session_id


# ── Audit ─────────────────────────────────────────────────────────────────────

_AUDIT_LOCK = threading.Lock()


def log_audit(actor, action, detail=None, actor_id=None, outcome="success"):
    """Append a hash-chained audit event without storing credentials or tokens.

    Reading the previous hash and inserting the new entry must be atomic:
    two concurrent requests would otherwise both chain onto the same entry
    and fork the chain. A process lock serialises threads; BEGIN IMMEDIATE
    takes SQLite's write lock so separate processes are serialised too.
    """
    try:
        with _AUDIT_LOCK:
            return _append_audit(actor, action, detail, actor_id, outcome)
    except Exception as e:
        logger.error(f"Failed to log audit event: actor={actor}, action={action}, detail={detail}, error={str(e)}")
        return False


def _append_audit(actor, action, detail, actor_id, outcome):
    conn = _conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        previous = _exec(conn,
            "SELECT entry_hash FROM audit_log ORDER BY log_id DESC LIMIT 1"
        ).fetchone()
        prev_hash = (previous[0] if previous and previous[0] else "0" * 64)
        canonical = "|".join([
            prev_hash, ts, str(actor or "system"), str(actor_id or ""),
            str(action or ""), str(detail or ""), str(outcome or "success"),
        ])
        entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        _exec(conn,
              """INSERT INTO audit_log
                 (actor, actor_id, action, detail, outcome, prev_hash, entry_hash, timestamp)
                 VALUES (?,?,?,?,?,?,?,?)""",
              (actor, actor_id, action, detail, outcome, prev_hash, entry_hash, ts))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_audit_logs(actor=None):
    try:
        conn = _conn()
        if actor:
            rows = _exec(conn,
                "SELECT timestamp, action, detail FROM audit_log WHERE actor=? ORDER BY log_id DESC",
                (actor,)).fetchall()
        else:
            rows = _exec(conn,
                "SELECT timestamp, actor, action, detail FROM audit_log ORDER BY log_id DESC"
                ).fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Failed to retrieve audit logs (actor={actor}): {str(e)}")
        return []


def verify_audit_chain():
    """Return (valid, checked_count, first_invalid_log_id)."""
    conn = _conn()
    rows = _exec(conn, """
        SELECT log_id, actor, actor_id, action, detail, outcome,
               prev_hash, entry_hash, timestamp
        FROM audit_log ORDER BY log_id ASC
    """).fetchall()
    conn.close()
    previous = "0" * 64
    checked = 0
    for row in rows:
        log_id, actor, actor_id, action, detail, outcome, prev_hash, entry_hash, ts = row
        # Legacy rows predate chaining and remain visible but start a new chain.
        if not entry_hash:
            continue
        canonical = "|".join([
            str(prev_hash or previous), str(ts), str(actor or "system"), str(actor_id or ""),
            str(action or ""), str(detail or ""), str(outcome or "success"),
        ])
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if prev_hash != previous or not secrets.compare_digest(entry_hash, expected):
            return False, checked, log_id
        previous = entry_hash
        checked += 1
    return True, checked, None


# ── Session queries ───────────────────────────────────────────────────────────

def get_student_session_count(student_id, clinician_id=None):
    try:
        conn = _conn()
        if clinician_id:
            count = _exec(conn,
                "SELECT COUNT(*) FROM intake_sessions WHERE student_id=? AND clinician_id=?",
                (student_id, clinician_id)).fetchone()[0]
        else:
            count = _exec(conn,
                "SELECT COUNT(*) FROM intake_sessions WHERE student_id=?",
                (student_id,)).fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Failed to get session count for student {student_id}: {str(e)}")
        return 0


def get_sessions_by_student(student_id):
    try:
        conn = _conn()
        rows = _exec(conn, """
            SELECT session_id, timestamp, phq_score, gad_score, flag
            FROM intake_sessions WHERE student_id=?
            ORDER BY timestamp DESC
        """, (student_id,)).fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Failed to get sessions for student {student_id}: {str(e)}")
        return []


def get_latest_sessions():
    try:
        conn = _conn()
        rows = _exec(conn, """
            SELECT s.session_id, s.student_id, s.timestamp, s.flag, s.phq_score, s.gad_score
            FROM intake_sessions s
            INNER JOIN (
                SELECT student_id, MAX(timestamp) AS max_ts
                FROM intake_sessions
                GROUP BY student_id
            ) latest ON s.student_id = latest.student_id AND s.timestamp = latest.max_ts
            ORDER BY s.timestamp DESC
        """).fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Failed to get latest sessions: {str(e)}")
        return []


# ── Normative functions ───────────────────────────────────────────────────────

def save_normative_session(data):
    ae   = _flatten_ae(data.get("analysis", {}) or {})
    vis  = data.get("visuals",  {}) or {}
    kb   = data.get("kbase",    {}) or {}
    task = data.get("task",     {}) or {}
    phq  = data.get("phq",      {}) or {}
    gad  = data.get("gad",      {}) or {}

    conn = _conn()
    params = (
        data.get("student_id", "NORMER"),
        _clean(ae.get("t2_score")),
        _clean(ae.get("t2_threshold")),
        _clean(ae.get("psi")),
        _clean(ae.get("pai")),
        int(phq.get("score", 0) or 0),
        int(gad.get("score", 0) or 0),
        _clean(kb.get("mean_flight")),
        _clean(kb.get("std_flight")),
        _clean(task.get("mean_flight", task.get("flight_time", 0))),
        json.dumps(vis.get("domain_t2", {})),
        json.dumps(vis.get("level_t2",  {})),
    )
    _exec(conn, """
        INSERT INTO normative_sessions
          (tester_id, t2_score, t2_threshold, psi, pai,
           phq_score, gad_score, kbase_mean, kbase_std, flight_time_mean,
           domain_t2_json, level_t2_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, params)
    conn.commit()
    conn.close()


def get_normative_count():
    try:
        conn = _conn()
        count = _exec(conn, "SELECT COUNT(*) FROM normative_sessions").fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


# Same rules as scripts/build_normative_reference.py: capture faults out, one
# session per tester, healthy (PHQ-9 and GAD-7 below 10) only.
MIN_HUMAN_IKI_S = 0.08


def compute_normative_stats():
    conn = _conn()
    rows = _exec(conn, """
        SELECT tester_id, timestamp, t2_score, psi, pai, phq_score, gad_score, flight_time_mean, kbase_mean
        FROM normative_sessions
        WHERE COALESCE(flight_time_mean, 0) >= ? AND COALESCE(kbase_mean, 0) >= ?
          -- first-session EWMA cold-start artifacts (T² > 10x its threshold)
          AND (t2_threshold IS NULL OR t2_threshold <= 0 OR t2_score <= 10 * t2_threshold)
        ORDER BY timestamp, id
    """, (MIN_HUMAN_IKI_S, MIN_HUMAN_IKI_S)).fetchall()
    conn.close()
    first = {}
    for r in rows:
        first.setdefault(r[0], r)
    healthy = [r for r in first.values() if (r[5] or 0) < 10 and (r[6] or 0) < 10]
    if not healthy:
        return False

    n    = len(healthy)
    cols = ['t2_score', 'psi', 'pai', 'phq_score', 'gad_score', 'flight_time_mean']
    stats = {}
    for i, col in enumerate(cols, start=2):
        vals = [float(r[i] or 0) for r in healthy]
        mean = sum(vals) / n
        sd   = math.sqrt(sum((v - mean) ** 2 for v in vals) / (n - 1)) if n > 1 else 1.0
        stats[col] = (mean, max(sd, 0.0001), n)

    conn = _conn()
    _exec(conn, "DELETE FROM normative_stats")
    for metric, (mean, sd, count) in stats.items():
        _exec(conn, """
            INSERT OR REPLACE INTO normative_stats (metric, norm_mean, norm_sd, count)
            VALUES (?,?,?,?)
        """, (metric, mean, sd, count))
    _exec(conn, "INSERT OR REPLACE INTO sync_state (key, value) VALUES ('normative_source', 'local')")
    conn.commit()
    conn.close()
    return True


def get_normative_stats():
    try:
        conn = _conn()
        rows  = _exec(conn,
            "SELECT metric, norm_mean, norm_sd, count, computed_at FROM normative_stats"
        ).fetchall()
        count = _exec(conn,
            "SELECT COUNT(*) FROM normative_sessions"
        ).fetchone()[0]
        conn.close()
        stats = {r[0]: {"mean": r[1], "sd": r[2], "count": r[3], "computed_at": r[4]} for r in rows}
        return {"stats": stats, "session_count": count, "baseline_ready": len(stats) > 0}
    except Exception:
        return {"stats": {}, "session_count": 0, "baseline_ready": False}


def get_normative_compare(session_id):
    try:
        from scipy.stats import norm as scipy_norm
        # Self-healing: ensure stats are seeded even if init_db() ran before the edit
        _seed_normative_stats()
        conn = _conn()

        row = _exec(conn, """
            SELECT t2_score, psi, pai, phq_score, gad_score
            FROM intake_sessions WHERE session_id=?
        """, (session_id,)).fetchone()

        stat_rows = _exec(conn,
            "SELECT metric, norm_mean, norm_sd, count FROM normative_stats"
        ).fetchall()
        conn.close()

        if not row or not stat_rows:
            return None

        norm   = {r[0]: {"mean": r[1], "sd": r[2], "count": r[3]} for r in stat_rows}
        labels = {
            "t2_score":  "Hotelling T²",
            "psi":       "Psychomotor Slowing Index",
            "pai":       "Psychomotor Agitation Index",
            "phq_score": "PHQ-9 Score",
            "gad_score": "GAD-7 Score",
        }
        patient_vals = {
            "t2_score":  row[0] or 0, "psi":       row[1] or 0,
            "pai":       row[2] or 0, "phq_score": row[3] or 0,
            "gad_score": row[4] or 0,
        }

        ref = _load_normative_reference() or {}
        ref_values = {m: v.get("values") for m, v in ref.get("metrics", {}).items()}

        result = {}
        for metric, pval in patient_vals.items():
            if metric in norm and norm[metric]["sd"] > 0:
                z   = (pval - norm[metric]["mean"]) / norm[metric]["sd"]
                values = ref_values.get(metric)
                if values:
                    # Empirical mid-rank percentile: these metrics are strongly
                    # right-skewed, so a normal-curve percentile would mislead.
                    below = sum(1 for v in values if v < pval)
                    equal = sum(1 for v in values if v == pval)
                    pct = 100.0 * (below + 0.5 * equal) / len(values)
                else:
                    pct = float(scipy_norm.cdf(z) * 100)
                result[metric] = {
                    "label":      labels[metric],
                    "patient":    pval,
                    "norm_mean":  norm[metric]["mean"],
                    "norm_sd":    norm[metric]["sd"],
                    "z":          round(z, 3),
                    "pct":        round(pct, 1),
                    "count":      norm[metric]["count"],
                }
        return result
    except Exception:
        return None


def get_session(session_id):
    try:
        conn = _conn()
        row = _exec(conn, """
            SELECT session_id, student_id, timestamp, flag, phq_score, gad_score,
                   t2_score, psi, pai, fuzzy_label, fuzzy_confidence
            FROM intake_sessions WHERE session_id=?
        """, (session_id,)).fetchone()
        conn.close()
        if row:
            return {
                "session_id": row[0],
                "student_id": row[1],
                "timestamp": row[2],
                "flag": row[3],
                "phq_score": row[4],
                "gad_score": row[5],
                "t2_score": row[6],
                "psi": row[7],
                "pai": row[8],
                "label": row[9],
                "confidence": row[10],
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {str(e)}")
        return None


def get_question_snapshots(session_id):
    try:
        conn = _conn()
        rows = _exec(conn, """
            SELECT snap_id, item_id, group_id, level, domain_label,
                   t2_score, psi, pai, flag, flight_time, pause_freq, response_len
            FROM question_snapshots WHERE session_id=?
            ORDER BY snap_id ASC
        """, (session_id,)).fetchall()
        conn.close()
        return [
            {
                "snap_id": r[0],
                "item_id": r[1],
                "group_id": r[2],
                "level": r[3],
                "domain_label": r[4],
                "t2_score": r[5],
                "psi": r[6],
                "pai": r[7],
                "flag": r[8],
                "flight_time": r[9],
                "pause_freq": r[10],
                "response_len": r[11],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get question snapshots for session {session_id}: {str(e)}")
        return []


# ── Clinician auth ────────────────────────────────────────────────────────────

PASSWORD_MIN_LENGTH = 12
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
SESSION_IDLE_MINUTES = 15
SESSION_ABSOLUTE_HOURS = 8


def _hash_password(password):
    salt = secrets.token_bytes(16)
    n, r, p = 16384, 8, 1
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32)
    return f"scrypt:{n}:{r}:{p}${salt.hex()}${derived.hex()}"


def _check_password(stored, password):
    try:
        params, salt_hex, expected_hex = stored.split("$")
        _, n, r, p = params.split(":")
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), dklen=len(bytes.fromhex(expected_hex)),
        )
        return secrets.compare_digest(actual.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


def _password_policy_error(password):
    if len(password or "") < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        return "Password must contain at least one letter and one number."
    common = {"password1234", "123456789012", "qwerty123456", "psyclick12345"}
    if password.lower() in common:
        return "Choose a password that is not commonly used."
    return None


def register_clinician(name, password, role=None):
    """
    Register a new clinician with auto-incrementing ID format: YYYYNNN
    (e.g., 2026001, 2026002, etc).
    Returns: (success, clinician_id, error_msg)
    """
    try:
        policy_error = _password_policy_error(password)
        if policy_error:
            return False, None, policy_error
        conn = _conn()

        existing = _exec(conn,
            "SELECT clinician_id FROM clinicians WHERE name=?",
            (name,)).fetchone()
        if existing:
            conn.close()
            return False, None, "Name already registered"

        current_year = datetime.now().year
        year_prefix  = str(current_year)
        year_start   = int(f"{year_prefix}000")
        year_end     = int(f"{year_prefix}999")

        latest = _exec(conn,
            "SELECT MAX(clinician_id) FROM clinicians WHERE clinician_id >= ? AND clinician_id <= ?",
            (year_start, year_end)).fetchone()

        next_seq = (latest[0] % 1000) + 1 if (latest and latest[0]) else 1
        clinician_id = int(f"{year_prefix}{next_seq:03d}")

        count = _exec(conn, "SELECT COUNT(*) FROM clinicians").fetchone()[0]
        assigned_role = role if role in {"admin", "clinician", "auditor"} else ("admin" if count == 0 else "clinician")
        password_hash = _hash_password(password)
        _exec(conn,
            """INSERT INTO clinicians
               (clinician_id, name, password, password_hash, role, status, failed_attempts,
                account_uid, updated_at, sync_dirty)
               VALUES (?, ?, '', ?, ?, 'active', 0, ?, ?, 1)""",
            (clinician_id, name, password_hash, assigned_role, uuid.uuid4().hex, utc_now()))
        conn.commit()
        conn.close()
        return True, clinician_id, None
    except Exception as e:
        return False, None, str(e)


def get_clinician_by_id(clinician_id):
    """Return clinician dict or None."""
    try:
        conn = _conn()
        row  = _exec(conn,
            "SELECT clinician_id, name, role, status FROM clinicians WHERE clinician_id=?",
            (clinician_id,)).fetchone()
        conn.close()
        return {
            "clinician_id": row[0], "name": row[1],
            "role": row[2] or "clinician", "status": row[3] or "active",
        } if row else None
    except Exception:
        return None


def verify_clinician(clinician_id, password):
    """Verify a credential, enforce lockout, and migrate legacy plaintext once."""
    try:
        conn = _conn()
        row  = _exec(conn,
            """SELECT password, password_hash, name, status,
                      COALESCE(failed_attempts,0), locked_until
               FROM clinicians WHERE clinician_id=?""",
            (clinician_id,)).fetchone()
        if not row:
            conn.close()
            return False, "Invalid clinician ID or password."

        legacy_password, password_hash, name, status, failed_attempts, locked_until = row
        now = datetime.now()
        if status != "active":
            conn.close()
            return False, "Account is disabled. Contact the administrator."
        if locked_until:
            try:
                if datetime.fromisoformat(locked_until) > now:
                    conn.close()
                    return False, "Account is temporarily locked. Try again later."
            except ValueError:
                pass

        verified = False
        if password_hash:
            try:
                verified = _check_password(password_hash, password)
            except (ValueError, TypeError):
                verified = False
        elif legacy_password:
            # One-time migration path for existing academic prototype accounts.
            verified = secrets.compare_digest(str(legacy_password), str(password))

        if not verified:
            failed_attempts += 1
            new_lock = None
            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                new_lock = (now + timedelta(minutes=LOCKOUT_MINUTES)).isoformat(timespec="seconds")
                failed_attempts = 0
            _exec(conn,
                "UPDATE clinicians SET failed_attempts=?, locked_until=? WHERE clinician_id=?",
                (failed_attempts, new_lock, clinician_id))
            conn.commit(); conn.close()
            return False, "Invalid clinician ID or password."

        migrated = not password_hash
        if migrated:
            password_hash = _hash_password(password)
        _exec(conn, """
            UPDATE clinicians
            SET password='', password_hash=?, failed_attempts=0,
                locked_until=NULL, last_login_at=?
            WHERE clinician_id=?
        """, (password_hash, now.isoformat(timespec="seconds"), clinician_id))
        if migrated:
            touch_clinician(conn, clinician_id)
        conn.commit(); conn.close()
        return True, name
    except Exception:
        return False, "Authentication service unavailable."


def create_security_session(clinician_id, role):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now()
    expires = now + timedelta(hours=SESSION_ABSOLUTE_HOURS)
    conn = _conn()
    _exec(conn, """
        INSERT INTO security_sessions
        (token_hash, clinician_id, role, created_at, last_seen_at, expires_at)
        VALUES (?,?,?,?,?,?)
    """, (token_hash, clinician_id, role, now.isoformat(timespec="seconds"),
          now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")))
    conn.commit(); conn.close()
    return token, expires.isoformat(timespec="seconds")


def authenticate_security_session(token):
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = _conn()
    row = _exec(conn, """
        SELECT s.session_id, s.clinician_id, s.role, s.last_seen_at, s.expires_at,
               c.name, c.status
        FROM security_sessions s
        JOIN clinicians c ON c.clinician_id=s.clinician_id
        WHERE s.token_hash=? AND s.revoked_at IS NULL
    """, (token_hash,)).fetchone()
    if not row:
        conn.close(); return None
    session_id, clinician_id, role, last_seen_at, expires_at, name, status = row
    now = datetime.now()
    try:
        expired = datetime.fromisoformat(expires_at) <= now
        idle = datetime.fromisoformat(last_seen_at) + timedelta(minutes=SESSION_IDLE_MINUTES) <= now
    except ValueError:
        expired = idle = True
    if status != "active" or expired or idle:
        _exec(conn, "UPDATE security_sessions SET revoked_at=? WHERE session_id=?",
              (now.isoformat(timespec="seconds"), session_id))
        conn.commit(); conn.close(); return None
    _exec(conn, "UPDATE security_sessions SET last_seen_at=? WHERE session_id=?",
          (now.isoformat(timespec="seconds"), session_id))
    conn.commit(); conn.close()
    return {"session_id": session_id, "id": clinician_id, "name": name, "role": role}


def revoke_security_session(token):
    if not token:
        return False
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = _conn()
    cursor = _exec(conn, "UPDATE security_sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
                   (datetime.now().isoformat(timespec="seconds"), token_hash))
    conn.commit(); changed = cursor.rowcount; conn.close()
    return changed > 0


def record_consent(patient_id, clinician_id, decision="granted", version="1.0"):
    if decision not in {"granted", "denied", "withdrawn"}:
        raise ValueError("Invalid consent decision")
    now = datetime.now().isoformat(timespec="seconds")
    conn = _conn()
    _exec(conn, """
        INSERT INTO consent_records
        (patient_id, clinician_id, consent_version, decision, recorded_at, withdrawn_at)
        VALUES (?,?,?,?,?,?)
    """, (patient_id, clinician_id, version, decision, now, now if decision == "withdrawn" else None))
    conn.commit(); conn.close()
    return True


def has_active_consent(patient_id, clinician_id):
    conn = _conn()
    row = _exec(conn, """
        SELECT decision FROM consent_records
        WHERE patient_id=? AND clinician_id=?
        ORDER BY consent_id DESC LIMIT 1
    """, (patient_id, clinician_id)).fetchone()
    conn.close()
    return bool(row and row[0] == "granted")


# ── Auto-ID generation ────────────────────────────────────────────────────────

def _code_number(code):
    m = re.fullmatch(r"C-(\d+)", str(code or ""))
    return int(m.group(1)) if m else 0


def get_next_client_id(clinician_id=None):
    """
    Next client code for this clinician: one past the highest code ever used.
    Codes are never reused, even after a client is deleted, so a code cannot
    end up joining two different people's histories on different devices.
    """
    try:
        conn = _conn()
        if clinician_id:
            rows = _exec(conn, "SELECT DISTINCT student_id FROM intake_sessions WHERE clinician_id=?",
                         (clinician_id,)).fetchall()
        else:
            rows = _exec(conn, "SELECT DISTINCT student_id FROM intake_sessions").fetchall()
        mark = _exec(conn, "SELECT value FROM sync_state WHERE key=?", (f"client_code_high:{clinician_id}",)).fetchone()
        conn.close()
        high = max([_code_number(r[0]) for r in rows] + [int(mark[0]) if mark else 0])
        return f"C-{high + 1:03d}"
    except Exception:
        return None


def get_device_id(conn=None):
    """A random id for this installation (kept in the local sync state).
    Pass the open connection when called inside a write, so it is not locked out."""
    own = conn is None
    conn = conn or _conn()
    try:
        row = _exec(conn, "SELECT value FROM sync_state WHERE key='device_id'").fetchone()
        if row:
            return row[0]
        did = uuid.uuid4().hex[:12]
        _exec(conn, "INSERT OR REPLACE INTO sync_state (key, value) VALUES ('device_id', ?)", (did,))
        if own:
            conn.commit()
        return did
    finally:
        if own:
            conn.close()


def code_conflicts(clinician_id):
    """Client codes this clinician started as a NEW client on more than one
    device. That happens when two devices were offline and both handed out the
    same next code, so the code may now hold two different people."""
    conn = _conn()
    try:
        rows = _exec(conn, """SELECT student_id, device_id FROM intake_sessions
                               WHERE clinician_id=? AND first_visit=1 AND device_id IS NOT NULL""",
                     (clinician_id,)).fetchall()
    finally:
        conn.close()
    devices = {}
    for code, dev in rows:
        devices.setdefault(code, set()).add(dev)
    return {code for code, devs in devices.items() if len(devs) > 1}


def replace_session(session_id, clinician_id, changes):
    """Re-record a session with some fields changed (new client code, or
    confirmed as the same person). Sessions sync as insert-only records, so the
    change reaches other devices as a new record plus a deletion of the old."""
    conn = _conn()
    try:
        cols = _session_columns(conn)
        row = _exec(conn, f"SELECT {', '.join(cols)} FROM intake_sessions WHERE session_id=? AND clinician_id=?",
                    (session_id, clinician_id)).fetchone()
        if not row:
            return None
        data = {**dict(zip(cols, row)), **changes,
                "session_uid": uuid.uuid4().hex, "updated_at": utc_now(), "synced_at": None}
        keep = [c for c in cols if c != "session_id"]
        new_id = _insert_returning(conn, f"INSERT INTO intake_sessions ({', '.join(keep)}) "
                                         f"VALUES ({', '.join('?' * len(keep))})", [data[c] for c in keep])
        qcols = [r[1] for r in _exec(conn, "PRAGMA table_info(question_snapshots)").fetchall() if r[1] != "snap_id"]
        for q in _exec(conn, f"SELECT {', '.join(qcols)} FROM question_snapshots WHERE session_id=?",
                       (session_id,)).fetchall():
            d = {**dict(zip(qcols, q)), "session_id": new_id}
            _exec(conn, f"INSERT INTO question_snapshots ({', '.join(qcols)}) VALUES ({', '.join('?' * len(qcols))})",
                  [d[c] for c in qcols])
        delete_sessions(conn, "session_id=?", (session_id,))
        conn.commit()
        return new_id
    finally:
        conn.close()


def questionnaire_checks(quality, phq, gad, phq_items=None, gad_items=None):
    """Questionnaires whose low score may not reflect how the client feels:
    answered in about a second per question, or the same non-zero answer to
    every question. Kept forgiving: a score that already calls for follow-up
    is left alone, and all 'Not at all' is a normal answer unless rushed."""
    q = quality or {}
    rushed = set(q.get("rushed") or [])
    pace = q.get("pace_s_per_item") or {}
    out = []
    for key, score, items in (("phq", phq, phq_items), ("gad", gad, gad_items)):
        if int(score or 0) >= 10:
            continue
        if key in rushed:
            out.append({"q": key, "why": "rushed", "pace": pace.get(key)})
        elif items and len(set(items)) == 1 and items[0] > 0:
            out.append({"q": key, "why": "same", "value": items[0]})
    return out


def note_client_code(clinician_id, code):
    """Remember the highest code used so deleting a client never frees it."""
    n = _code_number(code)
    if not n:
        return
    conn = _conn()
    key = f"client_code_high:{clinician_id}"
    row = _exec(conn, "SELECT value FROM sync_state WHERE key=?", (key,)).fetchone()
    if not row or int(row[0]) < n:
        _exec(conn, "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?,?)", (key, str(n)))
        conn.commit()
    conn.close()


def get_next_tester_id():
    """Return first unused tester ID T-001 … T-100."""
    try:
        conn = _conn()
        rows = _exec(conn,
            "SELECT DISTINCT tester_id FROM normative_sessions").fetchall()
        conn.close()
        used = {r[0] for r in rows}
        for i in range(1, 101):
            candidate = f"T-{i:03d}"
            if candidate not in used:
                return candidate
        return None
    except Exception:
        return None


# ── Overall result ────────────────────────────────────────────────────────────
# The stored flag describes behaviour only. The result a clinician sees must
# also reflect what the client reported: a self-harm answer or severe
# questionnaire scores can never sit under "No concerns".
# REPEAT: too little typing to assess behaviour. It is not a finding, so it
# sits below Follow up; the questionnaires can still raise the result.
_RANK = {"GREEN": 0, "REPEAT": 0.5, "AMBER": 1, "RED": 2}


def overall_status(behaviour_flag, phq, gad, item9):
    """Return (overall_flag, reasons) combining behaviour, PHQ-9, GAD-7 and item 9.

    A session with too little typing is REPEAT unless a questionnaire or a
    self-harm answer needs follow-up on its own."""
    flag = behaviour_flag if behaviour_flag in _RANK else "AMBER"
    reasons = []
    phq, gad, item9 = int(phq or 0), int(gad or 0), int(item9 or 0)

    def raise_to(level, why):
        nonlocal flag
        if _RANK[level] > _RANK[flag]:
            flag = level
        reasons.append((_RANK[level], why))

    if item9 > 0:
        raise_to("RED", "self-harm answer on PHQ-9 question 9")
    if phq >= 20:
        raise_to("RED", f"severe depressive symptoms (PHQ-9 {phq})")
    elif phq >= 10:
        raise_to("AMBER", f"PHQ-9 {phq} is at or above the screening cut-off of 10")
    if gad >= 15:
        raise_to("RED", f"severe anxiety symptoms (GAD-7 {gad})")
    elif gad >= 10:
        raise_to("AMBER", f"GAD-7 {gad} is at or above the screening cut-off of 10")
    # The reason that decided the result comes first
    return flag, [why for _, why in sorted(reasons, key=lambda r: -r[0])]


# ── Cloud sync tracking ───────────────────────────────────────────────────────
# Offline-first: every change is written here first. Accounts carry
# sync_dirty, sessions carry synced_at (NULL = not uploaded yet), and deleted
# sessions leave a tombstone so the deletion reaches other devices.

def utc_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "+00:00"


def touch_clinician(conn, clinician_id):
    """Mark an account change (role, status, password) for upload."""
    _exec(conn, "UPDATE clinicians SET updated_at=?, sync_dirty=1 WHERE clinician_id=?",
          (utc_now(), clinician_id))


def delete_sessions(conn, where_sql, params):
    """Delete sessions matching a WHERE clause, leaving tombstones for sync."""
    rows = _exec(conn, f"SELECT session_id, session_uid FROM intake_sessions WHERE {where_sql}", params).fetchall()
    now = utc_now()
    for sid, suid in rows:
        if suid:
            _exec(conn, "INSERT OR REPLACE INTO sync_tombstones (session_uid, deleted_at, pushed) VALUES (?,?,0)",
                  (suid, now))
        _exec(conn, "DELETE FROM question_snapshots WHERE session_id=?", (sid,))
        _exec(conn, "DELETE FROM intake_sessions WHERE session_id=?", (sid,))
    return len(rows)


def get_sync_state(key, default=None):
    try:
        conn = _conn()
        row = _exec(conn, "SELECT value FROM sync_state WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


def set_sync_state(key, value):
    conn = _conn()
    _exec(conn, "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?,?)", (key, str(value)))
    conn.commit(); conn.close()


_ACCOUNT_FIELDS = ("clinician_id", "account_uid", "name", "password_hash", "role", "status",
                   "created_at", "updated_at")


def get_dirty_accounts():
    conn = _conn()
    rows = _exec(conn, f"SELECT {', '.join(_ACCOUNT_FIELDS)} FROM clinicians "
                       "WHERE sync_dirty=1 AND password_hash IS NOT NULL AND password_hash != ''").fetchall()
    conn.close()
    return [dict(zip(_ACCOUNT_FIELDS, r)) for r in rows]


def mark_account_synced(clinician_id, updated_at):
    """Clear the flag unless the account changed again during the upload."""
    conn = _conn()
    _exec(conn, "UPDATE clinicians SET sync_dirty=0 WHERE clinician_id=? AND updated_at=?",
          (clinician_id, updated_at))
    conn.commit(); conn.close()


def apply_remote_account(acc):
    """Insert or update an account from the cloud (newest change wins)."""
    conn = _conn()
    try:
        local = _exec(conn, "SELECT account_uid, updated_at FROM clinicians WHERE clinician_id=?",
                      (acc["clinician_id"],)).fetchone()
        if local is None:
            name = acc["name"]
            if _exec(conn, "SELECT 1 FROM clinicians WHERE name=?", (name,)).fetchone():
                name = f"{name} ({acc['clinician_id']})"
            _exec(conn, """INSERT INTO clinicians (clinician_id, name, password, password_hash, role, status,
                           failed_attempts, created_at, account_uid, updated_at, sync_dirty)
                           VALUES (?,?,'',?,?,?,0,?,?,?,0)""",
                  (acc["clinician_id"], name, acc["password_hash"], acc["role"], acc["status"],
                   acc.get("created_at"), acc["account_uid"], acc["updated_at"]))
        elif local[0] == acc["account_uid"] and (local[1] or "") < acc["updated_at"]:
            _exec(conn, """UPDATE clinicians SET password_hash=?, role=?, status=?, updated_at=?, sync_dirty=0
                           WHERE clinician_id=?""",
                  (acc["password_hash"], acc["role"], acc["status"], acc["updated_at"], acc["clinician_id"]))
            if acc["status"] == "disabled":
                _exec(conn, "UPDATE security_sessions SET revoked_at=? WHERE clinician_id=? AND revoked_at IS NULL",
                      (datetime.now().isoformat(timespec="seconds"), acc["clinician_id"]))
        conn.commit()
    finally:
        conn.close()


def reassign_clinician_id(old_id, taken_ids):
    """
    Two devices created different accounts with the same ID while offline.
    The one that reached the cloud second moves to the next free ID, and its
    sessions follow it. Returns the new ID.
    """
    conn = _conn()
    try:
        year = str(old_id)[:4]
        used = {r[0] for r in _exec(conn, "SELECT clinician_id FROM clinicians").fetchall()} | set(taken_ids)
        new_id = next(i for i in (int(f"{year}{n:03d}") for n in range(1, 1000)) if i not in used)
        for table in ("clinicians", "intake_sessions", "consent_records", "security_sessions"):
            _exec(conn, f"UPDATE {table} SET clinician_id=? WHERE clinician_id=?", (new_id, old_id))
        touch_clinician(conn, new_id)
        _exec(conn, "UPDATE intake_sessions SET synced_at=NULL WHERE clinician_id=?", (new_id,))
        _exec(conn, "UPDATE security_sessions SET revoked_at=? WHERE clinician_id=? AND revoked_at IS NULL",
              (datetime.now().isoformat(timespec="seconds"), new_id))
        conn.commit()
        return new_id
    finally:
        conn.close()


_SESSION_LOCAL_ONLY = {"session_id", "synced_at"}


def _session_columns(conn):
    return [r[1] for r in _exec(conn, "PRAGMA table_info(intake_sessions)").fetchall()]


def get_unsynced_sessions(limit=50):
    """Sessions not yet uploaded: [{session_id, data: {column: value}}]."""
    try:
        conn = _conn()
        cols = _session_columns(conn)
        rows = _exec(conn, f"SELECT {', '.join(cols)} FROM intake_sessions WHERE synced_at IS NULL "
                           "AND session_uid IS NOT NULL ORDER BY session_id ASC LIMIT ?", (limit,)).fetchall()
        conn.close()
        out = []
        for r in rows:
            row = dict(zip(cols, r))
            out.append({"session_id": row["session_id"],
                        "data": {k: v for k, v in row.items() if k not in _SESSION_LOCAL_ONLY}})
        return out
    except Exception as e:
        logger.error(f"get_unsynced_sessions error: {e}")
        return []


def mark_session_synced(session_id):
    """Record that a session has been uploaded to the cloud."""
    try:
        conn = _conn()
        _exec(conn, "UPDATE intake_sessions SET synced_at=? WHERE session_id=?", (utc_now(), session_id))
        conn.commit(); conn.close()
        return True
    except Exception as e:
        logger.error(f"mark_session_synced error: {e}")
        return False


def get_pending_tombstones():
    conn = _conn()
    rows = _exec(conn, "SELECT session_uid, deleted_at FROM sync_tombstones WHERE pushed=0").fetchall()
    conn.close()
    return rows


def mark_tombstone_pushed(session_uid):
    conn = _conn()
    _exec(conn, "UPDATE sync_tombstones SET pushed=1 WHERE session_uid=?", (session_uid,))
    conn.commit(); conn.close()


def apply_remote_session(session_uid, data, deleted_at):
    """Insert a session from another device, or apply its deletion."""
    conn = _conn()
    try:
        local = _exec(conn, "SELECT session_id FROM intake_sessions WHERE session_uid=?", (session_uid,)).fetchone()
        if deleted_at:
            if local:
                _exec(conn, "DELETE FROM question_snapshots WHERE session_id=?", (local[0],))
                _exec(conn, "DELETE FROM intake_sessions WHERE session_id=?", (local[0],))
            _exec(conn, "INSERT OR REPLACE INTO sync_tombstones (session_uid, deleted_at, pushed) VALUES (?,?,1)",
                  (session_uid, str(deleted_at)))
        elif not local and not _exec(conn, "SELECT 1 FROM sync_tombstones WHERE session_uid=?",
                                     (session_uid,)).fetchone():
            if data.get("fuzzy_label") == "Insufficient Data" and data.get("flag") == "AMBER":
                data = {**data, "flag": "REPEAT"}       # uploaded by an older build
            cols = [c for c in _session_columns(conn) if c in data and c not in _SESSION_LOCAL_ONLY]
            sid = _insert_returning(conn, f"INSERT INTO intake_sessions ({', '.join(cols)}, synced_at) "
                                          f"VALUES ({', '.join('?' * len(cols))}, ?)",
                                    (*[data[c] for c in cols], utc_now()))
            for snap in json.loads(data.get("question_snapshots_json") or "[]"):
                _exec(conn, """INSERT INTO question_snapshots
                    (session_id, item_id, group_id, level, domain_label, t2_score, psi, pai, flag,
                     flight_time, pause_freq, response_len, hover_words_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sid, snap.get("item_id"), snap.get("group_id"), snap.get("level"), snap.get("domain_label"),
                     _clean(snap.get("t2_score", 0)), _clean(snap.get("psi", 0)), _clean(snap.get("pai", 0)),
                     snap.get("flag"), _clean(snap.get("flight_time", 0)), _clean(snap.get("pause_freq", 0)),
                     snap.get("response_len", 0), json.dumps(snap.get("hover_words") or [])))
        conn.commit()
    finally:
        conn.close()


def get_unsynced_count():
    """Changes waiting for upload: sessions, deletions and accounts."""
    try:
        conn = _conn()
        n = _exec(conn, "SELECT COUNT(*) FROM intake_sessions WHERE synced_at IS NULL").fetchone()[0]
        n += _exec(conn, "SELECT COUNT(*) FROM sync_tombstones WHERE pushed=0").fetchone()[0]
        n += _exec(conn, "SELECT COUNT(*) FROM clinicians WHERE sync_dirty=1").fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0
