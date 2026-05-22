"""
backend_controller.py — PsyClick

Mouse tracking roles — by phase:
─────────────────────────────────────────────────────────────────────────────
Phase               Mouse use?   What we extract
─────────────────────────────────────────────────────────────────────────────
Calibration         YES          Baseline cursor dynamics (velocity, jerk,
(click circles)                  path_entropy, pause_frequency) → EWMA seed

PHQ-9 / GAD-7       YES          Cursor dynamics while client navigates and
(Likert buttons)                 clicks answer options — real behavioral signal
                                 (hesitation before clicking, path directness)

Emotional Response  PARTIAL      Mouse is NOT held during typing.
Task — typing                    Only ONE signal is valid:
                                   → hover_words: which word in the prompt
                                     the cursor last paused on before the
                                     client moved to the keyboard.
                                 All other mouse metrics (velocity, jerk,
                                 path_entropy) during typing = ~0 / noise.
                                 We DO NOT feed these into T² during the task.
─────────────────────────────────────────────────────────────────────────────

T² Feature Vector during Emotional Task (keyboard-only, 5 features):
  flight_time, dwell_time, typing_velocity, error_rate, pause_frequency
  (pause_frequency = pre-key pauses in keystroke stream, not mouse)

PAI mouse sub-features (path_entropy, cursor_velocity, jerk) are only
meaningful from the PHQ/GAD phases, where they feed the EWMA baseline.
They are NOT recomputed from the typing-phase mouse data.
"""

import json
import os
from pathlib import Path
import database_manager as db
import dynamics_logger  as dl
import feature_extractor as fe
from anomaly_engine import AnomalyEngine


