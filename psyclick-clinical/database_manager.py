"""
database_manager_offline.py — PsyClick v4 OFFLINE EDITION
SQLite ONLY — No Supabase/PostgreSQL/Cloud — Completely Local & Offline

This version uses ONLY local SQLite database.
No network connections, no configuration files, no external dependencies.
Perfect for air-gapped clinical environments and demo deployments.
"""
import sqlite3, math, json, os, sys, time, hashlib, secrets
import logging
from datetime import datetime, timedelta

# Configure logging for database operations
logger = logging.getLogger(__name__)
_log_handler = logging.StreamHandler(sys.stderr)
_log_handler.setFormatter(logging.Formatter('[PsyClick DB] %(levelname)s: %(message)s'))
logger.addHandler(_log_handler)
logger.setLevel(logging.WARNING)


# ── OFFLINE: SQLite ONLY ──────────────────────────────────────────────────────

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

    # Determine base directory
    if getattr(sys, 'frozen', False):
        base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'PsyClick')
    else:
        base = os.path.dirname(os.path.abspath(__file__))
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
                created_at       TEXT DEFAULT (datetime('now'))
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
                synced_at       TEXT DEFAULT NULL
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

    try:
        conn.commit()
    except Exception:
        pass
    conn.close()

    # Seed normative stats if the table is empty
    _seed_normative_stats()


def _seed_normative_stats():
    """
    Pre-seed normative_stats from the 102-session healthy-tester population
    (110 collected; 3 cold-start artifacts excluded by T²/threshold ratio >10×).

    Cross-validated against BAT calibration values:
      PSI  p99 = 39.1050  ✓
      PAI  p99 = 107.8280 ✓
      T²-ratio p99 = 6.9975 ✓

    Only runs when normative_stats is empty — never overwrites existing data.
    """
    # Derived from CURRENT DATABASE MERGED.csv, T-format tester rows only,
    # excluding IDs 1-3 (T-001/T-002/T-003 first sessions — EWMA cold-start).
    SEED = {
        't2_score':         {'mean': 20.792655, 'sd': 26.479331, 'count': 102},
        'psi':              {'mean':  6.500542, 'sd':  9.169439, 'count': 102},
        'pai':              {'mean': 14.801972, 'sd': 24.432572, 'count': 102},
        'phq_score':        {'mean':  4.676471, 'sd':  1.791961, 'count': 102},
        'gad_score':        {'mean':  4.156863, 'sd':  2.151422, 'count': 102},
        'flight_time_mean': {'mean':  0.163393, 'sd':  0.064421, 'count': 102},
    }
    try:
        conn = _conn()
        existing = _exec(conn, "SELECT COUNT(*) FROM normative_stats").fetchone()[0]
        if existing > 0:
            conn.close()
            return  # already populated — don't overwrite
        for metric, s in SEED.items():
            _exec(conn, """
                INSERT OR REPLACE INTO normative_stats (metric, norm_mean, norm_sd, count)
                VALUES (?, ?, ?, ?)
            """, (metric, s['mean'], s['sd'], s['count']))
        conn.commit()
        conn.close()
        logger.info('[DB] Seeded normative_stats from 102-session population baseline.')
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

def log_audit(actor, action, detail=None, actor_id=None, outcome="success"):
    """Append a hash-chained audit event without storing credentials or tokens."""
    try:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = _conn()
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
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to log audit event: actor={actor}, action={action}, detail={detail}, error={str(e)}")
        return False


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


