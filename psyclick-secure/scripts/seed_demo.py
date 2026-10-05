"""
seed_demo.py — create the PsyClick demo administrator and its sample clients.

    python scripts/seed_demo.py                 # the app's normal database
    PSYCLICK_DB_PATH=path/to.db python scripts/seed_demo.py

FOR DEMONSTRATION ONLY. Every session is simulated input run through the real
scoring pipeline (see demo_simulation.py), so the results are exactly what
PsyClick computes for that behaviour. The clients belong to the demo account
only, and their sessions are marked so they are never uploaded by cloud sync.

Re-running replaces the demo account's clients; nothing else is touched.
"""

import os
import random
import sys
import zlib
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import logging
logging.disable(logging.WARNING)

import database_manager as db
from backend_controller import PsyClickController
from demo_simulation import run_session

DEMO_NAME     = "Demo Admin (simulation)"
DEMO_PASSWORD = "PsyClickDemo2026"
NOT_FOR_SYNC  = "demo-never-sync"     # synced_at marker: excluded from cloud upload

# Behaviour profiles (see demo_simulation.CALM for the healthy defaults)
NEAR_LIMIT = {"flight": 0.27, "dwell": 0.115, "pause": 0.03}
SLOW_MILD  = {"flight": 0.36, "dwell": 0.13,  "pause": 0.05}
SLOW_MARK  = {"flight": 0.46, "dwell": 0.15,  "pause": 0.07}
ERRATIC    = {"err": 0.32, "jitter": 0.09, "flight": 0.15}
MIXED_MARK = {"flight": 0.42, "dwell": 0.145, "pause": 0.06, "err": 0.3}


def relationships_only(item_id, gid, level):
    return {"flight": 0.85, "dwell": 0.18, "pause": 0.12} if gid == 2 else {}


def grows_with_load(item_id, gid, level):
    return {"A": {}, "B": {"flight": 0.30, "dwell": 0.12, "pause": 0.03},
            "C": {"flight": 0.80, "dwell": 0.175, "pause": 0.11}}[level]


ALL_ITEMS = ["A1", "A2", "B1", "C1", "A3", "B2", "B3", "C2", "A4", "B4", "C3", "C4"]

# Words the cursor rests on while reading (seconds), for the attention heatmap
LINGER_LOW  = {"C4": {"hard?": 1.6, "yourself": 0.9}, "C1": {"yourself": 1.1}}
LINGER_HIGH = {"C4": {"hard?": 3.4, "yourself": 2.2, "describe": 0.8},
               "C1": {"yourself": 2.6, "finish": 1.2}, "C2": {"left": 2.4, "out": 1.8},
               "B3": {"let": 1.4, "down": 2.1}, "C3": {"doubts": 2.0}}
LINGER_REL  = {"C2": {"left": 3.8, "out": 2.9, "group?": 1.2}, "B2": {"family": 2.7, "conflict": 1.9},
               "B3": {"down": 2.4, "important?": 1.1}, "A3": {"misunderstanding": 1.3}}

# client, days ago, questionnaires, behaviour, expected (flag, label or None)
SCENARIOS = [
    # Healthy and stable
    ("DEMO-01", 62, dict(phq=2, gad=1), {}, ("GREEN", "Normal")),
    ("DEMO-01", 3,  dict(phq=3, gad=2), {}, ("GREEN", "Normal")),
    # Early warning: behaviour changes before the questionnaires do
    ("DEMO-02", 75, dict(phq=3, gad=2), {}, ("GREEN", "Normal")),
    ("DEMO-02", 40, dict(phq=4, gad=3), {"task": NEAR_LIMIT, "linger": LINGER_LOW}, ("GREEN", None)),
    ("DEMO-02", 2,  dict(phq=6, gad=4), {"task": SLOW_MILD, "linger": LINGER_HIGH}, ("AMBER", "Psychomotor Retardation")),
    # Worsening to Review now
    ("DEMO-03", 90, dict(phq=6, gad=5), {}, ("GREEN", "Normal")),
    ("DEMO-03", 45, dict(phq=11, gad=8), {"task": SLOW_MILD, "linger": LINGER_LOW}, ("AMBER", "Psychomotor Retardation")),
    ("DEMO-03", 1,  dict(phq=17, gad=12, item9=1), {"task": SLOW_MARK, "linger": LINGER_HIGH,
                                                     "read": {"C4": 24.0, "C1": 17.5}}, ("RED", "Psychomotor Retardation")),
    # Improving with care
    ("DEMO-04", 84, dict(phq=19, gad=16, item9=2), {"task": MIXED_MARK, "linger": LINGER_HIGH,
                                                     "phq_mouse": "restless", "gad_mouse": "restless"}, ("RED", "Mixed Disturbance")),
    ("DEMO-04", 42, dict(phq=13, gad=10), {"task": SLOW_MILD}, ("AMBER", "Psychomotor Retardation")),
    ("DEMO-04", 4,  dict(phq=6, gad=5), {}, ("GREEN", "Normal")),
    # Self-harm answer while behaviour looks typical
    ("DEMO-05", 5,  dict(phq=8, gad=6, item9=1), {"linger": LINGER_LOW}, ("GREEN", "Normal")),
    # Severe on every measure, self-harm nearly every day
    ("DEMO-06", 0,  dict(phq=24, gad=18, item9=3), {"task": MIXED_MARK, "linger": LINGER_HIGH,
                                                     "read": {"C4": 31.0}, "phq_mouse": "restless",
                                                     "gad_mouse": "restless"}, ("RED", "Mixed Disturbance")),
    # High questionnaires, typical behaviour
    ("DEMO-07", 6,  dict(phq=16, gad=15), {}, ("GREEN", "Normal")),
    # Too little typing to score behaviour
    ("DEMO-08", 2,  dict(phq=9, gad=7), {"skip": ALL_ITEMS}, ("AMBER", "Insufficient Data")),
    # Reaction to one topic: relationships
    ("DEMO-09", 8,  dict(phq=7, gad=9), {"task": relationships_only, "linger": LINGER_REL,
                                         "read": {"C2": 26.0, "B2": 15.0}}, (None, None)),
    # Reaction grows with emotional load
    ("DEMO-10", 9,  dict(phq=10, gad=11), {"task": grows_with_load, "linger": LINGER_HIGH}, (None, None)),
    # Within range, leaning towards slowing
    ("DEMO-11", 12, dict(phq=7, gad=6), {"task": {"flight": 0.335, "dwell": 0.125, "pause": 0.045}},
     ("GREEN", "Psychomotor Retardation")),
    # Erratic, error-heavy typing: change in both directions
    ("DEMO-12", 15, dict(phq=12, gad=14), {"task": ERRATIC, "phq_mouse": "restless", "gad_mouse": "restless"},
     ("AMBER", "Mixed Disturbance")),
    # Some prompts left blank
    ("DEMO-13", 20, dict(phq=5, gad=10), {"skip": ["B2", "C2", "C3"], "linger": LINGER_LOW}, ("GREEN", "Normal")),
]