class PsyClickController:

    def __init__(self):
        db.init_db()
        self.hal          = dl.HardwareAbstractionLayer()
        self.key_logger   = dl.KeyLogger(self.hal)
        self.mouse_logger = dl.MouseLogger(self.hal)

        # Load normative baseline (v4: hybrid scoring)
        self.norm_stats = self._load_normative_baseline()
        self.engine = AnomalyEngine()
        self.normative_mode = False

        self._empty_mouse = {
            "hv": 0, "vv": 0, "tv": 0, "ta": 0,
            "jerk": 0, "curvature": 0,
            "path_entropy": 0, "cursor_velocity": 0, "pause_frequency": 0,
        }

        # Word bounding boxes registered per prompt, for hover detection
        self._word_boxes         = []
        self._current_question   = None
        self._question_snapshots = []

        # Cached mouse features from PHQ/GAD phases (the only valid task mouse data)
        self._phq_mouse_feats = {}
        self._gad_mouse_feats = {}

        self._reset_session()

    # ── Session lifecycle ─────────────────────────────────────────────────────
    def _reset_session(self):
        self.session_data = {
            "student_id": None,
            "kbase": {"mean_flight": 0, "std_flight": 0},
            "mbase": dict(self._empty_mouse),
            "phq":   {"score": 0, "mouse": dict(self._empty_mouse)},
            "gad":   {"score": 0, "mouse": dict(self._empty_mouse)},
            "task":  {"mean_flight": 0, "std_flight": 0},
        }
        # Reload normative baseline and reinitialize engine (v4)
        self.norm_stats = self._load_normative_baseline()
        self.engine = AnomalyEngine()
        self._word_boxes         = []
        self._current_question   = None
        self._question_snapshots = []
        self._phq_mouse_feats    = {}
        self._gad_mouse_feats    = {}
        try:
            self.key_logger.stop_logging()
            self.mouse_logger.stop_logging()
        except:
            pass

    def set_student_id(self, sid):
        self._reset_session()
        self.session_data["student_id"] = sid

    def _load_normative_baseline(self):
        """
        Load normative baseline (110-session population stats) for hybrid scoring.

        Searches for normative_baseline.json in:
          1. Current directory
          2. Parent directory (psyclick-1/)
          3. psyclick-clinical/ subdirectory

        Returns None if not found (engine will use ipsative-only fallback).
        """
        search_paths = [
            Path("normative_baseline.json"),
            Path("..") / "normative_baseline.json",
            Path("psyclick-clinical") / "normative_baseline.json",
        ]

        for path in search_paths:
            if path.exists():
                try:
                    with open(path) as f:
                        baseline = json.load(f)
                    print(f"[✓] Loaded normative baseline from {path}")
                    return baseline
                except Exception as e:
                    print(f"[!] Failed to load {path}: {e}")
                    continue

        print("[!] Normative baseline not found. Using ipsative-only scoring (fallback).")
        return None

    # ── Capture helpers ───────────────────────────────────────────────────────
    def start_key_capture(self, calibration_mode=False):
        self.key_logger.start_logging(calibration_mode=calibration_mode)

    def start_mouse_capture(self):
        self.mouse_logger.start_logging()

    # ── Word bounding-box hover detection ─────────────────────────────────────
    def register_word_boxes(self, boxes):
        print(f"DEBUG: Registering {len(boxes)} word boxes for prompt hover detection.")
        self._word_boxes = boxes

    def _map_hover_words(self, mouse_raw, key_raw):
        """
        Extract which prompt words the cursor paused over while reading
        the question (pre-typing window + any re-reading pauses during typing).

        Algorithm fix: pynput only fires MOVE events when the cursor actually
        moves.  A long dt on row[i] means the cursor was STATIONARY at
        row[i-1]'s position for that duration — so we check row[i-1]'s
        coordinates against word boxes, not row[i]'s.

        We include the full session (pre- and post-first-keypress) so that
        brief re-reading pauses mid-response are also captured.  Gaps while
        the cursor is over the TEXT ENTRY AREA (below the prompt) are excluded
        via the box-hit test, which only matches the prompt region.
        """
        if not self._word_boxes or not mouse_raw:
            return [], []

        import pandas as pd

        # Inject dummy mouse event at first keystroke timestamp to capture final reading pause
        if key_raw:
            down_events = [e for e in key_raw if e.get("event") == "DOWN"]
            if down_events:
                first_key = min(e["time"] for e in down_events)
                last_mouse = max(mouse_raw, key=lambda x: x["time"])
                if first_key > last_mouse["time"]:
                    mouse_raw.append({
                        "x": last_mouse["x"], 
                        "y": last_mouse["y"], 
                        "time": first_key, 
                        "event": "READING_PAUSE"
                    })

        df = pd.DataFrame(mouse_raw).sort_values("time").reset_index(drop=True)
        if len(df) < 2:
            return [], []

        dt = df["time"].diff()

        hover = {}
        all_pauses = []
        # i is the position-after-gap; i-1 is where the cursor actually sat
        for i in range(1, len(df)):
            gap = dt.iloc[i]
            if gap < 0.03:          # gap < 30 ms → normal movement, skip
                continue
            # Cursor was stationary at the PREVIOUS row's position
            prev = df.iloc[i - 1]
            px, py = prev["x"], prev["y"]
            dwell_ms = gap * 1000
            
            all_pauses.append({"x": int(px), "y": int(py), "ms": int(dwell_ms)})

            for box in self._word_boxes:
                # Add 40px tolerance for clinical usability (tremor, motor slowing, scaling, high-DPI)
                if (box["x1"] - 40) <= px <= (box["x2"] + 40) and (box["y1"] - 40) <= py <= (box["y2"] + 40):
                    w = box["word"]
                    if w not in hover:
                        hover[w] = {"word": w, "dwell_ms": 0.0, "hover_count": 0,
                                    "x": (box["x1"] + box["x2"]) // 2,
                                    "y": (box["y1"] + box["y2"]) // 2}
                    hover[w]["dwell_ms"]    += dwell_ms
                    hover[w]["hover_count"] += 1
                    break

        return sorted(hover.values(), key=lambda d: d["dwell_ms"], reverse=True), all_pauses

    def _pre_typing_pause_ms(self, mouse_raw, key_raw):
        """
        Compute the total time (ms) from when the question page was shown
        (first mouse event) to when the client pressed the first key.
        This is a clean, defensible measure: reading latency / cognitive approach time.
        Longer = more hesitation / processing load before engaging.
        """
        if not mouse_raw or not key_raw:
            return 0.0
        down_events = [e for e in key_raw if e.get("event") == "DOWN"]
        if not down_events:
            return 0.0
        first_key   = min(e["time"] for e in down_events)
        first_mouse = min(e["time"] for e in mouse_raw)
        gap_ms      = (first_key - first_mouse) * 1000
        return max(0.0, gap_ms)

    # ── Calibration ───────────────────────────────────────────────────────────
    def save_kbase(self):
        """
        Keyboard calibration: extracts typing features and seeds the EWMA baseline.
        Mouse is NOT running during keyboard calibration — client is typing.
        """
        raw   = self.key_logger.stop_logging()
        feats = fe.extract_features(raw)
        if feats:
            self.session_data["kbase"] = feats
            # Seed baseline with keyboard features only
            self.engine.update_baseline(feats)
        return feats is not None

    def save_mbase(self):
        """
        Mouse calibration: client clicks circles — full cursor dynamics valid.
        Feed into EWMA baseline as the mouse component.
        """
        raw   = self.mouse_logger.stop_logging()
        feats = fe.extract_mouse_features(raw)
        if feats:
            self.session_data["mbase"] = feats
            # Feed cursor dynamics into baseline — this is real mouse data
            self.engine.update_baseline(feats)
        return feats is not None

    # ── PHQ-9 / GAD-7 (mouse valid — client clicking Likert buttons) ─────────
    def save_phq(self, total_score):
        """
        PHQ-9 complete. Mouse was running during Likert selection — valid signal.
        Extract and cache; feed cursor features into EWMA baseline.
        """
        raw   = self.mouse_logger.stop_logging()
        feats = fe.extract_mouse_features(raw)
        self.session_data["phq"]["score"] = total_score
        if feats:
            self.session_data["phq"]["mouse"] = feats
            self._phq_mouse_feats            = feats
            # PHQ mouse data is real — feed into baseline
            self.engine.update_baseline(feats)

    def save_gad(self, total_score):
        """
        GAD-7 complete. Same as PHQ-9 — Likert clicking, valid mouse signal.
        """
        raw   = self.mouse_logger.stop_logging()
        feats = fe.extract_mouse_features(raw)
        self.session_data["gad"]["score"] = total_score
        if feats:
            self.session_data["gad"]["mouse"] = feats
            self._gad_mouse_feats            = feats
            # GAD mouse data is real — feed into baseline
            self.engine.update_baseline(feats)

    # ── Per-question snapshot (keyboard primary; mouse = hover only) ──────────
    def set_current_question(self, question_meta):
        self._current_question = question_meta
        self._word_boxes = [] # Clear boxes from previous question
        self.key_logger.start_logging(on_first_key=self._pause_mouse_logging)
        self.mouse_logger.start_logging()

    def _pause_mouse_logging(self):
        print("DEBUG: First key pressed, pausing mouse logging.")
        self.mouse_logger.stop_logging()

    def save_question_snapshot(self, question_meta, response_text):
        """
        Called when client submits each emotional response question.

        Keyboard features:   flight_time, dwell_time, typing_velocity,
                             error_rate, pause_frequency — PRIMARY T² inputs.

        Mouse features used: ONLY hover_words (pre-typing reading window)
                             and pre_typing_pause_ms (time from page shown
                             to first keypress — cognitive approach latency).

        Mouse features NOT used: cursor_velocity, jerk, path_entropy during
                             the typing window — these are ~0 because the
                             client's hand is on the keyboard, not the mouse.
                             Including them would contaminate the T² vector
                             with noise and weaken construct validity.

        T² vector for emotional task questions uses keyboard features + the
        PHQ/GAD-derived mouse baseline (which was established when mouse use
        was genuine).
        """
        key_raw   = self.key_logger.stop_logging()
        mouse_raw = self.mouse_logger.stop_logging()

        # ── Keyboard features (primary) ───────────────────────────────────────
        key_feats = fe.extract_features(key_raw) or {}

        # ── Mouse: hover words (pre-typing window only) ───────────────────────
        hover_words, pause_coords = self._map_hover_words(mouse_raw, key_raw)
        pre_typing_pause  = self._pre_typing_pause_ms(mouse_raw, key_raw)
        question_shown_at = min(e["time"] for e in mouse_raw) if mouse_raw else 0.0

        # ── T² feature vector: keyboard-only for the task phase ───────────────
        # We do NOT include cursor_velocity/jerk/path_entropy from the typing
        # window. Instead, those slots retain the PHQ/GAD baseline values so
        # the T² comparison is against the same feature space.
        phq_m = self._phq_mouse_feats
        gad_m = self._gad_mouse_feats
        # Average mouse baseline from PHQ and GAD (both used mouse genuinely)
        avg_mouse = {
            "path_entropy":   (phq_m.get("path_entropy",0)    + gad_m.get("path_entropy",0))    / 2,
            "cursor_velocity":(phq_m.get("cursor_velocity",0) + gad_m.get("cursor_velocity",0)) / 2,
            "jerk":           (phq_m.get("jerk",0)            + gad_m.get("jerk",0))            / 2,
            "pause_frequency": key_feats.get("pause_frequency", 0.0),  # keystroke pauses (valid)
        }

        combined = {**key_feats, **avg_mouse}

        # Assessment phase: analyse only — do NOT update baseline.
        # Calibration (kbase, mbase, PHQ, GAD) built the baseline; updating
        # here would pull μ toward the assessment data, collapsing diff → 0

        norm_stats = db.get_normative_stats().get('stats', {})
        analysis = self.engine.analyse(combined, norm_stats=norm_stats) if combined else {}

        snap = {
            "item_id":           question_meta.get("item_id", "?"),
            "group_id":          question_meta.get("group_id", 0),
            "level":             question_meta.get("level", "A"),
            "domain_label":      question_meta.get("domain_label", "unknown"),
            "group_name":        question_meta.get("group_name", ""),
            "level_name":        question_meta.get("level_name", ""),
            "prompt":            question_meta.get("prompt", ""),
            "response_len":      len(response_text),

            # T² results
            "t2_score":          float((analysis or {}).get("t2_score", 0.0)),
            "psi":               float((analysis or {}).get("psi", 0.0)),
            "pai":               float((analysis or {}).get("pai", 0.0)),
            "flag":              (analysis or {}).get("flag", "GREEN"),
            "confidence":        float((analysis or {}).get("confidence", 0.0)),

            # Keyboard biomarkers (primary — client typing)
            "flight_time":       key_feats.get("flight_time", 0.0),
            "dwell_time":        key_feats.get("dwell_time", 0.0),
            "typing_velocity":   key_feats.get("typing_velocity", 0.0),
            "error_rate":        key_feats.get("error_rate", 0.0),
            "raw_flights":       key_feats.get("raw_flight_times", []),

            # Mouse: only pre-typing signals (logically valid)
            "pre_typing_pause_ms": pre_typing_pause,   # reading latency
            "question_shown_at":   question_shown_at,  # epoch s when question appeared
            "hover_words":         hover_words,         # which words triggered hesitation
            "pause_coords":        pause_coords,        # debug: where did the mouse actually pause?
            
            # Mouse: NOT from the typing window (stored as 0 to be honest)
            "pause_freq":        0.0,   # not meaningful during typing
            "cursor_velocity":   0.0,   # not meaningful during typing
            "jerk":              0.0,   # not meaningful during typing
            "path_entropy":      0.0,   # not meaningful during typing
        }
        print(f"DEBUG: Saved snapshot. Hover words: {len(hover_words)}. Pauses: {len(pause_coords)}")
        self._question_snapshots.append(snap)

    # ── Final aggregation ─────────────────────────────────────────────────────
    def process_final_task(self):
        try:    last_key_raw = self.key_logger.stop_logging()
        except: last_key_raw = []
        try:    self.mouse_logger.stop_logging()   # discard — typing window
        except: pass

        all_flights = []
        for snap in self._question_snapshots:
            all_flights.extend(snap.get("raw_flights", []))
        last_key_feats = fe.extract_features(last_key_raw) or {}
        if last_key_feats.get("raw_flight_times"):
            all_flights.extend(last_key_feats["raw_flight_times"])

        valid_snaps = [s for s in self._question_snapshots if s.get("response_len", 0) >= 20]
        n_valid = len(valid_snaps)
        phq_m = self._phq_mouse_feats
        gad_m = self._gad_mouse_feats

        if n_valid > 0:
            agg = {
                # Keyboard (primary — from typing)
                "flight_time":     sum(s["flight_time"]     for s in valid_snaps) / n_valid,
                "dwell_time":      sum(s["dwell_time"]      for s in valid_snaps) / n_valid,
                "typing_velocity": sum(s["typing_velocity"] for s in valid_snaps) / n_valid,
                "error_rate":      sum(s["error_rate"]      for s in valid_snaps) / n_valid,
                # Mouse: use PHQ/GAD baseline values (genuinely captured)
                "path_entropy":    (phq_m.get("path_entropy",0)    + gad_m.get("path_entropy",0))    / 2,
                "cursor_velocity": (phq_m.get("cursor_velocity",0) + gad_m.get("cursor_velocity",0)) / 2,
                "jerk":            (phq_m.get("jerk",0)            + gad_m.get("jerk",0))            / 2,
                # pause_frequency: individual keystroke gaps > 1s per second of typing.
                # all_flights holds every raw inter-key interval across all questions,
                # so we replicate the exact definition used in extract_features.
                "pause_frequency": (sum(1 for ft in all_flights if ft > 1.0) / sum(all_flights)
                                    if all_flights else 0.0),
            }
        else:
            kb  = self.session_data["kbase"]
            agg = {
                "flight_time":    kb.get("mean_flight", 0),
                "dwell_time":     0.0, "typing_velocity": 0.0, "error_rate": 0.0,
                "path_entropy":   phq_m.get("path_entropy", 0),
                "cursor_velocity":phq_m.get("cursor_velocity", 0),
                "jerk":           phq_m.get("jerk", 0),
                "pause_frequency":0.0,
            }

        # Assessment phase — analyse against frozen calibration baseline only.
        norm_stats = db.get_normative_stats().get('stats', {})
        analysis = self.engine.analyse(agg, norm_stats=norm_stats) or {}

        # Domain-segmented T²
        domain_t2 = {}; domain_cnt = {}
        for snap in self._question_snapshots:
            gid = snap["group_id"]
            domain_t2[gid]  = domain_t2.get(gid, 0.0) + snap["t2_score"]
            domain_cnt[gid] = domain_cnt.get(gid, 0) + 1
        domain_t2_avg = {gid: domain_t2[gid] / domain_cnt[gid]
                         for gid in domain_t2 if domain_cnt[gid] > 0}

        # Level-resolved T²
        level_t2 = {}; level_cnt = {}
        for snap in self._question_snapshots:
            lv = snap["level"]
            level_t2[lv]  = level_t2.get(lv, 0.0) + snap["t2_score"]
            level_cnt[lv] = level_cnt.get(lv, 0) + 1
        level_t2_avg = {lv: level_t2[lv] / level_cnt[lv]
                        for lv in level_t2 if level_cnt[lv] > 0}

        # Pre-typing pause summary (per-question reading latency)
        pre_typing_pauses = {
            snap["item_id"]: snap.get("pre_typing_pause_ms", 0)
            for snap in self._question_snapshots
        }

        kb  = self.session_data["kbase"]
        k_z = ((agg["flight_time"] - kb.get("mean_flight", 0)) / kb["std_flight"]
               ) if kb.get("std_flight", 0) > 0 else 0.0

        final = self.session_data.copy()
        final["task"]      = {**agg, "mean_flight": agg["flight_time"], "std_flight": 0.0}
        final["k_z_score"] = k_z
        final["m_z_score"] = 0.0
        final["analysis"]  = analysis
        final["visuals"]   = {
            "flight_times":        all_flights,
            "pause_coords":        [],        # not collected during typing
            "question_snapshots":  self._question_snapshots,
            "domain_t2":           domain_t2_avg,
            "level_t2":            level_t2_avg,
            "pre_typing_pauses":   pre_typing_pauses,  # reading latency per question
        }

        if self.normative_mode:
            db.save_normative_session(final)
        else:
            session_id = db.save_full_intake(final)
            final["session_id"] = session_id  # expose to frontend for normative compare
        return final
