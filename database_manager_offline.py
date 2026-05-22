"""
database_manager_offline.py — PsyClick v4 OFFLINE EDITION
SQLite ONLY — No Supabase/PostgreSQL/Cloud — Completely Local & Offline

This version uses ONLY local SQLite database.
No network connections, no configuration files, no external dependencies.
Perfect for air-gapped clinical environments and demo deployments.
"""
import sqlite3, math, json, os, sys, time
import logging

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
        conn.commit()

    # Each table is created in its own try-except + commit
    _DDL_TABLES = [
        # ── Clinicians ────────────────────────────────────────────────────────
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
            try:
                conn.rollback()
            except Exception:
                pass

    # Migration guard for question_shown_at
    _add_col(conn, 'question_snapshots', 'question_shown_at', 'REAL')

    try:
        conn.commit()
    except Exception:
        pass
    conn.close()


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

def log_audit(actor, action, detail=None):
    try:
        import datetime as _dt
        ts = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = _conn()
        _exec(conn,
              "INSERT INTO audit_log (actor, action, detail, timestamp) VALUES (?,?,?,?)",
              (actor, action, detail, ts))
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
