"""
database_manager.py — PsyClick v3
Dual-mode: SQLite (local/dev) OR PostgreSQL (Supabase/cloud).

To use Supabase, create  %APPDATA%\\PsyClick\\config.json :
{
  "database_url": "postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres"
}
Or set the environment variable  PSYCLICK_DB_URL  before launching.
"""
import sqlite3, math, json, os, sys, time
import logging

# Configure logging for database operations
logger = logging.getLogger(__name__)
_log_handler = logging.StreamHandler(sys.stderr)
_log_handler.setFormatter(logging.Formatter('[PsyClick DB] %(levelname)s: %(message)s'))
logger.addHandler(_log_handler)
logger.setLevel(logging.WARNING)


# ── DB backend detection ──────────────────────────────────────────────────────

DB_NAME = None   # SQLite file path  (used when Postgres not configured)
_PG_URL = None   # PostgreSQL URL    (overrides SQLite when set)
_DB_STATUS = {
    "configured_backend": "unknown",
    "active_backend": "unknown",
    "fallback_active": False,
    "available": True,
    "last_error": None,
    "last_error_at": None,
}


class DatabaseUnavailableError(RuntimeError):
    """Raised when the configured cloud database cannot be reached."""


def _resolve_defaults():
    global DB_NAME, _PG_URL

    # Determine base directory
    if getattr(sys, 'frozen', False):
        base = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'PsyClick')
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base, exist_ok=True)
    DB_NAME = os.path.join(base, 'psyclick_data.db')

    # 0. CREDENTIALS REMOVED — Use environment variables or config.json instead
    # Hardcoded credentials are a security risk and have been removed.
    # Set PSYCLICK_DB_URL environment variable or create config.json
    _BUILTIN_DB_URL = None
    if _BUILTIN_DB_URL:
        _PG_URL = _BUILTIN_DB_URL
        _DB_STATUS.update({
            "configured_backend": "postgres",
            "active_backend": "postgres",
            "fallback_active": False,
            "available": True,
        })
        return

    # 1. Environment variable wins
    env_url = os.environ.get('PSYCLICK_DB_URL', '').strip()
    if env_url.startswith(('postgresql://', 'postgres://')):
        _PG_URL = env_url
        _DB_STATUS.update({
            "configured_backend": "postgres",
            "active_backend": "postgres",
            "fallback_active": False,
            "available": True,
        })
        return

    # 2. config.json discovery (multiple paths for packaged installs)
    cfg_candidates = [os.path.join(base, 'config.json')]
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(getattr(sys, 'executable', '')))
        cfg_candidates.extend([
            os.path.join(exe_dir, 'config.json'),
            os.path.join(exe_dir, '..', 'config.json'),
            os.path.join(exe_dir, '..', '..', 'config.json'),
            os.path.join(os.getcwd(), 'config.json'),
        ])
    for cfg_path in cfg_candidates:
        cfg_path = os.path.normpath(os.path.abspath(cfg_path))
        if not os.path.exists(cfg_path):
            continue
        try:
            with open(cfg_path, encoding='utf-8-sig') as f:
                cfg = json.load(f)
            url = (cfg.get('database_url') or cfg.get('database') or '').strip()
            if url.startswith(('postgresql://', 'postgres://')):
                _PG_URL = url
                _DB_STATUS.update({
                    "configured_backend": "postgres",
                    "active_backend": "postgres",
                    "fallback_active": False,
                    "available": True,
                })
                return
        except Exception:
            continue

    # 3. Fall back to local SQLite
    _DB_STATUS.update({
        "configured_backend": "sqlite",
        "active_backend": "sqlite",
        "fallback_active": False,
        "available": True,
    })


_resolve_defaults()


def reapply_db_config():
    """
    Re-run discovery after env vars are guaranteed set (e.g. Electron child process).
    Safe to call once at API startup.
    """
    global DB_NAME, _PG_URL
    DB_NAME = None
    _PG_URL = None
    _resolve_defaults()


def get_db_mode():
    """Return ('postgres', url) or ('sqlite', path) for diagnostics (URL host only, no password)."""
    if _PG_URL:
        try:
            from urllib.parse import urlparse
            u = urlparse(_PG_URL)
            host = u.hostname or ''
            return 'postgres', {'host': host, 'port': u.port or 5432, 'dbname': (u.path or '/').lstrip('/') or 'postgres'}
        except Exception:
            return 'postgres', {'host': '(parse error)'}
    return 'sqlite', {'path': DB_NAME}


def _record_db_error(exc):
    _DB_STATUS.update({
        "active_backend": "postgres" if _PG_URL else "sqlite",
        "available": False,
        "last_error": str(exc),
        "last_error_at": time.strftime('%Y-%m-%d %H:%M:%S'),
    })


