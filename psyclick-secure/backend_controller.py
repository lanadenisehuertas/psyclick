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
import logging
from datetime import datetime, timezone
import os
import sys
from pathlib import Path
import database_manager as db
import dynamics_logger  as dl
import feature_extractor as fe
from anomaly_engine import AnomalyEngine

_log = logging.getLogger(__name__)

HOVER_CAP_S = 5.0   # longest single stillness credited to one word


def _ae_scalar(ae, key):
    """Extract a scalar float from the clinical engine's nested result dict.

    The clinical AnomalyEngine returns psi/pai as dicts and t2_score under
    t2_scores.hybrid. This helper normalises all three to plain floats so
    the snapshot dict, database inserts, and frontend responses always receive
    serialisable values.
    """
    ae = ae or {}
    if key == "t2_score":
        v = ae.get("t2_score")
        if v is None:
            t2s = ae.get("t2_scores") or {}
            v = t2s.get("hybrid", t2s.get("ipsative", 0.0))
        return float(v if v is not None else 0.0)
    if key == "t2_threshold":
        v = ae.get("t2_threshold")
        if v is None:
            t2t = ae.get("t2_thresholds") or {}
            v = t2t.get("adjusted", t2t.get("base", 0.0))
        return float(v if v is not None else 0.0)
    v = ae.get(key, 0.0)
    if isinstance(v, dict):
        return float(v.get("total", v.get("adjusted", 0.0)))
    return float(v if v is not None else 0.0)


def _flatten_analysis(analysis):
    """Return a frontend-safe flat dict from the clinical engine result.

    Called in process_final_task so the report page always receives plain
    scalar values regardless of which engine version is running.
    """
    ae = analysis or {}
    return {
        "t2_score":    _ae_scalar(ae, "t2_score"),
        "t2_threshold":_ae_scalar(ae, "t2_threshold"),
        "psi":         _ae_scalar(ae, "psi"),
        "pai":         _ae_scalar(ae, "pai"),
        "flag":        ae.get("flag",       "GREEN"),
        "label":       ae.get("label",      ""),
        "confidence":  float(ae.get("confidence", 0.0)),
        "rationale":   ae.get("rationale",  ""),
    }


