"""Numerical regression tests for the PsyClick analysis pipeline."""
import json
import os
os.environ["PSYCLICK_SYNC_URL"] = ""   # tests never touch the cloud
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

    def test_label_follows_the_dominant_index(self):
        # Marked slowing with little restlessness must read as slowing at any
        # level of overall change, never as agitation.
        for t2 in (self.P95 * 0.85, self.P95 * 1.2, self.P99 * 1.5):
            self.assertEqual(self._flag(t2, psi=50.0, pai=20.0)["label"], "Psychomotor Retardation")
            self.assertEqual(self._flag(t2, psi=3.0, pai=150.0)["label"], "Psychomotor Agitation")

    def test_high_change_with_moderate_indices_is_not_normal(self):
        r = self._flag(self.P99 * 1.5, psi=12.0, pai=30.0)
        self.assertNotEqual(r["label"], "Normal")
        self.assertEqual(r["flag"], "AMBER")

    def test_high_change_with_a_high_index_stays_red(self):
        r = self._flag(self.P99 * 1.5, psi=150.0, pai=18.0)
        self.assertEqual((r["flag"], r["label"]), ("RED", "Psychomotor Retardation"))

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
        self.assertEqual(c["healthy_reference_testers"], 71)
        # no session with humanly impossible typing (doubled-keystroke capture fault)
        self.assertTrue(all(x >= 0.08 for x in self.ref["metrics"]["flight_time_mean"]["values"]))
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