def get_db_status():
    """Return sanitized runtime DB status for UI/API diagnostics."""
    mode, info = get_db_mode()
    status = dict(_DB_STATUS)
    status.update({"backend": mode, "info": info})
    return status


def configure_db(path_or_url):
    """Override the database path or URL at runtime (called from api_server.py)."""
    global DB_NAME, _PG_URL
    if path_or_url.startswith(('postgresql://', 'postgres://')):
        _PG_URL = path_or_url
        DB_NAME = None
        _DB_STATUS.update({
            "configured_backend": "postgres",
            "active_backend": "postgres",
            "fallback_active": False,
            "available": True,
            "last_error": None,
            "last_error_at": None,
        })
    else:
        DB_NAME = path_or_url
        _PG_URL = None
        _DB_STATUS.update({
            "configured_backend": "sqlite",
            "active_backend": "sqlite",
            "fallback_active": False,
            "available": True,
            "last_error": None,
            "last_error_at": None,
        })


# ── Connection / SQL helpers ──────────────────────────────────────────────────

def _is_pg():
    return _PG_URL is not None


def _conn():
    if _is_pg():
        import psycopg2
        try:
            conn = psycopg2.connect(_PG_URL, connect_timeout=5)
            _DB_STATUS.update({
                "active_backend": "postgres",
                "available": True,
                "fallback_active": False,
                "last_error": None,
                "last_error_at": None,
            })
            return conn
        except Exception as exc:
            _record_db_error(exc)
            raise DatabaseUnavailableError(
                "Supabase connection is unavailable. Please check the bundled config.json "
                "database_url, password, pooler host, tenant/project reference, and network access."
            ) from exc
    return sqlite3.connect(DB_NAME)


def _ph():
    """Parameter placeholder: %s (Postgres) or ? (SQLite)."""
    return '%s' if _is_pg() else '?'


def _sql(s):
    """Adapt SQLite DDL/DML to PostgreSQL syntax when needed."""
    if not _is_pg():
        return s
    for old, new in [
        ('?',                             '%s'),
        (' AUTOINCREMENT',                ''),
        ('INTEGER PRIMARY KEY',           'SERIAL PRIMARY KEY'),
        # NOTE: order matters — localtime variant must come before bare datetime('now')
        ("datetime('now','localtime')",   "TO_CHAR(NOW() AT TIME ZONE 'Asia/Manila', 'YYYY-MM-DD HH24:MI:SS')"),
        ("datetime('now')",               "TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')"),
        # After the datetime() replacements the default becomes TEXT DEFAULT (TO_CHAR(...))
        # which is valid; remove the wrapping parens only for the NOW()-only case (no longer hit)
        ('TEXT DEFAULT (NOW())',          "TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')"),
    ]:
        s = s.replace(old, new)
    return s


def _exec(conn, sql, params=None):
    """Execute SQL on either backend; return cursor."""
    c = conn.cursor()
    c.execute(_sql(sql), params or ())
    return c


def _insert_returning(conn, sql, params, returning_col='id'):
    """
    Execute an INSERT and return the new row's primary key.
    Postgres needs RETURNING; SQLite uses lastrowid.
    """
    if _is_pg():
        # Add RETURNING clause if not already present
        ret_sql = _sql(sql)
        if 'RETURNING' not in ret_sql.upper():
            ret_sql += f' RETURNING {returning_col}'
        c = conn.cursor()
        c.execute(ret_sql, params)
        return c.fetchone()[0]
    else:
        c = conn.cursor()
        c.execute(sql, params)
        return c.lastrowid


def _tables(conn):
    c = conn.cursor()
    if _is_pg():
        c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    else:
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in c.fetchall()]


