import database_manager as db
import dynamics_logger as dl
import feature_extractor as fe

class PsyClickController:
    def __init__(self):
        db.init_db()
        self.key_logger = dl.KeyLogger()
        self.mouse_logger = dl.MouseLogger()
        
        # Zero-filled default for safety
        self.empty_mouse = {'hv':0, 'vv':0, 'tv':0, 'ta':0, 'jerk':0, 'curvature':0}
        
        self.session_data = {
            'student_id': None,
            'kbase': {'mean_flight': 0, 'std_flight': 0},
            'mbase': self.empty_mouse,
            'phq': {'score': 0, 'mouse': self.empty_mouse},
            'gad': {'score': 0, 'mouse': self.empty_mouse},
            'task': {'mean_flight': 0, 'std_flight': 0}
        }

    def set_student_id(self, sid):
        self.session_data['student_id'] = sid

    # --- Capture & Save ---
    def start_key_capture(self):
        self.key_logger.start_logging()

    def start_mouse_capture(self):
        self.mouse_logger.start_logging()

    def save_kbase(self):
        raw = self.key_logger.stop_logging()
        feats = fe.extract_features(raw)
        if feats: self.session_data['kbase'] = feats
        return feats is not None

    def save_mbase(self):
        raw = self.mouse_logger.stop_logging()
        # Uses your new function to get Velocity/Jerk/Curvature
        feats = fe.extract_mouse_features(raw) 
        if feats: self.session_data['mbase'] = feats
        return feats is not None

    def save_phq(self, total_score):
        raw = self.mouse_logger.stop_logging()
        feats = fe.extract_mouse_features(raw)
        self.session_data['phq']['score'] = total_score
        if feats: self.session_data['phq']['mouse'] = feats

    def save_gad(self, total_score):
        raw = self.mouse_logger.stop_logging()
        feats = fe.extract_mouse_features(raw)
        self.session_data['gad']['score'] = total_score
        if feats: self.session_data['gad']['mouse'] = feats

    # --- Analysis ---
    def process_final_task(self):
        raw = self.key_logger.stop_logging()
        task_feats = fe.extract_features(raw)
        if not task_feats: return None
        
        self.session_data['task'] = task_feats
        
        # 1. Keyboard Z-Score (Speed)
        # Z = (Task_Mean - KBase_Mean) / KBase_Std
        kb = self.session_data['kbase']
        if kb['std_flight'] > 0:
            k_z = (task_feats['mean_flight'] - kb['mean_flight']) / kb['std_flight']
        else:
            k_z = 0

        # 2. Mouse Z-Score (Agitation/Jerk)
        # We use 'Jerk' as the primary metric for anxiety/agitation
        mb = self.session_data['mbase']
        phq_m = self.session_data['phq']['mouse']
        gad_m = self.session_data['gad']['mouse']
        
        # Average Jerk during PHQ and GAD
        avg_test_jerk = (phq_m['jerk'] + gad_m['jerk']) / 2
        
        # Prevent division by zero if baseline jerk is 0
        if mb['jerk'] > 0:
            # We assume standard deviation of baseline is approx 20% of mean if not calculated 
            # (since we only have one baseline value, we can't calculate std of the baseline itself yet)
            # A common heuristic for single-point baseline comparison is:
            # Z = (Test - Baseline) / Baseline
            # But for bell curve viz, let's normalize it:
            m_z = (avg_test_jerk - mb['jerk']) / mb['jerk'] 
            # Note: This is a % difference, treated as a Z-proxy for the chart
        else:
            m_z = 0

        final_record = self.session_data.copy()
        final_record['k_z_score'] = k_z
        final_record['m_z_score'] = m_z

        db.save_full_intake(final_record)
        return final_record