NOTES = {
    "DEMO-01": "Healthy and stable over two visits",
    "DEMO-02": "Early warning: behaviour shifts while questionnaires stay low",
    "DEMO-03": "Worsening across three visits, ends in Review now with a self-harm answer",
    "DEMO-04": "Improving with care: Review now, then Follow up, then No concerns",
    "DEMO-05": "Self-harm answer while behaviour looks typical",
    "DEMO-06": "Severe on every measure, self-harm nearly every day",
    "DEMO-07": "High questionnaire scores, typical behaviour",
    "DEMO-08": "Not enough typing to score behaviour",
    "DEMO-09": "Reaction concentrated on relationship prompts",
    "DEMO-10": "Reaction grows from mild to strong prompts",
    "DEMO-11": "Within the healthy range but leaning towards slowing",
    "DEMO-12": "Error-heavy, erratic typing (mixed pattern)",
    "DEMO-13": "Some prompts left blank",
}


def demo_account():
    conn = db._conn()
    row = conn.execute("SELECT clinician_id FROM clinicians WHERE name=?", (DEMO_NAME,)).fetchone()
    conn.close()
    if row:
        return row[0], False
    ok, cid, err = db.register_clinician(DEMO_NAME, DEMO_PASSWORD, "admin")
    if not ok:
        raise SystemExit(f"Could not create the demo account: {err}")
    return cid, True


def clear_demo_clients(cid):
    conn = db._conn()
    ids = [r[0] for r in conn.execute("SELECT session_id FROM intake_sessions WHERE clinician_id=?", (cid,))]
    if ids:
        marks = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM question_snapshots WHERE session_id IN ({marks})", ids)
        conn.execute(f"DELETE FROM intake_sessions WHERE session_id IN ({marks})", ids)
    conn.commit(); conn.close()
    return len(ids)


def main():
    db.init_db()
    cid, created = demo_account()
    removed = clear_demo_clients(cid)
    ctrl = PsyClickController()
    now = datetime.now(timezone.utc).replace(microsecond=0)

    print(f"{'Created' if created else 'Reusing'} demo account {cid}" + (f"; replaced {removed} old demo sessions" if removed else ""))
    for client, days, q, behaviour, (want_flag, want_label) in SCENARIOS:
        spec = {"client": client, **q, **behaviour}
        for seed in range(40):
            final = run_session(ctrl, db, spec, cid, random.Random(zlib.crc32(f"{client}/{days}".encode()) + seed))
            a = final["analysis"]
            if (want_flag in (None, a["flag"])) and (want_label in (None, a["label"])):
                break
            clear_session(final["session_id"])
        else:
            raise SystemExit(f"{client} ({days} d ago): could not reach {want_flag}/{want_label}; last {a['flag']}/{a['label']}")

        when = now - timedelta(days=days, hours=random.Random(days).randint(0, 6), minutes=random.Random(client).randint(0, 59))
        conn = db._conn()
        conn.execute("UPDATE intake_sessions SET timestamp=?, synced_at=? WHERE session_id=?",
                     (when.strftime("%Y-%m-%d %H:%M:%S"), NOT_FOR_SYNC, final["session_id"]))
        conn.commit(); conn.close()
        print(f"  {client}  {when:%Y-%m-%d}  PHQ-9 {q['phq']:>2}  GAD-7 {q['gad']:>2}  "
              f"T² {a['t2_score']:7.1f}  {a['flag']:5}  {a['label']}")

    db.log_audit("security", "Demo data loaded", f"{len(SCENARIOS)} simulated sessions", actor_id=cid)
    print(f"\nSign in with ID {cid} and password {DEMO_PASSWORD}")
    for k, v in NOTES.items():
        print(f"  {k}: {v}")


def clear_session(session_id):
    conn = db._conn()
    conn.execute("DELETE FROM question_snapshots WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM intake_sessions WHERE session_id=?", (session_id,))
    conn.commit(); conn.close()


if __name__ == "__main__":
    main()
