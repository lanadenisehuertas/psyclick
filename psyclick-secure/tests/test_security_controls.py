import sqlite3
import tempfile
import unittest
from pathlib import Path

import database_manager as db
import security_manager as security


class SecurityControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="psyclick_security_test_")
        root = Path(self.temp.name)
        db.DB_NAME = str(root / "psyclick_test.db")
        security.APP_DIR = root / "appdata"
        security.BACKUP_DIR = security.APP_DIR / "backups"
        db.init_db()

    def tearDown(self):
        self.temp.cleanup()

    def _register(self):
        ok, clinician_id, error = db.register_clinician(
            "Security Test Admin", "SecurePassphrase2026"
        )
        self.assertTrue(ok, error)
        return clinician_id

    def test_password_is_hashed_and_first_account_is_admin(self):
        clinician_id = self._register()
        conn = sqlite3.connect(db.DB_NAME)
        password, password_hash, role = conn.execute(
            "SELECT password, password_hash, role FROM clinicians WHERE clinician_id=?",
            (clinician_id,),
        ).fetchone()
        conn.close()
        self.assertEqual(password, "")
        self.assertNotIn("SecurePassphrase2026", password_hash)
        self.assertTrue(password_hash.startswith("scrypt:"))
        self.assertEqual(role, "admin")
        self.assertTrue(db.verify_clinician(clinician_id, "SecurePassphrase2026")[0])

    def test_password_policy_rejects_weak_password(self):
        ok, _, error = db.register_clinician("Weak User", "password")
        self.assertFalse(ok)
        self.assertIn("12", error)

    def test_security_session_expires_on_revocation(self):
        clinician_id = self._register()
        token, _ = db.create_security_session(clinician_id, "admin")
        identity = db.authenticate_security_session(token)
        self.assertEqual(identity["id"], clinician_id)
        self.assertTrue(db.revoke_security_session(token))
        self.assertIsNone(db.authenticate_security_session(token))

    def test_consent_is_persisted_and_fail_closed(self):
        clinician_id = self._register()
        self.assertFalse(db.has_active_consent("C-001", clinician_id))
        db.record_consent("C-001", clinician_id, "granted", "1.0")
        self.assertTrue(db.has_active_consent("C-001", clinician_id))
        db.record_consent("C-001", clinician_id, "withdrawn", "1.0")
        self.assertFalse(db.has_active_consent("C-001", clinician_id))

    def test_audit_chain_detects_tampering(self):
        clinician_id = self._register()
        db.log_audit("admin", "Created test event", "synthetic", actor_id=clinician_id)
        db.log_audit("admin", "Viewed test event", "synthetic", actor_id=clinician_id)
        valid, checked, invalid_id = db.verify_audit_chain()
        self.assertTrue(valid)
        self.assertEqual(checked, 2)
        self.assertIsNone(invalid_id)

        conn = sqlite3.connect(db.DB_NAME)
        conn.execute("UPDATE audit_log SET detail='tampered' WHERE log_id=1")
        conn.commit(); conn.close()
        valid, _, invalid_id = db.verify_audit_chain()
        self.assertFalse(valid)
        self.assertEqual(invalid_id, 1)

    def test_encrypted_backup_passes_restore_validation(self):
        clinician_id = self._register()
        backup = security.create_encrypted_backup(clinician_id)
        path = Path(backup["file"])
        self.assertTrue(path.exists())
        self.assertNotEqual(path.read_bytes()[:16], b"SQLite format 3\x00")
        result = security.validate_encrypted_backup(path, backup["sha256"])
        self.assertTrue(result["valid"])
        self.assertEqual(result["integrity_check"], "ok")


class IntrusionMonitorTests(unittest.TestCase):
    def setUp(self):
        import intrusion_monitor
        self.im = intrusion_monitor
        self.im.reset()
        self.alerts_logged = []

    def _fake_log_audit(self, actor, action, detail=None, actor_id=None, outcome="success"):
        self.alerts_logged.append((actor, action, detail, outcome))

    def test_no_throttle_below_threshold(self):
        for _ in range(self.im.FAILURE_THRESHOLD - 1):
            result = self.im.record_failure("10.0.0.5", "1", log_audit_fn=self._fake_log_audit)
            self.assertFalse(result["triggered"])
        self.assertEqual(self.im.is_source_throttled("10.0.0.5"), 0)
        self.assertEqual(self.alerts_logged, [])

    def test_throttle_triggers_after_threshold_and_logs_security_audit(self):
        for _ in range(self.im.FAILURE_THRESHOLD):
            result = self.im.record_failure("10.0.0.9", "42", log_audit_fn=self._fake_log_audit)
        self.assertTrue(result["triggered"])
        self.assertGreater(self.im.is_source_throttled("10.0.0.9"), 0)
        self.assertTrue(any(a[0] == "security" and "Intrusion alert" in a[1] for a in self.alerts_logged))
        alerts = self.im.get_recent_alerts()
        self.assertTrue(any(a["source"] == "10.0.0.9" for a in alerts))

    def test_successful_login_clears_failure_history(self):
        for _ in range(self.im.FAILURE_THRESHOLD - 1):
            self.im.record_failure("10.0.0.7", "1", log_audit_fn=self._fake_log_audit)
        self.im.record_success("10.0.0.7", "1")
        for _ in range(self.im.FAILURE_THRESHOLD - 1):
            result = self.im.record_failure("10.0.0.7", "1", log_audit_fn=self._fake_log_audit)
        self.assertFalse(result["triggered"])

    def test_rotating_source_against_single_target_still_detected(self):
        # Simulates a credential-stuffing attack against one account from many IPs.
        result = None
        for i in range(self.im.FAILURE_THRESHOLD):
            result = self.im.record_failure(f"10.0.1.{i}", "99", log_audit_fn=self._fake_log_audit)
        self.assertTrue(result["triggered"])
        self.assertIn("account 99", result["reason"])


if __name__ == "__main__":
    unittest.main()
