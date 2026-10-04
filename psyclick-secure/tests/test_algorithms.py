"""Numerical regression tests for the PsyClick analysis pipeline."""
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np

_TMP = tempfile.TemporaryDirectory(prefix="psyclick_alg_", ignore_cleanup_errors=True)
os.environ.setdefault("PSYCLICK_DB_PATH", str(Path(_TMP.name) / "alg.db"))

import anomaly_engine as ae
import database_manager as db
import feature_extractor as fe

ROOT = Path(__file__).resolve().parent.parent


def _typing_events(n=40, flight=0.2, dwell=0.08, backspace_every=10):
    events, t = [], 0.0
    for i in range(n):
        key = "backspace" if i % backspace_every == backspace_every - 1 else "a"
        events.append({"key": key, "event": "DOWN", "time": t})
        events.append({"key": key, "event": "UP", "time": t + dwell})
        t += flight
    return events


class FeatureExtractionTests(unittest.TestCase):
    def test_keyboard_features_match_known_values(self):
        f = fe.extract_features(_typing_events())
        self.assertAlmostEqual(f["flight_time"], 0.2, places=6)
        self.assertAlmostEqual(f["dwell_time"], 0.08, places=6)
        self.assertAlmostEqual(f["typing_velocity"], 39 / (39 * 0.2), places=6)

    def test_error_rate_counts_backspace_presses_once(self):
        # 4 backspaces in 40 presses; the UP events must not double the count.
        f = fe.extract_features(_typing_events())
        self.assertAlmostEqual(f["error_rate"], 0.10, places=6)

    def test_pause_frequency_counts_gaps_over_one_second(self):
        events, t = [], 0.0
        for gap in [0.2, 0.2, 1.5, 0.2, 0.2, 1.5, 0.2]:
            events += [{"key": "a", "event": "DOWN", "time": t},
                       {"key": "a", "event": "UP", "time": t + 0.05}]
            t += gap
        events += [{"key": "a", "event": "DOWN", "time": t},
                   {"key": "a", "event": "UP", "time": t + 0.05}]
        f = fe.extract_features(events)
        self.assertAlmostEqual(f["pause_frequency"], 2 / t, places=6)

    def test_wma_kernel_is_normalised_and_preserves_constants(self):
        self.assertAlmostEqual(fe._KERNEL.sum(), 1.0)
        out = fe._sliding_wma(np.full(20, 7.0))
        np.testing.assert_allclose(out, 7.0)

    def test_mouse_features_on_straight_line(self):
        t = np.arange(0, 3.0, 0.05)
        events = [{"x": 100 * ti, "y": 0.0, "time": float(ti), "event": "MOVE"} for ti in t]
        f = fe.extract_mouse_features(events)
        # The edge-normalised WMA bends the first/last two samples, so a 3 s
        # window reads ~3.6% low; interior samples are exact.
        self.assertAlmostEqual(f["cursor_velocity"], 100.0, delta=5.0)
        self.assertLess(f["path_entropy"], 0.2)   # one direction -> ~0 bits


class NormativeBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "normative_baseline.json").read_text(encoding="utf-8-sig"))
        cls.mu = np.array(cls.data["mu_pop"])
        cls.S = np.array(cls.data["S_pop"])

    def test_covariance_is_symmetric_positive_definite(self):
        np.testing.assert_allclose(self.S, self.S.T)
        self.assertGreater(np.linalg.eigvalsh(self.S).min(), 0)

    def test_dimensions_match_feature_vector(self):
        self.assertEqual(self.mu.shape, (ae.N_FEATURES,))
        self.assertEqual(self.S.shape, (ae.N_FEATURES, ae.N_FEATURES))

    def test_summary_agrees_with_matrix(self):
        means = list(self.data["summary"]["feature_means"].values())
        stds = list(self.data["summary"]["feature_stds"].values())
        np.testing.assert_allclose(self.mu, means, rtol=1e-9)
        np.testing.assert_allclose(np.sqrt(np.diag(self.S)), stds, rtol=1e-3)

    def test_population_mean_scores_zero(self):
        nb = ae.NormativeBaseline.from_dict(self.data)
        s_inv = ae._covariance_inverse(nb.S_pop, nb.n_pop)
        self.assertAlmostEqual(float((self.mu - nb.mu_pop) @ s_inv @ (self.mu - nb.mu_pop)), 0.0)