class PsyClickController:

    def __init__(self):
        db.init_db()
        self.hal          = dl.HardwareAbstractionLayer()
        self.key_logger   = dl.KeyLogger(self.hal)
        self.mouse_logger = dl.MouseLogger(self.hal)

        # Load normative baseline (v4: hybrid scoring)
        self.norm_stats = self._load_normative_baseline()
        self.engine = AnomalyEngine(normative_baseline=self.norm_stats)
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
        self.engine = AnomalyEngine(normative_baseline=self.norm_stats)
        self._word_boxes         = []
        self._current_question   = None
        self._question_snapshots = []
        self._phq_mouse_feats    = {}
        self._gad_mouse_feats    = {}
        self.kbase_problem       = None

    def set_student_id(self, sid):
        self._reset_session()
        self.session_data["student_id"] = sid

    # ── Capture helpers ───────────────────────────────────────────────────────
    def _load_normative_baseline(self):
        """
        Load normative baseline (110-session population stats) for hybrid scoring.

        Searches for normative_baseline.json next to this module first (the
        copy shipped with the code / bundled into the packaged API), then next
        to the executable, then the working directory.

        Returns None if not found (engine will use ipsative-only fallback).
        """
        module_dir = Path(__file__).resolve().parent
        exe_dir = Path(sys.executable).resolve().parent
        search_paths = [
            module_dir / "normative_baseline.json",
            exe_dir / "normative_baseline.json",
            exe_dir.parent / "normative_baseline.json",
            Path("normative_baseline.json"),
            Path("..") / "normative_baseline.json",
        ]

        for path in search_paths:
            if not path.exists():
                continue
            try:
                with open(path, encoding="utf-8-sig") as f:
                    baseline = json.load(f)
                mu = baseline["mu_pop"]
                S = baseline["S_pop"]
                if len(mu) != 8 or len(S) != 8 or any(len(row) != 8 for row in S):
                    raise ValueError("expected an 8-feature mean vector and 8x8 covariance")
            except Exception as e:
                _log.warning("Ignoring normative baseline %s: %s", path, e)
                continue
            # Logged outside the try: a console that cannot encode the message
            # must never cause a valid baseline to be discarded.
            _log.info("Loaded normative baseline from %s", path)
            return baseline

        _log.warning("Normative baseline not found; using ipsative-only scoring.")
        return None

    def start_key_capture(self, calibration_mode=False):
        self.key_logger.start_logging(calibration_mode=calibration_mode)

    def start_mouse_capture(self):
        self.mouse_logger.start_logging()

    # ── Word bounding-box hover detection ─────────────────────────────────────
    def register_word_boxes(self, boxes):
        """
        Called by the UI after each question prompt is rendered.
        boxes = list of {word, x1, y1, x2, y2} in screen coordinates.
        We only look at mouse events that occur BEFORE the first keypress —
        i.e., the reading/hovering window before the client touches the keyboard.
        """
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
            return []

        import pandas as pd

       
        df = pd.DataFrame(mouse_raw).sort_values("time").reset_index(drop=True)
        if len(df) < 2:
            return []

        dt = df["time"].diff()

        hover = {}
        # i is the position-after-gap; i-1 is where the cursor actually sat
        for i in range(1, len(df)):
            gap = dt.iloc[i]
            if gap < 0.10:          # gap < 100 ms → normal movement, skip
                continue
            # Cursor was stationary at the PREVIOUS row's position
            prev = df.iloc[i - 1]
            px, py = prev["x"], prev["y"]
            # A very long stillness is more likely the hand leaving the mouse
            # than reading one word, so a single stop counts for at most 5 s.
            dwell_ms = min(gap, HOVER_CAP_S) * 1000

            # Word boxes are padded and overlap; credit the nearest word.
            hits = [b for b in self._word_boxes
                    if b["x1"] <= px <= b["x2"] and b["y1"] <= py <= b["y2"]]
            if not hits:
                continue
            box = min(hits, key=lambda b: ((b["x1"] + b["x2"]) / 2 - px) ** 2
                                          + ((b["y1"] + b["y2"]) / 2 - py) ** 2)
            w = box["word"]
            if w not in hover:
                hover[w] = {"word": w, "dwell_ms": 0.0, "hover_count": 0,
                            "x": (box["x1"] + box["x2"]) // 2,
                            "y": (box["y1"] + box["y2"]) // 2}
            hover[w]["dwell_ms"]    += dwell_ms
            hover[w]["hover_count"] += 1

        return sorted(hover.values(), key=lambda d: d["dwell_ms"], reverse=True)

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
        self.kbase_problem = fe.typing_problem(raw)
        if self.kbase_problem:
            # Not the person's own typing: never let it become the baseline
            return False
        feats = fe.extract_features(raw)
        if feats:
            self.session_data["kbase"] = feats
            # Seed baseline with keyboard features only
            self.engine.update_baseline(feats, keystroke_count=feats.get("key_count", 0))
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
    def save_phq(self, total_score, item9=None):
        """
        PHQ-9 complete. Mouse was running during Likert selection — valid signal.
        Extract and cache; feed cursor features into EWMA baseline.
        item9 (0-3) is the self-harm item, kept so the clinician is alerted.
        """
        raw   = self.mouse_logger.stop_logging()
        feats = fe.extract_mouse_features(raw)
        self.session_data["phq"]["score"] = total_score
        self.session_data["phq"]["item9"] = item9
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

        # A single item is scored against the healthy item-level cut-offs
        # (one short response is far noisier than the session aggregate).
        self.engine.set_task("task_3_item")

        # ── Keyboard features (primary) ───────────────────────────────────────
        # Injected or auto-repeated keys are not the person's typing: the item
        # is kept (answer length, hover) but its timing is not scored.
        typing_issue = fe.typing_problem(key_raw)
        key_feats = {} if typing_issue else (fe.extract_features(key_raw) or {})

        # ── Mouse: hover words (pre-typing window only) ───────────────────────
        hover_words       = self._map_hover_words(mouse_raw, key_raw)
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

        # No keystrokes for this item (skipped / pasted): there is nothing to
        # score. Analysing the all-zero keyboard vector would fabricate a
        # large T² and contaminate the domain/level averages.
        analysis = self.engine.analyse(combined) if key_feats else {}

        snap = {
            "item_id":           question_meta.get("item_id", "?"),
            "group_id":          question_meta.get("group_id", 0),
            "level":             question_meta.get("level", "A"),
            "domain_label":      question_meta.get("domain_label", "unknown"),
            "group_name":        question_meta.get("group_name", ""),
            "level_name":        question_meta.get("level_name", ""),
            "prompt":            question_meta.get("prompt", ""),
            "response_len":      len(response_text),
            "key_count":         key_feats.get("key_count", 0),
            "typing_issue":      typing_issue,

            # T² results — use _ae_scalar so nested clinical engine dicts become floats
            "t2_score":          _ae_scalar(analysis, "t2_score"),
            "psi":               _ae_scalar(analysis, "psi"),
            "pai":               _ae_scalar(analysis, "pai"),
            "flag":              (analysis or {}).get("flag", "GREEN") if key_feats else "NO_DATA",
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
            
            # Mouse: NOT from the typing window (stored as 0 to be honest)
            "pause_freq":        0.0,   # not meaningful during typing
            "cursor_velocity":   0.0,   # not meaningful during typing
            "jerk":              0.0,   # not meaningful during typing
            "path_entropy":      0.0,   # not meaningful during typing
            "pause_coords":      [],    # not meaningful during typing
        }
        # Revisiting an item (Previous / Next) must not count it twice. Keep the
        # attempt with the most keystroke evidence; the latest answer length wins.
        for i, prev in enumerate(self._question_snapshots):
            if prev.get("item_id") == snap["item_id"]:
                if snap.get("key_count", 0) < prev.get("key_count", 0):
                    prev["response_len"] = snap["response_len"]
                else:
                    self._question_snapshots[i] = snap
                break
        else:
            self._question_snapshots.append(snap)

        # Restart for next question
        self.key_logger.start_logging()
        self.mouse_logger.start_logging()

    # ── Final aggregation ─────────────────────────────────────────────────────
    def process_final_task(self):
        try:    last_key_raw = self.key_logger.stop_logging()
        except: last_key_raw = []
        try:    self.mouse_logger.stop_logging()   # discard — typing window
        except: pass

        typed_snaps = [s for s in self._question_snapshots if s.get("key_count", 0) > 0]
        # Prefer substantive answers (>= 20 chars); if every answer was short,
        # still use whatever keystroke timing exists rather than none at all.
        valid_snaps = [s for s in typed_snaps if s.get("response_len", 0) >= 20] or typed_snaps
        n_valid = len(valid_snaps)

        # Flights from the same responses that feed the aggregate, so the
        # pause-frequency numerator and denominator describe the same typing.
        all_flights = []
        for snap in valid_snaps:
            all_flights.extend(snap.get("raw_flights", []))
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
            agg = None

        # Engagement is judged on the assessment typing as well as calibration;
        # without this the keystroke tally never grows past calibration.
        self.engine.baseline.keystroke_count += sum(s.get("key_count", 0) for s in valid_snaps)

        # Assessment phase — analyse against frozen calibration baseline only.
        self.engine.set_task("task_3")
        analysis = self.engine.analyse(agg) if agg else None
        if not analysis:
            # No typed responses (or no calibration baseline): scoring zeros
            # against the baseline would report a spurious disturbance. Flag
            # for clinician review without asserting a psychomotor pattern.
            agg = agg or {k: 0.0 for k in ("flight_time", "dwell_time", "typing_velocity",
                                           "error_rate", "path_entropy", "cursor_velocity",
                                           "jerk", "pause_frequency")}
            analysis = {
                "t2_score": 0.0, "t2_threshold": 0.0, "psi": 0.0, "pai": 0.0,
                "flag": "AMBER", "label": "Insufficient Data", "confidence": 0.0,
                "rationale": ("Not enough keyboard data was captured (calibration or emotional-task "
                              "responses), so psychomotor behaviour could not be assessed. Repeat the "
                              "session or rely on the questionnaire scores and clinical observation."),
            }

        # Domain-segmented T²
        domain_t2 = {}; domain_cnt = {}
        scored_snaps = [s for s in self._question_snapshots if s.get("flag") != "NO_DATA"]
        for snap in scored_snaps:
            gid = snap["group_id"]
            domain_t2[gid]  = domain_t2.get(gid, 0.0) + snap["t2_score"]
            domain_cnt[gid] = domain_cnt.get(gid, 0) + 1
        domain_t2_avg = {gid: domain_t2[gid] / domain_cnt[gid]
                         for gid in domain_t2 if domain_cnt[gid] > 0}

        # Level-resolved T²
        level_t2 = {}; level_cnt = {}
        for snap in scored_snaps:
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
        final["k_z_score"] = float(k_z)
        final["m_z_score"] = 0.0
        final["analysis"]  = _flatten_analysis(analysis)
        final["visuals"]   = {
            "flight_times":        all_flights,
            "pause_coords":        [],        # not collected during typing
            "question_snapshots":  self._question_snapshots,
            "domain_t2":           domain_t2_avg,
            "level_t2":            level_t2_avg,
            "pre_typing_pauses":   pre_typing_pauses,  # reading latency per question
        }

        final["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if self.normative_mode:
            db.save_normative_session(final)
        else:
            final["session_id"] = db.save_full_intake(final)
        return final
