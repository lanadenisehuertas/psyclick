"""
backend_controller.py  —  PsyClick
Orchestrates the full single-session pipeline:

    HAL (dynamics_logger)
    → Sliding Window WMA + Feature Extraction (feature_extractor)
    → Within-Session EWMA baseline (anomaly_engine.AnomalyEngine)
    → Hotelling's T² + Feature Contribution + Fuzzy Logic + Decision Tree
      (anomaly_engine.AnomalyEngine.analyse)
    → Database persistence (database_manager)

One AnomalyEngine instance lives for the duration of the session and is
reset when a new session starts.  EWMA state is never written to disk.
"""

import database_manager as db
import dynamics_logger  as dl
import feature_extractor as fe
from anomaly_engine import AnomalyEngine


class PsyClickController:

    def __init__(self):
        db.init_db()

        # Shared HAL — one instance per application lifetime
        self.hal          = dl.HardwareAbstractionLayer()
        self.key_logger   = dl.KeyLogger(self.hal)
        self.mouse_logger = dl.MouseLogger(self.hal)

        # Per-session anomaly engine (reset on each new intake)
        self.engine = AnomalyEngine()

        self._empty_mouse = {
            "hv": 0, "vv": 0, "tv": 0, "ta": 0,
            "jerk": 0, "curvature": 0,
            "path_entropy": 0, "cursor_velocity": 0, "pause_frequency": 0,
        }

        self._reset_session()

    # ── Session lifecycle ──────────────────────────────────────────────────────
    def _reset_session(self):
        self.session_data = {
            "student_id": None,
            "kbase": {"mean_flight": 0, "std_flight": 0},
            "mbase": dict(self._empty_mouse),
            "phq":   {"score": 0, "mouse": dict(self._empty_mouse)},
            "gad":   {"score": 0, "mouse": dict(self._empty_mouse)},
            "task":  {"mean_flight": 0, "std_flight": 0},
        }
        self.engine = AnomalyEngine()   # fresh EWMA state for this session

    def set_student_id(self, sid):
        self._reset_session()
        self.session_data["student_id"] = sid

    # ── Capture helpers ────────────────────────────────────────────────────────
    def start_key_capture(self, calibration_mode=False):
        self.key_logger.start_logging(calibration_mode=calibration_mode)

    def start_mouse_capture(self):
        self.mouse_logger.start_logging()

    # ── Calibration phase ──────────────────────────────────────────────────────
    def save_kbase(self):
        """
        Stop keyboard capture (calibration_mode finalises HAL delta_latency).
        Extract features → feed into EWMA baseline → store as kbase.
        """
        raw   = self.key_logger.stop_logging()
        feats = fe.extract_features(raw)
        if feats:
            self.session_data["kbase"] = feats
            # Feed calibration window into EWMA baseline
            self.engine.update_baseline(feats)
        return feats is not None

    def save_mbase(self):
        raw   = self.mouse_logger.stop_logging()
        feats = fe.extract_mouse_features(raw)
        if feats:
            self.session_data["mbase"] = feats
            # Also feed mouse calibration into EWMA baseline
            self.engine.update_baseline(feats)
        return feats is not None

    # ── PHQ / GAD ─────────────────────────────────────────────────────────────
    def save_phq(self, total_score):
        raw   = self.mouse_logger.stop_logging()
        feats = fe.extract_mouse_features(raw)
        self.session_data["phq"]["score"] = total_score
        if feats:
            self.session_data["phq"]["mouse"] = feats

    def save_gad(self, total_score):
        raw   = self.mouse_logger.stop_logging()
        feats = fe.extract_mouse_features(raw)
        self.session_data["gad"]["score"] = total_score
        if feats:
            self.session_data["gad"]["mouse"] = feats

    # ── Assessment phase ───────────────────────────────────────────────────────
    def process_final_task(self):
        """
        Stop task keyboard capture.
        Run the full pipeline:
            Feature Extraction → Hotelling T2 → Feature Contribution
            → Fuzzy Logic + Decision Tree
        Save to database and return the complete result dict.

        Returns a result dict even when the EWMA baseline is not ready,
        so the report page always receives data and never silently fails.
        """
        raw        = self.key_logger.stop_logging()
        task_feats = fe.extract_features(raw)

        # ── Bug fix: if not enough keystrokes, use last known kbase values
        # so the session still saves and the report still shows.
        if not task_feats:
            task_feats = {
                "mean_flight":     self.session_data["kbase"].get("mean_flight", 0),
                "std_flight":      self.session_data["kbase"].get("std_flight", 0),
                "flight_time":     self.session_data["kbase"].get("mean_flight", 0),
                "dwell_time":      0.0,
                "typing_velocity": 0.0,
                "error_rate":      0.0,
                "key_count":       0,
            }

        self.session_data["task"] = task_feats

        # ── Legacy Z-scores ────────────────────────────────────────────────────
        kb = self.session_data["kbase"]
        if kb.get("std_flight", 0) > 0:
            k_z = (task_feats["mean_flight"] - kb["mean_flight"]) / kb["std_flight"]
        else:
            k_z = 0.0

        # You MUST define these variables BEFORE the if-statement uses them
        mb    = self.session_data["mbase"]
        phq_m = self.session_data["phq"]["mouse"]
        gad_m = self.session_data["gad"]["mouse"]

        avg_test_jerk = (phq_m.get("jerk", 0) + gad_m.get("jerk", 0)) / 2
        
        # Safe Mouse Z-score (Prevent NaN or division by zero)
        if mb.get("jerk", 0) > 0:
            m_z = (avg_test_jerk - mb["jerk"]) / mb["jerk"]
        else:
            m_z = 0.0
            
        # ── New pipeline ───────────────────────────────────────────────────────
        # Stop mouse logger once — guard against already-stopped state
        try:
            mouse_raw = self.mouse_logger.stop_logging()
        except Exception:
            mouse_raw = []
        mouse_feats = fe.extract_mouse_features(mouse_raw) or {}

        # Feed the task window into EWMA so the engine always has at least
        # one baseline window to work with if calibration was minimal.
        combined = {**task_feats, **mouse_feats}
        self.engine.update_baseline(combined)

        analysis = self.engine.analyse(combined)

        # ── Assemble final record ──────────────────────────────────────────────
        final_record              = self.session_data.copy()
        final_record["k_z_score"] = k_z
        final_record["m_z_score"] = m_z
        final_record["analysis"]  = analysis or {}

        # --- NEW: Add the raw visual arrays to the final payload ---
        final_record["visuals"] = {
            "flight_times": task_feats.get("raw_flight_times", []) if task_feats else [],
            "pause_coords": mouse_feats.get("pause_coords", []) if mouse_feats else []
        }

        db.save_full_intake(final_record)
        return final_record
