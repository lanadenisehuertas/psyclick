"""
demo_simulation.py — synthetic sessions for the PsyClick demo account.

Every demo session is produced by the real pipeline: synthetic keystroke and
mouse event streams go through feature_extractor, the anomaly engine, the
hover-word mapper and database_manager.save_full_intake, exactly as a live
session would. Only the raw input is simulated, so every score, flag and
label in the demo is what PsyClick actually computes for that behaviour.

A behaviour profile describes how a simulated client types and moves:
    flight   mean gap between key presses (s)       dwell  key hold (s)
    jitter   spread of the gaps                     err    backspace rate
    pause    chance of a >1 s pause per key          mouse  "calm" | "restless"
"""

import math
import random

# The 12 written prompts, as shown by the assessment (EmotionalTask.jsx)
QUESTIONS = [
    ("A1", 1, "A", "time_workload", "How do you pick which task to do first when you have many deadlines?"),
    ("A2", 1, "A", "time_workload", "What does your daily routine look like during a very busy week?"),
    ("B1", 1, "B", "time_workload", "How did you feel the last time a surprise task was added to your workload?"),
    ("C1", 1, "C", "time_workload", "How do you feel about yourself when you do not finish everything you planned to do?"),
    ("A3", 2, "A", "interpersonal", "How did your most recent misunderstanding with someone close to you get started?"),
    ("B2", 2, "B", "interpersonal", "How does it feel to have a conflict with your family that is not yet fixed?"),
    ("B3", 2, "B", "interpersonal", "How did you react the last time you felt you let down someone important?"),
    ("C2", 2, "C", "interpersonal", "What did it feel like the last time you were left out of a group?"),
    ("A4", 3, "A", "performance_pressure", "What do you usually do to get ready for a big deadline or exam?"),
    ("B4", 3, "B", "performance_pressure", "How does your body feel when you have to speak in front of a panel or boss?"),
    ("C3", 4, "C", "self_area", "What doubts do you have when you think about a big decision you made recently?"),
    ("C4", 4, "C", "self_area", "What words do you use to describe yourself on days when things are very hard?"),
]
GROUP_NAMES = {1: "Group 1: Time Pressure & Workload", 2: "Group 2: Interpersonal Friction",
               3: "Group 3: Performance Pressure", 4: "Group 4: Self Area"}
LEVEL_NAMES = {"A": "Level A - Descriptive / Low Emotional Load",
               "B": "Level B - Recall of Specific Events / Moderate Load",
               "C": "Level C - Self-Evaluation / Highest Psychomotor Activation"}

CALM = dict(flight=0.17, dwell=0.095, jitter=0.045, err=0.03, pause=0.004, mouse="calm")
LETTERS = "etaoinshrdlucmfwypvbgk"


class FakeLogger:
    """Stands in for the pynput loggers: hands the controller a prepared stream."""
    def __init__(self):
        self.next = []

    def start_logging(self, *a, **k):
        pass

    def stop_logging(self):
        data, self.next = self.next, []
        return data

    def suspend(self):
        pass

    def resume(self):
        pass


def keystrokes(rng, n, p, t0):
    """Key DOWN/UP events for n characters typed with profile p, starting at t0."""
    ev, t = [], t0
    for i in range(n):
        if i:
            gap = max(0.04, rng.gauss(p["flight"], p["jitter"]))
            if rng.random() < p["pause"]:
                gap = rng.uniform(1.2, 3.2)
            if p.get("away") and i == n // 2:
                gap += p["away"]                 # left the keyboard mid-answer
            t += gap
        key = "backspace" if (i > 2 and rng.random() < p["err"]) else rng.choice(LETTERS)
        dwell = max(0.03, rng.gauss(p["dwell"], 0.02))
        ev.append({"key": key, "event": "DOWN", "time": t})
        ev.append({"key": key, "event": "UP", "time": t + dwell})
    return ev, t


def mouse_path(rng, style, t0, targets, dur_per_leg=0.55, think=None):
    """MOVE events travelling between targets. 'restless' adds tremor and overshoot.
    think=(lo, hi): seconds the cursor rests before each move (reading a question)."""
    ev, t = [], t0
    x, y = targets[0]
    for tx, ty in targets[1:]:
        if think:
            t += rng.uniform(*think)
        steps = max(8, int(dur_per_leg * 60))
        for s in range(1, steps + 1):
            f = 0.5 - 0.5 * math.cos(math.pi * s / steps)            # ease in/out
            nx, ny = x + (tx - x) * f, y + (ty - y) * f
            if style == "restless":
                nx += rng.gauss(0, 9); ny += rng.gauss(0, 9)
                dt = rng.uniform(0.006, 0.02)
            else:
                nx += rng.gauss(0, 0.8); ny += rng.gauss(0, 0.8)
                dt = rng.uniform(0.014, 0.019)
            t += dt
            ev.append({"x": nx, "y": ny, "event": "MOVE", "time": t})
        x, y = tx, ty
        t += rng.uniform(0.15, 0.35) if style == "calm" else rng.uniform(0.03, 0.1)
        ev.append({"x": x, "y": y, "event": "CLICK", "time": t})
    return ev, t


