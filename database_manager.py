"""
database_manager.py  —  PsyClick
Stores one row per session.  EWMA state is NOT stored — it is in-memory only
and discarded after the report is generated (single-session design).

New columns added for the updated pipeline:
    t2_score, t2_threshold, psi, pai, fuzzy_label, fuzzy_confidence,
    flag, rationale
Z-score columns are retained for backward compatibility with the Patients
history view.
"""

import sqlite3
import math

DB_NAME = "psyclick_data.db"


def init_db():
    conn   = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intake_sessions (
            session_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id   TEXT,
            timestamp    TEXT DEFAULT (datetime('now')),

            -- Keyboard baseline (retained for reference)
            kbase_mean REAL, kbase_std REAL,

            -- Mouse baseline (retained for reference)
            mbase_hv REAL, mbase_vv REAL, mbase_tv REAL,
            mbase_ta REAL, mbase_jerk REAL, mbase_curve REAL,

            -- PHQ-9
            phq_score INTEGER,
            phq_hv REAL, phq_vv REAL, phq_tv REAL,
            phq_ta REAL, phq_jerk REAL, phq_curve REAL,

            -- GAD-7
            gad_score INTEGER,
            gad_hv REAL, gad_vv REAL, gad_tv REAL,
            gad_ta REAL, gad_jerk REAL, gad_curve REAL,

            -- Emotional task raw
            task_k_mean REAL, task_k_std REAL,

            -- Legacy Z-scores (kept for Patients history page)
            k_z_score REAL,
            m_z_score REAL,

            -- NEW: Pipeline outputs
            t2_score        REAL,
            t2_threshold    REAL,
            psi             REAL,
            pai             REAL,
            fuzzy_label     TEXT,
            fuzzy_confidence REAL,
            flag            TEXT,
            rationale       TEXT
        )
    """)
    conn.commit()
    conn.close()


def _clean(val):
    """Converts Nones and ALL types of NaNs (including Numpy) to 0.0"""
    if val is None:
        return 0.0
    
    try:
        # Forcing to float catches both standard Python NaNs and numpy.float64 NaNs
        if math.isnan(float(val)):
            return 0.0
    except (ValueError, TypeError):
        # If the value is a string (like the patient ID or labels), leave it alone
        pass
        
    return val


def save_full_intake(data):
    conn   = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    ae = data.get("analysis", {}) or {}

    # Pack all values into a list first
    raw_values = [
        data["student_id"],
        data["kbase"]["mean_flight"], data["kbase"]["std_flight"],
        data["mbase"]["hv"], data["mbase"]["vv"], data["mbase"]["tv"],
        data["mbase"]["ta"], data["mbase"]["jerk"], data["mbase"]["curvature"],
        data["phq"]["score"],
        data["phq"]["mouse"]["hv"], data["phq"]["mouse"]["vv"],
        data["phq"]["mouse"]["tv"], data["phq"]["mouse"]["ta"],
        data["phq"]["mouse"]["jerk"], data["phq"]["mouse"]["curvature"],
        data["gad"]["score"],
        data["gad"]["mouse"]["hv"], data["gad"]["mouse"]["vv"],
        data["gad"]["mouse"]["tv"], data["gad"]["mouse"]["ta"],
        data["gad"]["mouse"]["jerk"], data["gad"]["mouse"]["curvature"],
        data["task"]["mean_flight"], data["task"]["std_flight"],
        data.get("k_z_score", 0), data.get("m_z_score", 0),
        ae.get("t2_score"), ae.get("t2_threshold"), ae.get("psi"), ae.get("pai"),
        ae.get("label"), ae.get("confidence"), ae.get("flag"), ae.get("rationale")
    ]

    # Clean the list and convert to a tuple for SQLite
    safe_values = tuple(_clean(v) for v in raw_values)

    cursor.execute("""
        INSERT INTO intake_sessions (
            student_id,
            kbase_mean, kbase_std,
            mbase_hv, mbase_vv, mbase_tv, mbase_ta, mbase_jerk, mbase_curve,
            phq_score, phq_hv, phq_vv, phq_tv, phq_ta, phq_jerk, phq_curve,
            gad_score, gad_hv, gad_vv, gad_tv, gad_ta, gad_jerk, gad_curve,
            task_k_mean, task_k_std,
            k_z_score, m_z_score,
            t2_score, t2_threshold, psi, pai,
            fuzzy_label, fuzzy_confidence, flag, rationale
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, safe_values)
    
    conn.commit()
    conn.close()