def _add_col(conn, table, col, coltype):
    try:
        c = conn.cursor()
        if _is_pg():
            c.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {coltype}')
        else:
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
        conn.commit()

    # Each table is created in its own try-except + commit so that a DDL error on
    # one table (e.g. already-different schema in Supabase) does NOT abort the
    # whole transaction and leave every other table un-created.

    _DDL_TABLES = [
        # ── Clinicians (year-based IDs: YYYYNNN format) ──────────────────────
        ("clinicians", """
            CREATE TABLE IF NOT EXISTS clinicians (
                clinician_id     INTEGER PRIMARY KEY,
                name             TEXT NOT NULL UNIQUE,
                password         TEXT NOT NULL,
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
                flight_times_json TEXT
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
                action    TEXT,
                detail    TEXT,
                timestamp TEXT DEFAULT (datetime('now','localtime'))
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
            # Roll back only this statement so the connection stays usable
            try:
                conn.rollback()
            except Exception:
                pass

    # Migration guard for question_shown_at (runs after question_snapshots is ensured)
    _add_col(conn, 'question_snapshots', 'question_shown_at', 'REAL')

    try:
        conn.commit()
    except Exception:
        pass
    conn.close()


# ── Utility ───────────────────────────────────────────────────────────────────

def _clean(val):
    if val is None:
        return 0.0
    try:
        val = float(val)  # ← CONVERT first (handles numpy.float64, etc.)
        if math.isnan(val):
            return 0.0
        return val
    except (ValueError, TypeError):
        return 0.0


def _flatten_ae(ae):
    """Normalise an analysis-engine result to flat scalar fields.

    Standard engine  → psi/pai are floats, t2_score/t2_threshold are floats.
    Clinical engine  → psi/pai are dicts {total, ...}, t2_score lives under
                       t2_scores.hybrid, t2_threshold under t2_thresholds.adjusted.
    Returns a plain dict with scalar values so psycopg2 can serialise them.
    """
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
    ph = _ph()

    clinician_id = data.get("clinician_id")
    if clinician_id is not None:
        try:
            clinician_id = int(clinician_id)
        except (ValueError, TypeError):
            clinician_id = None

    # Build parameter tuple in EXACT column order:
    # (student_id, clinician_id, 30-numeric-values, label, confidence, flag, rationale, 3-json-strings)

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
        ae.get("label", ""),                          # fuzzy_label (string)
        _clean(ae.get("confidence", 0.0)),            # fuzzy_confidence (numeric)
        ae.get("flag", "GREEN"),                      # flag (string)
        ae.get("rationale", ""),                      # rationale (string)
        json.dumps(data.get("visuals", {}).get("domain_t2", {})),  # domain_t2_json
        json.dumps([
            {k: v for k, v in s.items() if k not in ("raw_flights", "pause_coords")}
            for s in data.get("visuals", {}).get("question_snapshots", [])
        ]),  # question_snapshots_json
        json.dumps(data.get("visuals", {}).get("flight_times", [])),  # flight_times_json
    )

    placeholders = ','.join([ph] * len(safe))
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
    """, safe, returning_col='session_id')

    # Per-question snapshots
    snap_ph = ','.join([ph] * 13)
    for snap in data.get("visuals", {}).get("question_snapshots", []):
        try:
            hover_json = json.dumps(snap.get("hover_words", []) or [])
        except (TypeError, ValueError):
            hover_json = json.dumps([])

        _exec(conn, f"""
            INSERT INTO question_snapshots
              (session_id, item_id, group_id, level, domain_label,
               t2_score, psi, pai, flag, flight_time, pause_freq,
               response_len, hover_words_json)
            VALUES ({snap_ph})
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

def log_audit(actor, action, detail=None):
    """
    Log an audit event to the database.

    Args:
        actor: 'clinician' or 'patient'
        action: Action name (e.g., 'Logged in', 'Started Session')
        detail: Optional additional detail

    Returns:
        True if successful, False if failed
    """
    try:
        import datetime as _dt
        # Always supply the timestamp explicitly so we never depend on the column DEFAULT.
        # The DEFAULT (datetime('now','localtime')) becomes TO_CHAR(NOW()...) in PostgreSQL
        # via _sql(), but PostgreSQL cannot implicitly cast timestamptz to TEXT in a DEFAULT
        # clause, so rows inserted without an explicit timestamp would fail on fresh tables.
        ts = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = _conn()
        ph = _ph()
        _exec(conn,
              f"INSERT INTO audit_log (actor, action, detail, timestamp) VALUES ({ph},{ph},{ph},{ph})",
              (actor, action, detail, ts))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to log audit event: actor={actor}, action={action}, detail={detail}, error={str(e)}")
        return False


def get_audit_logs(actor=None):
    """
    Retrieve audit log entries.

    Args:
        actor: Optional filter ('clinician' or 'patient'). If None, returns all.

    Returns:
        List of tuples: [(timestamp, [actor,] action, detail), ...] or [] on error
    """
    try:
        conn = _conn()
        ph = _ph()
        if actor:
            rows = _exec(conn,
                f"SELECT timestamp, action, detail FROM audit_log WHERE actor={ph} ORDER BY log_id DESC",
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


# ── Session queries ───────────────────────────────────────────────────────────

def get_student_session_count(student_id, clinician_id=None):
    try:
        conn = _conn()
        ph = _ph()
        if clinician_id:
            count = _exec(conn,
                f"SELECT COUNT(*) FROM intake_sessions WHERE student_id={ph} AND clinician_id={ph}",
                (student_id, clinician_id)).fetchone()[0]
        else:
            count = _exec(conn,
                f"SELECT COUNT(*) FROM intake_sessions WHERE student_id={ph}",
                (student_id,)).fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Failed to get session count for student {student_id}: {str(e)}")
        return 0


def get_sessions_by_student(student_id):
    try:
        conn = _conn()
        ph = _ph()
        rows = _exec(conn, f"""
            SELECT session_id, timestamp, phq_score, gad_score, flag
            FROM intake_sessions WHERE student_id={ph}
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
    ph   = _ph()
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
    placeholders = ','.join([ph] * len(params))
    _exec(conn, f"""
        INSERT INTO normative_sessions
          (tester_id, t2_score, t2_threshold, psi, pai,
           phq_score, gad_score, kbase_mean, kbase_std, flight_time_mean,
           domain_t2_json, level_t2_json)
        VALUES ({placeholders})
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
    ph   = _ph()
    for metric, (mean, sd, count) in stats.items():
        if _is_pg():
            _exec(conn, f"""
                INSERT INTO normative_stats (metric, norm_mean, norm_sd, count)
                VALUES ({ph},{ph},{ph},{ph})
                ON CONFLICT (metric) DO UPDATE
                  SET norm_mean=EXCLUDED.norm_mean, norm_sd=EXCLUDED.norm_sd,
                      count=EXCLUDED.count, computed_at=NOW()
            """, (metric, mean, sd, count))
        else:
            _exec(conn, f"""
                INSERT OR REPLACE INTO normative_stats (metric, norm_mean, norm_sd, count)
                VALUES ({ph},{ph},{ph},{ph})
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
        conn = _conn()
        ph   = _ph()

        row = _exec(conn, f"""
            SELECT t2_score, psi, pai, phq_score, gad_score
            FROM intake_sessions WHERE session_id={ph}
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


# ── Clinician registration & management ────────────────────────────────────────

def register_clinician(name, password):
    """
    Register a new clinician with auto-incrementing ID format: YYYYNNN
    (e.g., 2026001, 2026002, etc).
    Returns: (success, clinician_id, error_msg)
    """
    try:
        from datetime import datetime

        conn = _conn()
        ph = _ph()

        # Check if name already exists
        existing = _exec(conn,
            f"SELECT clinician_id FROM clinicians WHERE name={ph}",
            (name,)).fetchone()

        if existing:
            conn.close()
            return False, None, "Name already registered"

        # Generate new ID: current year + 3-digit sequence
        current_year = datetime.now().year
        year_prefix = str(current_year)
        year_start = int(f"{year_prefix}000")
        year_end = int(f"{year_prefix}999")

        # Find the highest sequence number for this year (works in both SQLite and PostgreSQL)
        latest = _exec(conn,
            f"SELECT MAX(clinician_id) FROM clinicians WHERE clinician_id >= {ph} AND clinician_id <= {ph}",
            (year_start, year_end)).fetchone()

        if latest and latest[0]:
            next_seq = (latest[0] % 1000) + 1
        else:
            next_seq = 1

        clinician_id = int(f"{year_prefix}{next_seq:03d}")

        # Insert new clinician with generated ID
        _exec(conn, f"""
            INSERT INTO clinicians (clinician_id, name, password)
            VALUES ({ph}, {ph}, {ph})
        """, (clinician_id, name, password))

        conn.commit()
        conn.close()

        return True, clinician_id, None
    except Exception as e:
        return False, None, str(e)


def get_clinician_by_id(clinician_id):
    """Get clinician details by ID."""
    try:
        conn = _conn()
        ph = _ph()
        row = _exec(
            conn,
            f"SELECT clinician_id, name FROM clinicians WHERE clinician_id={ph}",
            (clinician_id,),
        ).fetchone()
        conn.close()

        if not row:
            return None

        return {"clinician_id": row[0], "name": row[1]}
    except Exception:
        return None


def verify_clinician(clinician_id, password):
    """Verify clinician login."""
    try:
        conn = _conn()
        ph = _ph()
        row = _exec(conn,
            f"SELECT password, name FROM clinicians WHERE clinician_id={ph}",
            (clinician_id,)).fetchone()
        conn.close()

        if not row:
            return False, "Clinician ID not found"

        if row[0] != password:
            return False, "Incorrect password"

        return True, row[1]  # Return name on success
    except Exception as e:
        return False, str(e)


# ── Auto-ID generation ────────────────────────────────────────────────────────

def get_next_client_id(clinician_id=None):
    """Return the first unused client ID in the format C-001 to C-100 for this clinician."""
    try:
        conn = _conn()
        ph = _ph()
        if clinician_id:
            rows = _exec(conn,
                f"SELECT DISTINCT student_id FROM intake_sessions WHERE clinician_id={ph}",
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
    """Return the first unused tester ID in the format T-001 to T-100."""
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