def click_targets(rng, n, spread=420):
    return [(700 + rng.uniform(-spread, spread), 450 + rng.uniform(-260, 260)) for _ in range(n)]


def word_boxes(prompt, x0=380, y0=300):
    """Screen boxes for each prompt word, padded by 20 px as the UI does."""
    boxes, x, y = [], x0, y0
    for w in prompt.split(" "):
        width = 11 * len(w) + 6
        if x + width > x0 + 680:
            x, y = x0, y + 42
        boxes.append({"word": w, "x1": x - 20, "y1": y - 20, "x2": x + width + 20, "y2": y + 28 + 20})
        x += width + 9
    return boxes


def reading_mouse(rng, boxes, t0, linger, read_s):
    """Cursor drifting along the prompt while reading, resting on lingered words."""
    ev, t = [], t0
    centres = {b["word"]: ((b["x1"] + b["x2"]) / 2, (b["y1"] + b["y2"]) / 2) for b in boxes}
    ev.append({"x": 300.0, "y": 520.0, "event": "MOVE", "time": t})
    order = [b["word"] for b in boxes if b["word"] in linger]
    if not order:
        return ev + [{"x": 302.0, "y": 522.0, "event": "MOVE", "time": t0 + read_s}]
    for w in order:
        cx, cy = centres[w]
        for s in range(1, 13):                       # glide to the word
            t += 0.016
            ev.append({"x": cx + (300 - cx) * (1 - s / 12) * 0.2, "y": cy + rng.gauss(0, 1), "event": "MOVE", "time": t})
        t += linger[w]                               # rest on it
        ev.append({"x": cx + 2, "y": cy + 1, "event": "MOVE", "time": t})
    lx, ly = ev[-1]["x"], ev[-1]["y"]
    for s in range(1, 16):                           # move down to the answer box
        t += 0.016
        ev.append({"x": lx + (300 - lx) * s / 15, "y": ly + (640 - ly) * s / 15, "event": "MOVE", "time": t})
    ev.append({"x": 301.0, "y": 641.0, "event": "MOVE", "time": max(t + 0.05, t0 + read_s)})
    return ev


def run_session(ctrl, db, spec, clinician_id, rng):
    """
    Drive PsyClickController through one full session.

    spec keys: client, phq, gad, item9, base (profile), task (profile or
    per-item callable), skip (item ids left blank), linger ({item: {word: s}}),
    read ({item: seconds before typing}), phq_mouse/gad_mouse ("calm"|"restless").
    """
    k, m = FakeLogger(), FakeLogger()
    ctrl.key_logger, ctrl.mouse_logger = k, m
    ctrl.set_student_id(spec["client"])
    ctrl.session_data["clinician_id"] = clinician_id
    ctrl.session_data["consent_verified"] = True

    base = {**CALM, **spec.get("base", {})}
    t = 1000.0

    k.next, t = keystrokes(rng, 150, base, t)
    ctrl.save_kbase()
    m.next, t = mouse_path(rng, "calm", t + 2, click_targets(rng, 6))
    ctrl.save_mbase()
    # phq_leg: seconds per answer click (about 0.45 s of travel per option normally)
    m.next, t = mouse_path(rng, spec.get("phq_mouse", "calm"), t + 2, click_targets(rng, 10, 200),
                           spec.get("phq_leg", 0.45), spec.get("phq_think", (2.0, 3.5)))
    ctrl.save_phq(spec["phq"], spec.get("item9", 0))
    m.next, t = mouse_path(rng, spec.get("gad_mouse", "calm"), t + 2, click_targets(rng, 8, 200), 0.45, (2.0, 3.5))
    ctrl.save_gad(spec["gad"])

    task = spec.get("task", {})
    for item_id, gid, level, dom, prompt in QUESTIONS:
        meta = {"item_id": item_id, "group_id": gid, "level": level, "domain_label": dom,
                "group_name": GROUP_NAMES[gid], "level_name": LEVEL_NAMES[level], "prompt": prompt}
        boxes = word_boxes(prompt)
        ctrl.register_word_boxes(boxes)
        t += 5
        read_s = spec.get("read", {}).get(item_id, rng.uniform(4.5, 9.0))
        m.next = reading_mouse(rng, boxes, t, spec.get("linger", {}).get(item_id, {}), read_s)
        if item_id in spec.get("skip", ()):
            k.next, text = [], ""
        else:
            prof = task(item_id, gid, level) if callable(task) else task
            p = {**base, **(prof or {})}
            n = rng.randint(70, 130)
            k.next, t_end = keystrokes(rng, n, p, t + read_s)
            text = "x" * max(25, int(n * 0.85))
            t = t_end
        ctrl.save_question_snapshot(meta, text)

    final = ctrl.process_final_task()
    return final