class HoverWordTests(unittest.TestCase):
    def _map(self, boxes, moves):
        import backend_controller as bc
        fake = type("C", (), {})()
        fake._word_boxes = boxes
        return bc.PsyClickController._map_hover_words(fake, moves, [])

    BOXES = [  # padded boxes overlap between neighbouring words
        {"word": "feel", "x1": 0, "y1": 0, "x2": 80, "y2": 40},
        {"word": "alone", "x1": 60, "y1": 0, "x2": 160, "y2": 40},
    ]

    def test_overlap_goes_to_the_nearest_word(self):
        # x=78 is inside both boxes; it is 32 px from "alone" and 38 px from "feel"
        moves = [{"x": 78, "y": 20, "time": 0.0}, {"x": 300, "y": 300, "time": 1.0}]
        out = self._map(self.BOXES, moves)
        self.assertEqual(out[0]["word"], "alone")

    def test_long_stillness_is_capped(self):
        moves = [{"x": 120, "y": 20, "time": 0.0}, {"x": 300, "y": 300, "time": 60.0}]
        out = self._map(self.BOXES, moves)
        self.assertEqual(out[0]["word"], "alone")
        self.assertAlmostEqual(out[0]["dwell_ms"], 5000.0)

    def test_short_movement_gaps_are_ignored(self):
        moves = [{"x": 120, "y": 20, "time": 0.0}, {"x": 125, "y": 20, "time": 0.05}]
        self.assertEqual(self._map(self.BOXES, moves), [])


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
        self.assertTrue(all(s["count"] == 71 for s in stats.values()))

    def test_outdated_seed_is_replaced(self):
        conn = sqlite3.connect(db.DB_NAME)
        conn.execute("DELETE FROM normative_stats")
        conn.execute("DELETE FROM sync_state WHERE key='normative_source'")
        conn.execute("INSERT INTO normative_stats (metric, norm_mean, norm_sd, count) VALUES ('t2_score', 19.66, 24.87, 83)")
        conn.commit(); conn.close()
        db._seed_normative_stats()
        stats = db.get_normative_stats()["stats"]
        self.assertEqual(stats["t2_score"]["count"], 71)
        self.assertEqual(len(stats), 6)

    def test_recompute_excludes_cold_start_artifacts(self):
        conn = sqlite3.connect(db.DB_NAME)
        rows = [("T-004", 10.0), ("T-005", 20.0), ("T-006", 30.0), ("T-001", 5231.0)]
        for tid, t2 in rows:
            conn.execute(
                "INSERT INTO normative_sessions (tester_id,t2_score,t2_threshold,psi,pai,phq_score,gad_score,"
                "kbase_mean,kbase_std,flight_time_mean,domain_t2_json,level_t2_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (tid, t2, 15.5073, 1.0, 1.0, 3, 3, 0.15, 0.1, 0.15, "{}", "{}"))
        conn.commit(); conn.close()
        self.assertTrue(db.compute_normative_stats())
        t2 = db.get_normative_stats()["stats"]["t2_score"]
        self.assertEqual(t2["count"], 3)
        self.assertAlmostEqual(t2["mean"], 20.0)
        self.assertAlmostEqual(t2["sd"], 10.0)


class FullSessionTests(unittest.TestCase):
    """A complete simulated session through the real controller and database."""

    @classmethod
    def setUpClass(cls):
        import random
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from backend_controller import PsyClickController
        from demo_simulation import run_session
        cls.final = run_session(PsyClickController(), db,
                                {"client": "T-FULL", "phq": 11, "gad": 6, "item9": 2,
                                 "linger": {"C4": {"hard?": 2.0}}},
                                clinician_id=1, rng=random.Random(7))

    def test_session_saves_on_a_fresh_database(self):
        conn = sqlite3.connect(db.DB_NAME)
        row = conn.execute("SELECT phq_score, gad_score, phq_item9, flag FROM intake_sessions WHERE session_id=?",
                           (self.final["session_id"],)).fetchone()
        conn.close()
        self.assertEqual(row[:3], (11, 6, 2))
        self.assertIn(row[3], {"GREEN", "AMBER", "RED"})

    def test_every_prompt_is_scored_and_hover_is_mapped(self):
        snaps = self.final["visuals"]["question_snapshots"]
        self.assertEqual(len(snaps), 12)
        self.assertTrue(all(s["flag"] != "NO_DATA" for s in snaps))
        c4 = next(s for s in snaps if s["item_id"] == "C4")
        self.assertEqual(c4["hover_words"][0]["word"], "hard?")
        self.assertAlmostEqual(c4["hover_words"][0]["dwell_ms"], 2000, delta=50)


class TypingPlausibilityTests(unittest.TestCase):
    def test_human_typing_passes(self):
        self.assertIsNone(fe.typing_problem(_typing_events(60, flight=0.17)))

    def test_injected_text_is_caught(self):
        ev = []                               # different keys arriving in the same instant
        for i in range(60):
            t = (i // 3) * 0.17
            ev += [{"key": "qwertyuiop"[i % 10], "event": "DOWN", "time": t},
                   {"key": "qwertyuiop"[i % 10], "event": "UP", "time": t + 0.0001}]
        self.assertEqual(fe.typing_problem(ev), "automatic")

    def test_doubled_hook_events_are_not_flagged_and_score_the_same(self):
        ev = _typing_events(60, flight=0.17)
        doubled = sorted(ev + [dict(e) for e in ev], key=lambda e: e["time"])
        self.assertIsNone(fe.typing_problem(doubled))
        a, b = fe.extract_features(ev), fe.extract_features(doubled)
        for k in ("flight_time", "dwell_time", "typing_velocity", "error_rate", "pause_frequency"):
            self.assertAlmostEqual(a[k], b[k], places=9)

    def test_fast_natural_typing_passes(self):
        import random
        rng, ev, t = random.Random(4), [], 0.0
        for i in range(200):   # ~110 wpm with frequent overlapping keys
            t += max(0.004, rng.gauss(0.09, 0.05))
            ev += [{"key": "abcdefgh"[i % 8], "event": "DOWN", "time": t},
                   {"key": "abcdefgh"[i % 8], "event": "UP", "time": t + 0.08}]
        self.assertIsNone(fe.typing_problem(ev))

    def test_held_key_is_caught(self):
        ev = [{"key": "a", "event": "DOWN", "time": 0.5 + 0.033 * i} for i in range(40)]
        ev.append({"key": "a", "event": "UP", "time": 2.0})
        self.assertEqual(fe.typing_problem(ev), "held_key")

    def test_rejected_warm_up_never_becomes_the_baseline(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from backend_controller import PsyClickController
        from demo_simulation import FakeLogger
        ctrl = PsyClickController()
        ctrl.key_logger = FakeLogger()
        ctrl.key_logger.next = [{"key": "a", "event": e, "time": 1.0 + (i // 2) * 0.001}
                                for i, e in enumerate(["DOWN", "UP"] * 80)]
        self.assertFalse(ctrl.save_kbase())
        self.assertEqual(ctrl.kbase_problem, "automatic")
        self.assertFalse(ctrl.engine.baseline.is_ready)


class RobustAverageTests(unittest.TestCase):
    """Skipping, idling and switching windows must not move the averages."""

    @staticmethod
    def _typing(seed=1, n=120):
        import random
        rng, ev, t = random.Random(seed), [], 0.0
        for i in range(n):
            t += max(0.05, rng.gauss(0.17, 0.05)) + (rng.uniform(1.2, 3) if rng.random() < 0.03 else 0)
            k = "abcdefg"[i % 7]
            ev += [{"key": k, "event": "DOWN", "time": t}, {"key": k, "event": "UP", "time": t + 0.09}]
        return ev

    @staticmethod
    def _cut(ev):
        """Event index of a key press that follows an ordinary (< 0.5 s) gap."""
        downs = [i for i, e in enumerate(ev) if e["event"] == "DOWN"]
        return next(i for p, i in zip(downs, downs[1:]) if i > 50 and ev[i]["time"] - ev[p]["time"] < 0.5)

    def _close(self, a, b, tol=0.01):
        for k in ("flight_time", "dwell_time", "typing_velocity", "error_rate", "pause_frequency"):
            self.assertAlmostEqual(a[k], b[k], delta=max(1e-9, abs(a[k]) * tol), msg=k)

    def test_time_away_is_left_out(self):
        ev = self._typing()
        cut = self._cut(ev)
        away = [dict(e, time=e["time"] + (300 if i >= cut else 0)) for i, e in enumerate(ev)]
        a, b = fe.extract_features(ev), fe.extract_features(away)
        self._close(a, b)
        self.assertEqual(len(b["away_gaps"]), 1)
        self.assertGreater(b["away_gaps"][0], 299)

    def test_focus_break_is_left_out(self):
        ev = self._typing()
        cut = self._cut(ev)
        brk = (ev[:cut] + [{"key": None, "event": "BREAK", "time": ev[cut - 1]["time"] + 0.01}]
               + [dict(e, time=e["time"] + 7) for e in ev[cut:]])
        a, b = fe.extract_features(ev), fe.extract_features(brk)
        self._close(a, b)
        self.assertEqual(b["breaks"], 1)

    def test_thinking_pauses_still_count(self):
        ev = self._typing()
        cut = self._cut(ev)
        paused = [dict(e, time=e["time"] + (8 if i >= cut else 0)) for i, e in enumerate(ev)]
        a, b = fe.extract_features(ev), fe.extract_features(paused)
        self.assertEqual(b["away_gaps"], [])
        pauses = lambda f: sum(1 for g in f["raw_flight_times"] if g > 1.0)
        self.assertEqual(pauses(b), pauses(a) + 1)          # an 8 s pause is still a pause

    def test_suspended_logger_drops_keys_and_marks_the_gap(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("dl_real", ROOT / "dynamics_logger.py")
        dl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dl)       # the real module (another test swaps in a fake)

        class K:
            def __init__(self, c):
                self.char = c
        lg = dl.KeyLogger(dl.HardwareAbstractionLayer())
        lg.start_logging()
        for c in "ab":
            lg.on_press(K(c)); lg.on_release(K(c))
        lg.suspend()
        lg.on_press(K("x")); lg.on_release(K("x"))
        lg.resume()
        lg.on_press(K("d")); lg.on_release(K("d"))
        data = lg.stop_logging()
        self.assertNotIn("x", [e["key"] for e in data])
        self.assertEqual([e["event"] for e in data].count("BREAK"), 1)


class OverallStatusTests(unittest.TestCase):
    def test_behaviour_alone_when_questionnaires_are_low(self):
        self.assertEqual(db.overall_status("GREEN", 4, 3, 0), ("GREEN", []))
        self.assertEqual(db.overall_status("RED", 4, 3, 0)[0], "RED")

    def test_self_harm_answer_is_never_no_concerns(self):
        flag, why = db.overall_status("GREEN", 6, 4, 1)
        self.assertEqual(flag, "RED")
        self.assertIn("self-harm", why[0])

    def test_questionnaire_cut_offs(self):
        self.assertEqual(db.overall_status("GREEN", 10, 0, 0)[0], "AMBER")
        self.assertEqual(db.overall_status("GREEN", 0, 10, 0)[0], "AMBER")
        self.assertEqual(db.overall_status("GREEN", 20, 0, 0)[0], "RED")
        self.assertEqual(db.overall_status("GREEN", 0, 15, 0)[0], "RED")
        self.assertEqual(db.overall_status("AMBER", 12, 0, 0)[0], "AMBER")   # never lowered

    def test_too_little_typing_is_repeat_unless_questionnaires_need_follow_up(self):
        self.assertEqual(db.overall_status("REPEAT", 4, 3, 0), ("REPEAT", []))
        self.assertEqual(db.overall_status("REPEAT", 12, 3, 0)[0], "AMBER")
        self.assertEqual(db.overall_status("REPEAT", 4, 3, 2)[0], "RED")


class SessionQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import random
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from backend_controller import PsyClickController
        import demo_simulation as ds
        cls.ds, cls.ctrl, cls.random = ds, PsyClickController(), random

    def _run(self, spec, seed=3):
        return self.ds.run_session(self.ctrl, db, {"client": "T-Q", "phq": 3, "gad": 2, **spec},
                                   clinician_id=1, rng=self.random.Random(seed))

    def test_too_few_answers_gives_no_behavioural_verdict(self):
        f = self._run({"skip": ["A1", "A2", "B1", "C1", "A3", "B2", "B3", "C2", "A4"]})
        self.assertEqual(f["analysis"]["label"], "Insufficient Data")
        self.assertIn("Only 3 written answer", f["analysis"]["rationale"])
        self.assertEqual(f["quality"]["answers_skipped"], 9)

    def test_long_wait_before_typing_is_marked_as_away(self):
        f = self._run({"read": {"C4": 90.0}})
        c4 = next(s for s in f["visuals"]["question_snapshots"] if s["item_id"] == "C4")
        self.assertTrue(c4["pre_typing_away"])
        a1 = next(s for s in f["visuals"]["question_snapshots"] if s["item_id"] == "A1")
        self.assertFalse(a1["pre_typing_away"])


class RevisitAndBrowserMetricsTests(unittest.TestCase):
    """A prompt visited twice is scored on all its typing; browser timing wins."""

    @classmethod
    def setUpClass(cls):
        import random
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from backend_controller import PsyClickController
        import demo_simulation as ds
        cls.ds, cls.random = ds, random
        cls.ctrl = PsyClickController()
        # calibrate through a full simulated session first (baseline ready)
        ds.run_session(cls.ctrl, db, {"client": "T-R", "phq": 2, "gad": 2}, clinician_id=1, rng=random.Random(2))
        cls.ctrl.set_student_id("T-R2")
        k, m = ds.FakeLogger(), ds.FakeLogger()
        cls.ctrl.key_logger, cls.ctrl.mouse_logger = k, m
        rng = random.Random(4)
        k.next, _ = ds.keystrokes(rng, 150, ds.CALM, 10.0); cls.ctrl.save_kbase()
        m.next, _ = ds.mouse_path(rng, "calm", 50.0, ds.click_targets(rng, 6)); cls.ctrl.save_mbase()
        cls.k, cls.m, cls.rng = k, m, rng
        cls.meta = {"item_id": "B3", "group_id": 2, "level": "B", "prompt": "How did you react?"}

    def test_two_visits_are_scored_together(self):
        k, m = self.k, self.m
        k.next, t = self.ds.keystrokes(self.rng, 60, self.ds.CALM, 100.0)
        self.ctrl.save_question_snapshot(self.meta, "x" * 50,
                                         {"pre_typing_ms": 4200, "pre_typing_away": False,
                                          "hover_words": [{"word": "react?", "dwell_ms": 900, "hover_count": 2}]})
        k.next, _ = self.ds.keystrokes(self.rng, 40, self.ds.CALM, t + 120.0)
        self.ctrl.save_question_snapshot(self.meta, "x" * 80,
                                         {"pre_typing_ms": 1500, "pre_typing_away": False,
                                          "hover_words": [{"word": "react?", "dwell_ms": 300, "hover_count": 1}]})
        snaps = [s for s in self.ctrl._question_snapshots if s["item_id"] == "B3"]
        self.assertEqual(len(snaps), 1)
        b3 = snaps[0]
        self.assertEqual(b3["visits"], 2)
        self.assertGreaterEqual(b3["key_count"], 95)           # both visits' keys
        self.assertEqual(b3["response_len"], 80)                # final answer
        self.assertEqual(b3["pre_typing_pause_ms"], 4200)       # first reading
        self.assertEqual(b3["hover_words"][0]["dwell_ms"], 1200)
        self.assertEqual(b3["reading_source"], "browser")
        self.assertEqual(b3["away_s"], 0)                       # the 2 min between visits is not a pause


if __name__ == "__main__":
    unittest.main()
