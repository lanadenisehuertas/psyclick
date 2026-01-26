import database_manager as db
import dynamics_logger as dl
import feature_extractor as fe
import anomaly_engine as ae

class PsyClickController:
    def __init__(self):
        print(">> Backend: Initializing Systems...")
        db.init_db()
        self.logger = dl.KeyLogger()
        self.current_student_id = None

    def set_student_id(self, student_id):
        self.current_student_id = student_id
        print(f">> Backend: Active Student set to {student_id}")

    def start_capture(self):
        if not self.current_student_id:
            raise ValueError("No student ID set!")
        self.logger.start_logging()

    def stop_capture_and_save_baseline(self):
        raw_data = self.logger.stop_logging()
        features = fe.extract_features(raw_data)
        if features:
            db.save_user_baseline(self.current_student_id, features['mean_flight'], features['std_flight'])
            return True, "Baseline Saved"
        return False, "Insufficient Data"

    def stop_capture_and_analyze(self):
        raw_data = self.logger.stop_logging()
        features = fe.extract_features(raw_data)
        if not features:
            return None
        z_score, is_anomaly = ae.analyze_session(self.current_student_id, features)
        db.save_session(self.current_student_id, features['mean_flight'], z_score, is_anomaly)
        return {"z_score": z_score, "is_anomaly": is_anomaly, "mean_flight": features['mean_flight']}
