"""End-to-end API test: a full simulated assessment session through the real
Flask app, controller, feature extractor, anomaly engine and database.

Keyboard/mouse hooks are replaced by scripted loggers so the test needs no
physical input device or display."""
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

_TMP = tempfile.TemporaryDirectory(prefix="psyclick_e2e_", ignore_cleanup_errors=True)
os.environ["PSYCLICK_SECURE_HOME"] = _TMP.name
_E2E_DB = str(Path(_TMP.name) / "e2e.db")
os.environ["PSYCLICK_DB_PATH"] = _E2E_DB

import dynamics_logger as dl  # noqa: E402
import database_manager as db  # noqa: E402
import security_manager as security  # noqa: E402

db.DB_NAME = _E2E_DB
security.APP_DIR = Path(_TMP.name) / "appdata"
security.BACKUP_DIR = security.APP_DIR / "backups"


class _ScriptedKeys:
    def __init__(self, hal):
        self.hal, self.raw_data, self.script = hal, [], []

    def start_logging(self, calibration_mode=False, on_first_key=None):
        self.raw_data = list(self.script)

    def stop_logging(self):
        out, self.raw_data = self.raw_data, []
        return out


class _ScriptedMouse:
    def __init__(self, hal):
        self.hal, self.raw_data, self.script = hal, [], []

    def start_logging(self):
        self.raw_data = list(self.script)

    def stop_logging(self):
        out, self.raw_data = self.raw_data, []
        return out


dl.KeyLogger, dl.MouseLogger = _ScriptedKeys, _ScriptedMouse

import api_server  # noqa: E402
from backend_controller import PsyClickController  # noqa: E402


def typing(rng, n=60, flight=0.16, dwell=0.07, backspace_p=0.04, pause_p=0.0):
    ev, t = [], 100.0
    for _ in range(n):
        key = "backspace" if rng.random() < backspace_p else "abcdefgh"[rng.integers(8)]
        ev.append({"key": key, "event": "DOWN", "time": t})
        ev.append({"key": key, "event": "UP", "time": t + dwell + rng.normal(0, 0.01)})
        t += max(0.03, flight + rng.normal(0, 0.04)) + (1.6 if rng.random() < pause_p else 0.0)
    return ev


def mouse(rng, n=120, speed=180.0):
    t, x, y, ev = 50.0, 500.0, 400.0, []
    for _ in range(n):
        t += 0.016
        x += speed * 0.016 * np.cos(rng.uniform(-1, 1)) + rng.normal(0, 1)
        y += speed * 0.016 * np.sin(rng.uniform(-1, 1)) + rng.normal(0, 1)
        ev.append({"x": float(x), "y": float(y), "time": t, "event": "MOVE"})
    return ev


