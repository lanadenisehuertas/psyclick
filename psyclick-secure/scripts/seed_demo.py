"""
seed_demo.py — create the PsyClick demo administrator and its sample clients.

    python scripts/seed_demo.py                 # the app's normal database
    PSYCLICK_DB_PATH=path/to.db python scripts/seed_demo.py

FOR DEMONSTRATION ONLY. Every session is simulated input run through the real
scoring pipeline (see demo_simulation.py), so the results are exactly what
PsyClick computes for that behaviour. The clients belong to the demo account
and sync like any other account's data, so the demo works on every device.

Two clients (DEMO-14, DEMO-15) show restlessness, which the current engine
cannot reach from simulated input (questionnaire-phase mouse movement is part
of the client's own baseline). Their overall scores are set by hand and the
flag, label and rationale come from the engine's own classifier; they are
marked "illustrative" in the notes.

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

import anomaly_engine as ae
import database_manager as db
import json
from backend_controller import PsyClickController
from demo_simulation import run_session

DEMO_NAME     = "Demo Admin (simulation)"
DEMO_PASSWORD = "PsyClickDemo2026"

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
    ("DEMO-04", 84, dict(phq=19, gad=16, item9=2), {"task": MIXED_MARK, "linger": LINGER_HIGH, "context": {"keyboard": "laptop"},
                                                     "phq_mouse": "restless", "gad_mouse": "restless"}, ("RED", "Mixed Disturbance")),
    ("DEMO-04", 42, dict(phq=13, gad=10), {"task": SLOW_MILD, "context": {"keyboard": "laptop"}}, ("AMBER", "Psychomotor Retardation")),
    ("DEMO-04", 4,  dict(phq=6, gad=5), {"context": {"keyboard": "desktop"}}, ("GREEN", "Normal")),
    # Self-harm answer while behaviour looks typical
    ("DEMO-05", 5,  dict(phq=8, gad=6, item9=1), {"linger": LINGER_LOW}, ("GREEN", "Normal")),
    # Severe on every measure, self-harm nearly every day
    ("DEMO-06", 0,  dict(phq=24, gad=18, item9=3), {"task": MIXED_MARK, "linger": LINGER_HIGH,
                                                     "read": {"C4": 31.0}, "phq_mouse": "restless",
                                                     "gad_mouse": "restless"}, ("RED", "Mixed Disturbance")),
    # High questionnaires, typical behaviour
    ("DEMO-07", 6,  dict(phq=16, gad=15), {}, ("GREEN", "Normal")),
    # Too little typing to score behaviour
    ("DEMO-08", 30, dict(phq=8, gad=6), {}, ("GREEN", "Normal")),
    ("DEMO-08", 2,  dict(phq=9, gad=7), {"skip": ALL_ITEMS}, ("REPEAT", "Insufficient Data")),
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
    ("DEMO-13", 20, dict(phq=5, gad=10), {"skip": ["B2", "C2", "C3"], "linger": LINGER_LOW,
                                          "context": {"language": "mixed", "age_band": "18-64"}}, ("GREEN", "Normal")),
    # Restlessness (illustrative values, see the module docstring)
    ("DEMO-14", 10, dict(phq=8, gad=13), {"task": {"err": 0.08}, "linger": LINGER_LOW,
                                          "illustrative": dict(t2=72.0, psi=9.0, pai=70.0)},
     ("AMBER", "Psychomotor Agitation")),
    ("DEMO-15", 1,  dict(phq=14, gad=19), {"task": {"err": 0.1}, "linger": LINGER_HIGH,
                                           "illustrative": dict(t2=168.0, psi=12.0, pai=210.0)},
     ("RED", "Psychomotor Agitation")),
    # Slow from the very start: the own-baseline comparison looks normal
    ("DEMO-16", 7,  dict(phq=6, gad=5), {"base": {"flight": 0.36, "dwell": 0.13, "jitter": 0.06},
                                         "context": {"typing": "rarely", "age_band": "65plus"}}, ("GREEN", "Normal")),
    # Interrupted: left the keyboard for 6 minutes in one answer and 40 s in another
    ("DEMO-17", 11, dict(phq=7, gad=8), {"task": lambda i, g, l: {"away": 360} if i == "C2" else ({"away": 40} if i == "A4" else {}),
                                         "read": {"B3": 95.0}}, ("GREEN", "Normal")),
    # PHQ-9 clicked through in about a second per question
    ("DEMO-18", 13, dict(phq=0, gad=1), {"phq_leg": 0.05, "phq_think": (0.3, 0.7)}, ("GREEN", "Normal")),
]

NOTES = {
    "DEMO-01": "Healthy and stable over two visits",
    "DEMO-02": "Early warning: behaviour shifts while questionnaires stay low",
    "DEMO-03": "Worsening across three visits, ends in Review now with a self-harm answer",
    "DEMO-04": "Improving with care: Review now, then Follow up, then No concerns (laptop, then a desktop keyboard)",
    "DEMO-05": "Self-harm answer while behaviour looks typical",
    "DEMO-06": "Severe on every measure, self-harm nearly every day",
    "DEMO-07": "High questionnaire scores, typical behaviour",
    "DEMO-08": "Not enough typing to score behaviour: Repeat session (an earlier scored visit stays the behaviour comparison)",
    "DEMO-09": "Reaction concentrated on relationship prompts",
    "DEMO-10": "Reaction grows from mild to strong prompts",
    "DEMO-11": "Within the healthy range but leaning towards slowing",
    "DEMO-12": "Error-heavy, erratic typing (mixed pattern)",
    "DEMO-13": "Some prompts left blank; answered in Tagalog and English",
    "DEMO-14": "Restlessness, Follow up (illustrative values)",
    "DEMO-15": "Marked restlessness with severe anxiety, Review now (illustrative values)",
    "DEMO-16": "Slow from the very start: looks normal against the own baseline, slow against healthy adults (rarely types, 65 or older)",
    "DEMO-17": "Interrupted session: away from the keyboard, long wait before a prompt",
    "DEMO-18": "PHQ-9 clicked through in about a second per question",
}

LEVEL_WEIGHT = {"A": 0.7, "B": 1.0, "C": 1.4}


def apply_illustrative(session_id, final, values):
    """Set the overall scores by hand; flag, label and rationale come from the
    engine's classifier, and the prompt scores are rescaled to match."""
    p95 = ae.BOOTSTRAP_THRESHOLDS["task_3"]["p95"]
    fz = ae.fuzzy_classify(values["t2"], p95, p95, {"total": values["psi"]}, values["pai"], task_context="task_3")
    snaps = [s for s in final["visuals"]["question_snapshots"]]
    scored = [s for s in snaps if s.get("flag") != "NO_DATA"]
    total_w = sum(LEVEL_WEIGHT[s["level"]] for s in scored) or 1
    for s in scored:
        w = LEVEL_WEIGHT[s["level"]] * len(scored) / total_w
        s["t2_score"] = round(values["t2"] * 1.1 * w, 2)
        s["psi"] = round(values["psi"] * w, 2)
        s["pai"] = round(values["pai"] * w, 2)
    domain = {}
    for s in scored:
        domain.setdefault(s["group_id"], []).append(s["t2_score"])
    domain = {g: sum(v) / len(v) for g, v in domain.items()}
    conn = db._conn()
    conn.execute("""UPDATE intake_sessions SET t2_score=?, psi=?, pai=?, fuzzy_label=?, fuzzy_confidence=?,
                    flag=?, rationale=?, domain_t2_json=?, question_snapshots_json=? WHERE session_id=?""",
                 (values["t2"], values["psi"], values["pai"], fz["label"], fz["confidence"], fz["flag"],
                  fz["rationale"], json.dumps(domain),
                  json.dumps([{k: v for k, v in s.items() if k not in ("raw_flights", "pause_coords")} for s in snaps]),
                  session_id))
    for s in scored:
        conn.execute("UPDATE question_snapshots SET t2_score=?, psi=?, pai=? WHERE session_id=? AND item_id=?",
                     (s["t2_score"], s["psi"], s["pai"], session_id, s["item_id"]))
    conn.commit(); conn.close()
    return {"t2_score": values["t2"], "flag": fz["flag"], "label": fz["label"]}


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
    """Remove the demo account's sessions; tombstones carry this to other devices."""
    conn = db._conn()
    n = db.delete_sessions(conn, "clinician_id=?", (cid,))
    conn.commit(); conn.close()
    return n


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
            if "illustrative" in spec:
                a = apply_illustrative(final["session_id"], final, spec["illustrative"])
            if (want_flag in (None, a["flag"])) and (want_label in (None, a["label"])):
                break
            clear_session(final["session_id"])
        else:
            raise SystemExit(f"{client} ({days} d ago): could not reach {want_flag}/{want_label}; last {a['flag']}/{a['label']}")

        when = now - timedelta(days=days, hours=random.Random(days).randint(0, 6), minutes=random.Random(client).randint(0, 59))
        conn = db._conn()
        conn.execute("UPDATE intake_sessions SET timestamp=? WHERE session_id=?",
                     (when.strftime("%Y-%m-%d %H:%M:%S"), final["session_id"]))
        conn.commit(); conn.close()
        print(f"  {client}  {when:%Y-%m-%d}  PHQ-9 {q['phq']:>2}  GAD-7 {q['gad']:>2}  "
              f"T² {a['t2_score']:7.1f}  {a['flag']:5}  {a['label']}")

    db.log_audit("security", "Demo data loaded", f"{len(SCENARIOS)} simulated sessions", actor_id=cid)
    print(f"\nSign in with ID {cid} and password {DEMO_PASSWORD}")
    for k, v in NOTES.items():
        print(f"  {k}: {v}")


def clear_session(session_id):
    conn = db._conn()
    db.delete_sessions(conn, "session_id=?", (session_id,))
    conn.commit(); conn.close()


if __name__ == "__main__":
    main()