def compute_normative_stats():
    conn = _conn()
    rows = _exec(conn, """
        SELECT t2_score, psi, pai, phq_score, gad_score, flight_time_mean
        FROM normative_sessions
    """).fetchall()
    conn.close()
    if not rows:
        return False

    n    = len(rows)
    cols = ['t2_score', 'psi', 'pai', 'phq_score', 'gad_score', 'flight_time_mean']
    stats = {}
    for i, col in enumerate(cols):
        vals = [float(r[i] or 0) for r in rows]
        mean = sum(vals) / n
        sd   = math.sqrt(sum((v - mean) ** 2 for v in vals) / (n - 1)) if n > 1 else 1.0
        stats[col] = (mean, max(sd, 0.0001), n)

    conn = _conn()
    for metric, (mean, sd, count) in stats.items():
        _exec(conn, """
            INSERT OR REPLACE INTO normative_stats (metric, norm_mean, norm_sd, count)
            VALUES (?,?,?,?)
        """, (metric, mean, sd, count))
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

        result = {}
        for metric, pval in patient_vals.items():
            if metric in norm and norm[metric]["sd"] > 0:
                z   = (pval - norm[metric]["mean"]) / norm[metric]["sd"]
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
               (clinician_id, name, password, password_hash, role, status, failed_attempts)
               VALUES (?, ?, '', ?, ?, 'active', 0)""",
            (clinician_id, name, password_hash, assigned_role))
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

        if not password_hash:
            password_hash = _hash_password(password)
        _exec(conn, """
            UPDATE clinicians
            SET password='', password_hash=?, failed_attempts=0,
                locked_until=NULL, last_login_at=?
            WHERE clinician_id=?
        """, (password_hash, now.isoformat(timespec="seconds"), clinician_id))
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

def get_next_client_id(clinician_id=None):
    """Return first unused client ID C-001 … C-100 for this clinician."""
    try:
        conn = _conn()
        if clinician_id:
            rows = _exec(conn,
                "SELECT DISTINCT student_id FROM intake_sessions WHERE clinician_id=?",
                (clinician_id,)).fetchall()
        else:
            rows = _exec(conn,
                "SELECT DISTINCT student_id FROM intake_sessions").fetchall()
        conn.close()
        used = {r[0] for r in rows}
        for i in range(1, 101):
            candidate = f"C-{i:03d}"
            if candidate not in used:
                return candidate
        return None
    except Exception:
        return None


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


# ── Cloud sync tracking ───────────────────────────────────────────────────────

def get_unsynced_sessions(limit=50):
    """Return intake_sessions rows that have not yet been synced to the cloud."""
    try:
        conn  = _conn()
        rows  = _exec(conn, """
            SELECT session_id, student_id, clinician_id, timestamp,
                   kbase_mean, kbase_std,
                   mbase_hv, mbase_vv, mbase_tv, mbase_ta, mbase_jerk, mbase_curve,
                   phq_score, phq_hv, phq_vv, phq_tv, phq_ta, phq_jerk, phq_curve,
                   gad_score, gad_hv, gad_vv, gad_tv, gad_ta, gad_jerk, gad_curve,
                   task_k_mean, task_k_std, k_z_score, m_z_score,
                   t2_score, t2_threshold, psi, pai,
                   fuzzy_label, fuzzy_confidence, flag, rationale,
                   domain_t2_json, question_snapshots_json, flight_times_json
            FROM intake_sessions
            WHERE synced_at IS NULL
            ORDER BY session_id ASC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        cols = [
            "session_id", "student_id", "clinician_id", "timestamp",
            "kbase_mean", "kbase_std",
            "mbase_hv", "mbase_vv", "mbase_tv", "mbase_ta", "mbase_jerk", "mbase_curve",
            "phq_score", "phq_hv", "phq_vv", "phq_tv", "phq_ta", "phq_jerk", "phq_curve",
            "gad_score", "gad_hv", "gad_vv", "gad_tv", "gad_ta", "gad_jerk", "gad_curve",
            "task_k_mean", "task_k_std", "k_z_score", "m_z_score",
            "t2_score", "t2_threshold", "psi", "pai",
            "fuzzy_label", "fuzzy_confidence", "flag", "rationale",
            "domain_t2_json", "question_snapshots_json", "flight_times_json",
        ]
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        logger.error(f"get_unsynced_sessions error: {e}")
        return []


def mark_session_synced(session_id):
    """Record that a session has been uploaded to the cloud."""
    try:
        import datetime as _dt
        ts   = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = _conn()
        _exec(conn,
              "UPDATE intake_sessions SET synced_at=? WHERE session_id=?",
              (ts, session_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"mark_session_synced error: {e}")
        return False


def get_unsynced_count():
    """Return the number of sessions not yet synced to the cloud."""
    try:
        conn  = _conn()
        count = _exec(conn,
            "SELECT COUNT(*) FROM intake_sessions WHERE synced_at IS NULL"
        ).fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0