QUESTIONS = [
    {"item_id": f"{lv}{i}", "group_id": g, "level": lv, "domain_label": dom,
     "group_name": f"Group {g}", "level_name": f"Level {lv}", "prompt": "Describe a recent time you felt pressure."}
    for g, dom in ((1, "time_workload"), (2, "interpersonal"), (3, "academic_performance"), (4, "self_evaluation"))
    for lv in "ABC" for i in (g,)
][:12]


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.DB_NAME = _E2E_DB
        db.init_db()
        api_server.back = PsyClickController()
        api_server._back_ready = True
        cls.c = api_server.app.test_client()
        cls.rng = np.random.default_rng(7)
        r = cls.c.post("/api/register", json={"name": "Dr. Admin", "password": "CorrectHorse!2026"}).get_json()
        assert r["success"], r
        cls.admin_id = r["clinician_id"]
        cls.token = cls.c.post("/api/login", json={"id": str(cls.admin_id), "password": "CorrectHorse!2026"}).get_json()["token"]
        cls.h = {"Authorization": f"Bearer {cls.token}"}

    def post(self, path, **body):
        return self.c.post(path, json=body, headers=self.h)

    def get(self, path):
        return self.c.get(path, headers=self.h)

    def run_session(self, patient, flight, pause_p, backspace_p, text_len=60, typed=lambda qi: True, response="x" * 80):
        back = api_server.back
        r = self.post("/api/intake/start", patient_id=patient, consent=True)
        self.assertTrue(r.get_json()["success"], r.get_json())
        back.key_logger.script = typing(self.rng, 70, 0.16, 0.07, 0.03)
        self.post("/api/calibration/keyboard/start"); self.post("/api/calibration/keyboard/save")
        back.mouse_logger.script = mouse(self.rng, 140, 180)
        self.post("/api/calibration/mouse/start"); self.post("/api/calibration/mouse/save")
        back.mouse_logger.script = mouse(self.rng, 140, 180)
        self.post("/api/assessment/phq/start"); self.post("/api/assessment/phq/save", score=4)
        self.post("/api/assessment/gad/start"); self.post("/api/assessment/gad/save", score=3)
        back.mouse_logger.script = []
        self.post("/api/assessment/emotional/start")
        for qi, q in enumerate(QUESTIONS):
            self.post("/api/assessment/question/set", question=q)
            # what the patient typed for this item since logging (re)started
            back.key_logger.raw_data = typing(self.rng, text_len, flight, 0.07, backspace_p, pause_p) if typed(qi) else []
            self.post("/api/assessment/word-boxes", boxes=[{"word": "pressure", "x1": 0, "y1": 0, "x2": 50, "y2": 20}])
            self.post("/api/assessment/question/snapshot", question=q, response=response if typed(qi) else "", qi=qi, total=12)
        back.key_logger.script = []
        return self.post("/api/assessment/finish").get_json()

    # ── security gates ────────────────────────────────────────────────────────
    def test_01_requires_authentication(self):
        self.assertEqual(self.c.get("/api/patients").status_code, 401)

    def test_02_consent_gate_blocks_capture(self):
        r = self.post("/api/intake/start", patient_id="C-900", consent=False)
        self.assertEqual(r.status_code, 400)

    # ── full session ──────────────────────────────────────────────────────────
    def test_03_full_session_produces_valid_report(self):
        rep = self.run_session("C-001", flight=0.16, pause_p=0.0, backspace_p=0.03)
        self.assertTrue(rep["success"], rep)
        a = rep["report"]["analysis"]
        for k in ("t2_score", "psi", "pai", "confidence"):
            self.assertTrue(np.isfinite(a[k]), (k, a))
            self.assertGreaterEqual(a[k], 0.0)
        self.assertIn(a["flag"], ("GREEN", "AMBER", "RED"))
        self.assertTrue(a["rationale"])
        self.assertEqual(len(rep["report"]["visuals"]["question_snapshots"]), 12)
        self.assertEqual(set(rep["report"]["visuals"]["domain_t2"]), {"1", "2", "3", "4"})

    def test_04_typical_typing_is_not_flagged_but_disturbed_typing_scores_higher(self):
        calm = self.run_session("C-002", 0.16, 0.0, 0.03)["report"]["analysis"]
        slow = self.run_session("C-003", 0.55, 0.25, 0.22)["report"]["analysis"]
        self.assertEqual(calm["flag"], "GREEN")
        self.assertGreater(slow["t2_score"], calm["t2_score"])
        self.assertGreater(slow["psi"], calm["psi"])

    def test_05_sessions_are_persisted_and_retrievable(self):
        patients = self.get("/api/patients").get_json()
        self.assertGreaterEqual(len(patients), 1)
        recent = self.get("/api/sessions/recent").get_json()
        self.assertTrue(len(recent) >= 1)
        sid = recent[0].get("session_id") or recent[0].get("id")
        self.assertEqual(self.get(f"/api/session/{sid}").status_code, 200)
        cmp = self.get(f"/api/normative/compare/{sid}").get_json()
        self.assertTrue(cmp["available"])
        self.assertIn("t2_score", cmp["metrics"])

    def test_06_normative_baseline_is_loaded_by_the_engine(self):
        self.assertTrue(api_server.back.engine.norm_baseline.is_initialized)
        self.assertTrue(self.get("/api/db-health").get_json()["normative_baseline_loaded"])
        stats = self.get("/api/normative/stats").get_json()
        self.assertTrue(stats["baseline_ready"])

    def test_07_report_export_is_encrypted(self):
        rep = self.run_session("C-004", 0.16, 0.0, 0.03)["report"]
        r = self.post("/api/export/report", report=rep).get_json()
        self.assertTrue(r["success"], r)
        self.assertTrue(Path(r["file"]).exists())

    def test_08_audit_chain_and_backup(self):
        self.assertTrue(self.get("/api/audit/verify").get_json()["valid"])
        b = self.post("/api/admin/backup").get_json()
        self.assertTrue(b["success"], b)

    def test_09_role_enforcement_and_account_provisioning(self):
        r = self.post("/api/register", name="Dr. Clinician", password="AnotherStrong#2026", role="clinician").get_json()
        self.assertTrue(r["success"], r)
        tok = self.c.post("/api/login", json={"id": str(r["clinician_id"]), "password": "AnotherStrong#2026"}).get_json()["token"]
        h2 = {"Authorization": f"Bearer {tok}"}
        self.assertEqual(self.c.get("/api/admin/users", headers=h2).status_code, 403)
        self.assertEqual(self.c.get("/api/audit", headers=h2).status_code, 403)

    # ── situational edge cases ────────────────────────────────────────────────
    def test_11_skipped_items_are_not_scored(self):
        rep = self.run_session("C-011", 0.16, 0.0, 0.03, typed=lambda qi: qi % 2 == 1)["report"]
        snaps = rep["visuals"]["question_snapshots"]
        self.assertTrue(all(s["flag"] == "NO_DATA" and s["t2_score"] == 0.0 for s in snaps[0::2]))
        self.assertTrue(all(s["flag"] != "NO_DATA" for s in snaps[1::2]))
        self.assertEqual(rep["analysis"]["flag"], "GREEN")

    def test_12_short_answers_do_not_raise_false_alarm(self):
        rep = self.run_session("C-012", 0.16, 0.0, 0.03, text_len=4, response="ok")["report"]
        self.assertEqual(rep["analysis"]["flag"], "GREEN")

    def test_13_no_typing_is_reported_as_insufficient_not_disturbed(self):
        a = self.run_session("C-013", 0.16, 0.0, 0.03, typed=lambda qi: False)["report"]["analysis"]
        self.assertEqual(a["label"], "Insufficient Data")
        self.assertEqual(a["flag"], "AMBER")
        self.assertEqual(a["t2_score"], 0.0)

    def test_14_questionnaire_scores_are_validated(self):
        self.post("/api/intake/start", patient_id="C-014", consent=True)
        self.assertEqual(self.post("/api/assessment/phq/save", score=28).status_code, 400)
        self.assertEqual(self.post("/api/assessment/gad/save", score=-1).status_code, 400)
        self.assertEqual(self.post("/api/assessment/gad/save", score="5").status_code, 400)
        self.assertEqual(self.post("/api/assessment/phq/save", score=27).status_code, 200)

    def test_10_logout_revokes_token(self):
        tok = self.c.post("/api/login", json={"id": str(self.admin_id), "password": "CorrectHorse!2026"}).get_json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        self.assertEqual(self.c.get("/api/patients", headers=h).status_code, 200)
        self.c.post("/api/logout", headers=h)
        self.assertEqual(self.c.get("/api/patients", headers=h).status_code, 401)


if __name__ == "__main__":
    unittest.main()