class HotellingTests(unittest.TestCase):
    def test_covariance_inverse_matches_formula(self):
        S = np.diag([0.09, 0.04, 4.0, 0.0025, 1.0, 10000.0, 1e12, 0.01])
        s_inv = ae._covariance_inverse(S, 200)
        self.assertEqual(s_inv.shape, S.shape)
        np.testing.assert_allclose(s_inv, s_inv.T, atol=1e-12)
        self.assertGreater(np.linalg.eigvalsh(s_inv).min(), 0)

    def test_t2_is_zero_at_baseline_and_grows_with_distance(self):
        b = ae.EWMABaseline()
        x = np.array([0.15, 0.05, 5.0, 0.01, 2.8, 180.0, 3e5, 0.15])
        for _ in range(4):
            b.update(x)
        near = ae.compute_t2_hybrid(x, b)[0]
        far = ae.compute_t2_hybrid(x * 1.5, b)[0]
        self.assertAlmostEqual(near, 0.0)
        self.assertGreater(far, near)

    def test_contributions_sum_to_ipsative_t2(self):
        b = ae.EWMABaseline()
        rng = np.random.default_rng(3)
        base = np.array([0.15, 0.05, 5.0, 0.01, 2.8, 180.0, 3e5, 0.15])
        for _ in range(4):
            b.update(base * (1 + 0.05 * rng.standard_normal(8)))
        x = base * 1.2
        t2, _, _, _, s_inv = ae.compute_t2_hybrid(x, b)
        C, *_ = ae.compute_contributions_revised(x, b.mu, s_inv, b.ever_seen)
        self.assertAlmostEqual(float(C.sum()), t2, places=6)

    def test_small_sample_threshold_is_chi_square(self):
        self.assertAlmostEqual(ae._t2_threshold_base(4), 15.5073, places=3)

    def test_large_sample_threshold_approaches_chi_square(self):
        self.assertAlmostEqual(ae._t2_threshold_base(100000), 15.5073, delta=0.05)


class EWMATests(unittest.TestCase):
    def test_recursion(self):
        b = ae.EWMABaseline()
        x1 = np.arange(1.0, 9.0)
        x2 = x1 + 2.0
        b.update(x1)
        b.update(x2)
        np.testing.assert_allclose(b.mu, 0.2 * x2 + 0.8 * x1)
        np.testing.assert_allclose(b.S, 0.2 * np.outer(x2 - x1, x2 - x1) + 0.8 * 1e-4 * np.eye(8))

    def test_first_observation_of_a_feature_seeds_its_mean(self):
        b = ae.EWMABaseline()
        kbd = np.array([0.15, 0.05, 5.0, 0.01, 0.0, 0.0, 0.0, 0.15])
        b.update(kbd, mask=np.array([1, 1, 1, 1, 0, 0, 0, 1], bool))
        mouse = np.array([0.0, 0.0, 0.0, 0.0, 2.8, 180.0, 3e5, 0.0])
        b.update(mouse, mask=np.array([0, 0, 0, 0, 1, 1, 1, 0], bool))
        np.testing.assert_allclose(b.mu[4:7], mouse[4:7])
        self.assertAlmostEqual(b.S[5, 5], 0.8 * 1e-4)   # no spurious innovation


class FuzzyAndFlagTests(unittest.TestCase):
    P95 = ae.BOOTSTRAP_THRESHOLDS["task_3"]["p95"]
    P99 = ae.BOOTSTRAP_THRESHOLDS["task_3"]["p99"]

    def _flag(self, t2, psi=0.0, pai=0.0, task="task_3"):
        return ae.fuzzy_classify(t2, self.P95, self.P95, {"total": psi}, pai, task_context=task)

    def test_below_p95_is_green(self):
        self.assertEqual(self._flag(self.P95 * 0.9)["flag"], "GREEN")

    def test_above_p99_with_high_indices_is_red(self):
        self.assertEqual(self._flag(self.P99 * 2, psi=80.0, pai=250.0)["flag"], "RED")

    def test_between_p95_and_p99_is_amber(self):
        self.assertEqual(self._flag((self.P95 + self.P99) / 2, psi=20.0, pai=50.0)["flag"], "AMBER")

    def test_item_cutoffs_are_looser_than_session_cutoffs(self):
        item = ae.BOOTSTRAP_THRESHOLDS["task_3_item"]
        self.assertGreater(item["p95"], self.P95)
        self.assertEqual(self._flag(self.P95 * 1.2, task="task_3_item")["flag"], "GREEN")

    def test_log_normalisation_bounds_and_order(self):
        self.assertEqual(ae._normalise_logscale(0.0, 0.0, 20.0), 0.0)
        a, b = ae._normalise_logscale(20.0, 0.0, 20.0), ae._normalise_logscale(60.0, 0.0, 20.0)
        self.assertAlmostEqual(a, 1 - np.exp(-1), places=6)
        self.assertTrue(0 < a < b < 1)

    def test_memberships_are_valid(self):
        for x in np.linspace(0, 1, 101):
            for v in (ae._trapmf(x, -0.01, 0, 0.3, 0.55), ae._trimf(x, 0.3, 0.55, 0.8)):
                self.assertTrue(0.0 <= v <= 1.0)


class NormativeReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = json.loads((ROOT / "normative_reference.json").read_text(encoding="utf-8"))

    def test_engine_uses_reference_cutoffs(self):
        t = self.ref["thresholds"]
        self.assertAlmostEqual(ae.BOOTSTRAP_THRESHOLDS["task_3"]["p95"], t["session"]["p95"])
        self.assertAlmostEqual(ae.BOOTSTRAP_THRESHOLDS["task_3_item"]["p99"], t["item"]["p99"])
        self.assertAlmostEqual(ae.PSI_SCALE, t["psi_p99"] / 2)

    def test_fallback_matches_shipped_reference(self):
        t = self.ref["thresholds"]
        fb = ae._REFERENCE_FALLBACK
        self.assertAlmostEqual(fb["session"]["p95"], t["session"]["p95"], places=3)
        self.assertAlmostEqual(fb["session"]["p99"], t["session"]["p99"], places=3)
        self.assertAlmostEqual(fb["item"]["p95"], t["item"]["p95"], places=3)
        self.assertAlmostEqual(fb["psi_p99"], t["psi_p99"], places=3)

    def test_reference_population_is_consistent(self):
        c = self.ref["counts"]
        self.assertEqual(c["healthy_reference_testers"], 83)
        for m in self.ref["metrics"].values():
            v = np.array(m["values"])
            self.assertEqual(len(v), m["n"])
            self.assertAlmostEqual(v.mean(), m["mean"], places=9)
            self.assertAlmostEqual(v.std(ddof=1), m["sd"], places=9)
        self.assertTrue(all(x < 10 for x in self.ref["metrics"]["phq_score"]["values"]))
        self.assertTrue(all(x < 10 for x in self.ref["metrics"]["gad_score"]["values"]))

    def test_cutoffs_are_ordered(self):
        t = self.ref["thresholds"]["session"]
        self.assertLess(t["p95_ci95"][0], t["p95"])
        self.assertLess(t["p95"], t["p99"])


class EngagementTests(unittest.TestCase):
    def test_keystroke_tiers(self):
        b = ae.EWMABaseline()
        for count, level in ((0, "LOW"), (10, "PARTIAL"), (30, "FULL")):
            b.keystroke_count = count
            self.assertEqual(b.get_engagement_level(), level)


class NormativeStatsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="psyclick_norm_test_", ignore_cleanup_errors=True)
        self._prev_db = db.DB_NAME
        db.DB_NAME = str(Path(self.temp.name) / "norm.db")
        db.init_db()

    def tearDown(self):
        db.DB_NAME = self._prev_db
        self.temp.cleanup()

    def test_seed_population_is_present(self):
        stats = db.get_normative_stats()["stats"]
        self.assertEqual(set(stats), {"t2_score", "psi", "pai", "phq_score", "gad_score", "flight_time_mean"})
        self.assertTrue(all(s["count"] == 83 for s in stats.values()))

    def test_legacy_seed_is_replaced(self):
        conn = sqlite3.connect(db.DB_NAME)
        conn.execute("DELETE FROM normative_stats")
        conn.execute("INSERT INTO normative_stats (metric, norm_mean, norm_sd, count) VALUES ('t2_score', 20.79, 26.48, 102)")
        conn.commit(); conn.close()
        db._seed_normative_stats()
        stats = db.get_normative_stats()["stats"]
        self.assertEqual(stats["t2_score"]["count"], 83)
        self.assertEqual(len(stats), 6)

    def test_recompute_excludes_cold_start_artifacts(self):
        conn = sqlite3.connect(db.DB_NAME)
        rows = [("T-004", 10.0), ("T-005", 20.0), ("T-006", 30.0), ("T-001", 5231.0)]
        for tid, t2 in rows:
            conn.execute(
                "INSERT INTO normative_sessions (tester_id,t2_score,t2_threshold,psi,pai,phq_score,gad_score,"
                "kbase_mean,kbase_std,flight_time_mean,domain_t2_json,level_t2_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (tid, t2, 15.5073, 1.0, 1.0, 3, 3, 0.1, 0.1, 0.1, "{}", "{}"))
        conn.commit(); conn.close()
        self.assertTrue(db.compute_normative_stats())
        t2 = db.get_normative_stats()["stats"]["t2_score"]
        self.assertEqual(t2["count"], 3)
        self.assertAlmostEqual(t2["mean"], 20.0)
        self.assertAlmostEqual(t2["sd"], 10.0)


if __name__ == "__main__":
    unittest.main()
