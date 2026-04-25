"""
database_manager.py — PsyClick v3
Extended schema: per-question snapshots stored in question_snapshots table.
Main sessions table retains all original columns for backward compatibility.
"""
import sqlite3, math, json

DB_NAME = "psyclick_data.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c    = conn.cursor()

    # ── Migration: add new columns to existing DB if they don't exist ─────────
    def _add_col(table, col, coltype, default="NULL"):
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype} DEFAULT {default}")
        except Exception:
            pass  # Column already exists

    # Ensure table exists first (will be created below if not)
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    
    if "audit_log" not in tables:
        pass  # will be created below by CREATE TABLE IF NOT EXISTS
    
    if "intake_sessions" in tables:
        _add_col("intake_sessions", "domain_t2_json",           "TEXT")
        _add_col("intake_sessions", "question_snapshots_json",  "TEXT")
        conn.commit()

    # ── Main sessions table  ─────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS intake_sessions (
            session_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id       TEXT,
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
            question_snapshots_json TEXT
        )
    """)

    # ── Per-question snapshots (one row per question per session) ─────────────
    c.execute("""
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
            question_shown_at REAL,
            FOREIGN KEY (session_id) REFERENCES intake_sessions(session_id)
        )
    """)

    # Migration guard for existing databases missing question_shown_at
    try:
        c.execute("ALTER TABLE question_snapshots ADD COLUMN question_shown_at REAL")
        conn.commit()
    except Exception:
        pass  # column already exists
    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        log_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        actor     TEXT,
        action    TEXT,
        detail    TEXT,
        timestamp TEXT DEFAULT (datetime('now','localtime'))
    )
    """)

    conn.commit()
    conn.close()


def _clean(val):
    if val is None:
        return 0.0
    try:
        if math.isnan(float(val)):
            return 0.0
    except (ValueError, TypeError):
        pass
    return val


def save_full_intake(data):
    conn = sqlite3.connect(DB_NAME)
    c    = conn.cursor()

    ae = data.get("analysis", {}) or {}

    raw = [
        data["student_id"],
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
        ae.get("label"), ae.get("confidence"),
        ae.get("flag"), ae.get("rationale"),
        json.dumps(data.get("visuals", {}).get("domain_t2", {})),
        json.dumps([
            {k: v for k, v in s.items() if k not in ("raw_flights", "pause_coords")}
            for s in data.get("visuals", {}).get("question_snapshots", [])
        ]),
    ]

    safe = tuple(_clean(v) for v in raw)

    c.execute("""
        INSERT INTO intake_sessions (
            student_id,
            kbase_mean, kbase_std,
            mbase_hv, mbase_vv, mbase_tv, mbase_ta, mbase_jerk, mbase_curve,
            phq_score, phq_hv, phq_vv, phq_tv, phq_ta, phq_jerk, phq_curve,
            gad_score, gad_hv, gad_vv, gad_tv, gad_ta, gad_jerk, gad_curve,
            task_k_mean, task_k_std,
            k_z_score, m_z_score,
            t2_score, t2_threshold, psi, pai,
            fuzzy_label, fuzzy_confidence, flag, rationale,
            domain_t2_json, question_snapshots_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, safe)

    session_id = c.lastrowid

    # Insert per-question snapshots
    for snap in data.get("visuals", {}).get("question_snapshots", []):
        c.execute("""
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
            _clean(snap.get("t2_score", 0)),
            _clean(snap.get("psi", 0)),
            _clean(snap.get("pai", 0)),
            snap.get("flag", "GREEN"),
            _clean(snap.get("flight_time", 0)),
            _clean(snap.get("pause_freq", 0)),
            snap.get("response_len", 0),
            json.dumps(snap.get("hover_words", [])),
        ))

    conn.commit()
    conn.close()
    return session_id

def log_audit(actor, action, detail=None):
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute(
            "INSERT INTO audit_log (actor, action, detail) VALUES (?,?,?)",
            (actor, action, detail)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # never crash the UI over a log failure

def get_audit_logs(actor=None):
    try:
        conn = sqlite3.connect(DB_NAME)
        if actor:
            rows = conn.execute(
                "SELECT timestamp, action, detail FROM audit_log WHERE actor=? ORDER BY log_id DESC",
                (actor,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT timestamp, actor, action, detail FROM audit_log ORDER BY log_id DESC"
            ).fetchall()
        conn.close()
        return rows
    except Exception:
        return []