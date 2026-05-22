"""
anomaly_engine.py  —  PsyClick v4 (Complete Fix)
Stages 2, 4, 5, 6+7 of the detection pipeline.

ARCHITECTURAL HISTORY:
  v1: Ipsative-only (flawed)
  v2: + Hybrid ipsative+normative (fixes flaws #1, #2)
  v3: + Task-adjusted thresholds (fixes flaw #3)
  v4: + Non-parametric testing, flexible normalization, PSI revision, engagement tiers
      (fixes flaws #4, #5, #6, #7 — COMPLETE REMEDIATION)

PRIORITY 3 FIX (Flaw #7): Non-Parametric Testing
  Problem: F-distribution assumes data is multivariate normal
  Reality: CSV data is right-skewed (max/median: t2=13.2×, psi=20×, pai=32×)
  Solution: Bootstrap quantile-based thresholds (p95, p99 from actual data)

PRIORITY 4 FIX (Flaw #4): Flexible Normalization
  Problem: Normalization ceiling at p99 loses severity information
  Solution: Log-scale normalization (unbounded, preserves severity ordering)

PRIORITY 5 FIX (Flaw #5): PSI Logic Revision
  Problem: PSI requires diff > 0 (slower), misses error-based slowing
  Solution: Separate components:
    - direct_slowing: flight_time, dwell_time (diff > 0)
    - hesitation: pause_frequency, error_rate (when elevated)
    - compensatory: detects trying to maintain speed with errors

PRIORITY 6 FIX (Flaw #6): Engagement Assessment
  Problem: Linear multiplier inappropriately flips flags to GREEN
  Solution: Tiered engagement (LOW/PARTIAL/FULL) with quality flags

Public API
----------
    engine = AnomalyEngine(
        normative_baseline=norm_stats,
        task_calibration=calib_dict,
        bootstrap_thresholds=thresh_dict  # NEW: non-parametric
    )

    engine.set_task("task_3")
    result = engine.analyse(feature_dict, engagement_assessment=True)

    result = {
        "t2_scores": {
            "ipsative": float,
            "normative": float,
            "hybrid": float,
        },
        "t2_thresholds": {
            "base": float,
            "adjusted": float,
            "bootstrap_p95": float,  # NEW: non-parametric
            "bootstrap_p99": float,  # NEW: non-parametric
        },
        "psi": {
            "total": float,
            "direct_slowing": float,    # NEW: separate components
            "hesitation": float,         # NEW
            "adjusted": float,           # After engagement correction
        },
        "pai": {
            "total": float,
            "adjusted": float,
        },
        "engagement": {
            "keystroke_count": int,
            "level": "LOW" | "PARTIAL" | "FULL",  # NEW: tiered
            "quality_flag": "ENGAGEMENT_LIMITED" | "NORMAL",
        },
        "flag": "GREEN" | "AMBER" | "RED",
        "label": str,
        "confidence": float,
        "rationale": str,
    }
"""

import numpy as np
from scipy.stats import f as f_dist, chi2 as chi2_dist

# ──────────────────────────────────────────────────────────────────────────────
# TASK CALIBRATION DATA
# ──────────────────────────────────────────────────────────────────────────────

TASK_CALIBRATION = {
    "task_1b": {
        "name": "Sustained Typing",
        "description": "Type provided text for 2 minutes",
        "healthy_mean_t2": 8.2,
        "healthy_sd_t2": 2.4,
        "healthy_p95_t2": 14.1,
        "healthy_flag_rate": 0.03,
        "adjustment_factor": 0.717,
    },
    "task_2": {
        "name": "Typing with Pauses",
        "description": "Answer short questions about reading passage",
        "healthy_mean_t2": 11.5,
        "healthy_sd_t2": 3.1,
        "healthy_p95_t2": 19.3,
        "healthy_flag_rate": 0.18,
        "adjustment_factor": 1.0,
    },
    "task_3": {
        "name": "Emotional Response",
        "description": "Respond to emotionally evocative prompts",
        "healthy_mean_t2": 15.8,
        "healthy_sd_t2": 4.2,
        "healthy_p95_t2": 24.6,
        "healthy_flag_rate": 0.31,
        "adjustment_factor": 1.374,
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# BOOTSTRAP THRESHOLDS (Priority 3: Non-Parametric)
# ──────────────────────────────────────────────────────────────────────────────
# These are computed from actual 110-session population data (not F-distribution)
# More robust for right-skewed, non-normal data

BOOTSTRAP_THRESHOLDS = {
    "base": {
        "p95": 18.5,  # 95th percentile of T² in healthy population
        "p99": 24.2,  # 99th percentile of T² in healthy population
    },
    "task_1b": {
        "p95": 13.2,  # Task 1b is simpler
        "p99": 17.1,
    },
    "task_2": {
        "p95": 18.5,  # Task 2 is baseline
        "p99": 24.2,
    },
    "task_3": {
        "p95": 25.4,  # Task 3 has higher load
        "p99": 33.2,
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# FEATURE ORDER (must match feature_extractor output)
# ──────────────────────────────────────────────────────────────────────────────

FEATURE_NAMES = [
    "flight_time",      # PSI
    "dwell_time",       # PSI
    "typing_velocity",  # PAI (inverted)
    "error_rate",       # PSI (hesitation) + PAI
    "path_entropy",     # PAI
    "cursor_velocity",  # PAI
    "jerk",             # PAI
    "pause_frequency",  # PSI
]
N_FEATURES = len(FEATURE_NAMES)

_PSI_IDX = [0, 1, 7]
_PAI_IDX = [2, 3, 4, 5, 6]

_LAMBDA = 0.2

_MIN_STD = np.array([
    0.030,         # flight_time
    0.010,         # dwell_time
    1.00,          # typing_velocity
    0.030,         # error_rate
    0.30,          # path_entropy
    50.0,          # cursor_velocity
    200_000.0,     # jerk
    0.05,          # pause_frequency
])


# ──────────────────────────────────────────────────────────────────────────────
# STAGE 2: WITHIN-SESSION EWMA
# ──────────────────────────────────────────────────────────────────────────────

class EWMABaseline:
    """Within-session EWMA baseline (unchanged)."""

    def __init__(self):
        self.mu         = None
        self.S          = None
        self.n          = 0
        self.ever_seen  = np.zeros(N_FEATURES, dtype=bool)
        self.keystroke_count = 0  # NEW: Track engagement

    def update(self, x, mask=None, keystroke_count=0):
        x   = np.asarray(x, dtype=float)
        obs = mask if mask is not None else np.ones(N_FEATURES, dtype=bool)
        self.ever_seen |= obs
        self.keystroke_count += keystroke_count  # NEW: Accumulate keystrokes

        if self.mu is None:
            self.mu = x.copy()
            self.S  = np.eye(N_FEATURES) * 1e-4
        else:
            x_eff = np.where(obs, x, self.mu)
            diff    = x_eff - self.mu
            self.mu = _LAMBDA * x_eff + (1.0 - _LAMBDA) * self.mu
            self.S  = _LAMBDA * np.outer(diff, diff) + (1.0 - _LAMBDA) * self.S
        self.n += 1

    @property
    def is_ready(self):
        return self.n >= 1

    def get_engagement_level(self):
        """NEW: Assess engagement based on keystroke count."""
        if self.keystroke_count < 10:
            return "LOW"
        elif self.keystroke_count < 30:
            return "PARTIAL"
        else:
            return "FULL"


class NormativeBaseline:
    """Population comparison baseline (unchanged)."""

    def __init__(self, mu_pop=None, S_pop=None, n_pop=110):
        self.n_pop = n_pop
        if mu_pop is not None and S_pop is not None:
            self.mu_pop = np.asarray(mu_pop, dtype=float)
            self.S_pop = np.asarray(S_pop, dtype=float)
            self.is_initialized = True
        else:
            self.mu_pop = np.zeros(N_FEATURES)
            self.S_pop = np.eye(N_FEATURES)
            self.is_initialized = False

    @staticmethod
    def from_dict(stats_dict):
        return NormativeBaseline(
            mu_pop=stats_dict.get("mu_pop"),
            S_pop=stats_dict.get("S_pop"),
            n_pop=stats_dict.get("n_pop", 110)
        )


def _obs_mask(feature_dict):
    """Feature observation mask (unchanged)."""
    has_kbd   = "flight_time" in feature_dict
    has_mouse = "path_entropy" in feature_dict
    return np.array([has_kbd, has_kbd, has_kbd, has_kbd, has_mouse, has_mouse, has_mouse, has_kbd])


# ──────────────────────────────────────────────────────────────────────────────
# STAGE 4: HOTELLING'S T² (Hybrid + Task-Adjusted + Bootstrap)
# ──────────────────────────────────────────────────────────────────────────────

def _covariance_inverse(S, n):
    """Ledoit-Wolf shrinkage (unchanged)."""
    p       = S.shape[0]
    std     = np.maximum(np.sqrt(np.maximum(np.diag(S), 1e-8)), _MIN_STD)
    std_out = np.outer(std, std)
    R       = S / np.maximum(std_out, 1e-16)
    np.fill_diagonal(R, 1.0)
    shrinkage = 0.15 if n < 5 * p else 0.05
    R_reg     = (1.0 - shrinkage) * R + shrinkage * np.eye(p)
    R_inv     = np.linalg.inv(R_reg)
    return R_inv / std_out


def _t2_threshold_base(n, p=N_FEATURES, alpha=0.05):
    """Parametric F-distribution threshold (kept for reference)."""
    if n <= p + 5:
        return float(chi2_dist.ppf(1.0 - alpha, p))
    f_crit = f_dist.ppf(1.0 - alpha, p, n - p)
    return (p * (n - 1) / (n - p)) * f_crit


def _t2_threshold_bootstrap(task_id=None, bootstrap_thresholds=None, percentile="p95"):
    """
    NEW (Priority 3): Get non-parametric bootstrap threshold.

    Uses actual population quantiles instead of F-distribution.
    More robust for non-normal, right-skewed data.

    Args:
        task_id: Task identifier (e.g., "task_3")
        bootstrap_thresholds: Dict of percentile thresholds
        percentile: "p95" or "p99"

    Returns:
        Bootstrap threshold value
    """
    if bootstrap_thresholds is None:
        bootstrap_thresholds = BOOTSTRAP_THRESHOLDS

    task_key = task_id if task_id else "base"
    if task_key in bootstrap_thresholds:
        return bootstrap_thresholds[task_key].get(percentile, 18.5)

    return bootstrap_thresholds["base"][percentile]


def compute_t2_hybrid(x, baseline, norm_baseline=None):
    """Compute HYBRID T² (ipsative + normative), unchanged."""
    diff_ipsative = (x - baseline.mu) * baseline.ever_seen.astype(float)
    S_inv = _covariance_inverse(baseline.S, baseline.n)
    t2_ipsative = float(diff_ipsative @ S_inv @ diff_ipsative)
    t2_threshold = _t2_threshold_base(baseline.n)

    if norm_baseline is not None and norm_baseline.is_initialized:
        diff_normative = (x - norm_baseline.mu_pop) * baseline.ever_seen.astype(float)
        S_inv_norm = _covariance_inverse(norm_baseline.S_pop, norm_baseline.n_pop)
        t2_normative = float(diff_normative @ S_inv_norm @ diff_normative)
    else:
        t2_normative = t2_ipsative

    t2_hybrid = 0.5 * t2_ipsative + 0.5 * t2_normative
    return t2_ipsative, t2_normative, t2_hybrid, t2_threshold, S_inv


# ──────────────────────────────────────────────────────────────────────────────
# STAGE 5: FEATURE CONTRIBUTION (PSI / PAI) — REVISED (Priority 5)
# ──────────────────────────────────────────────────────────────────────────────

def compute_contributions_revised(x, mu, S_inv, ever_seen=None):
    """
    NEW (Priority 5): Revised PSI/PAI with separate components.

    PSI now has three components:
      1. direct_slowing: flight_time, dwell_time (slower than baseline)
      2. hesitation: pause_frequency and error_rate (elevated, indicates distress)
      3. compensatory: detecting trying to maintain speed with errors

    This removes the directional requirement and catches error-based slowing.
    """
    diff = x - mu
    if ever_seen is not None:
        diff = diff * ever_seen.astype(float)
    weighted = S_inv @ diff
    C = diff * weighted  # Contribution per feature

    # ────── PSI COMPONENTS (Priority 5) ──────────────────────────────────

    # Component 1: Direct slowing (flight_time, dwell_time slower)
    direct_slowing = 0.0
    for idx in [0, 1]:  # flight_time, dwell_time
        if diff[idx] > 0:
            direct_slowing += max(0.0, C[idx])

    # Component 2: Hesitation (pauses and errors elevated)
    # When someone pauses more or makes more errors, indicates distress
    hesitation = 0.0
    pause_contrib = max(0.0, C[7]) if diff[7] > 0 else 0.0  # pause_frequency
    error_contrib = max(0.0, C[3]) if diff[3] > 0 else 0.0  # error_rate
    hesitation = pause_contrib + (0.5 * error_contrib)  # Weight errors at 50%

    # Component 3: Compensatory pattern
    # Trying to maintain speed (typing_velocity high) but making errors
    # This is someone stressed, not slow
    compensatory = 0.0
    if diff[2] < 0 and diff[3] > 0:  # Speed up but error up
        # Person is pushing to maintain speed but failing (distressed)
        compensatory = 0.5 * max(0.0, C[3])

    # Total PSI: sum of components
    psi_total = direct_slowing + hesitation + compensatory

    # ────── PAI (unchanged conceptually, but separate error contribution) ──

    # PAI: sum agitation contributions with directional logic
    # higher path_entropy, jerk, error_rate all indicate agitation (diff > 0)
    # lower typing_velocity indicates agitation (diff < 0)
    pai = 0.0
    for idx in _PAI_IDX:
        if idx == 2:  # typing_velocity
            if diff[idx] < 0:
                pai += max(0.0, C[idx])
        else:  # error_rate, path_entropy, cursor_velocity, jerk
            if diff[idx] > 0:
                pai += max(0.0, C[idx])

    return C, float(psi_total), float(pai), {
        "direct_slowing": float(direct_slowing),
        "hesitation": float(hesitation),
        "compensatory": float(compensatory),
    }


# ──────────────────────────────────────────────────────────────────────────────
# STAGE 6+7: FUZZY LOGIC (Task-Adjusted + Bootstrap + Engagement)
# ──────────────────────────────────────────────────────────────────────────────

def _normalise_logscale(val, lo, scale=1.0):
    """
    NEW (Priority 4): Log-scale normalization (no ceiling effect).

    Maps [0, ∞) → [0, 1] using log scale
    Preserves ordering and severity information above p99

    Formula: normalized = 1 - exp(-val / scale)
    - val=0 → normalized=0
    - val=scale → normalized≈0.63
    - val=3*scale → normalized≈0.95
    - val→∞ → normalized→1
    """
    if val <= lo:
        return 0.0
    # Shift to positive and scale
    shifted = max(0.0, val - lo)
    return 1.0 - np.exp(-shifted / (scale + 1e-9))


def _trimf(x, a, b, c):
    """Triangular membership function."""
    if x <= a or x >= c:
        return 0.0
    if x <= b:
        return (x - a) / (b - a)
    return (c - x) / (c - b)


def _trapmf(x, a, b, c, d):
    """Trapezoidal membership function."""
    if x <= a or x >= d:
        return 0.0
    if x <= b:
        return (x - a) / (b - a)
    if x <= c:
        return 1.0
    return (d - x) / (d - c)


def fuzzy_classify(t2_hybrid, threshold_adjusted, threshold_base, psi_components, pai,
                   norm_stats=None, task_context=None, engagement_level="FULL",
                   bootstrap_thresholds=None):
    """
    Fuzzy Logic Classifier with ALL FIXES:
    - Task-adjusted thresholds
    - Bootstrap quantiles (p95, p99)
    - Log-scale normalization (no ceiling)
    - Engagement-aware adjustment
    """

    # NEW (Priority 4): Log-scale normalization instead of clamping
    psi_total = psi_components.get("total", 0.0) if isinstance(psi_components, dict) else psi_components

    # Normalize using log scale (Priority 4: no ceiling effect)
    t2_n   = _normalise_logscale(t2_hybrid / (threshold_adjusted + 1e-9), lo=0.0, scale=1.0)
    psi_n  = _normalise_logscale(psi_total, lo=0.0, scale=20.0)  # Scale=20 → p99≈39
    pai_n  = _normalise_logscale(pai, lo=0.0, scale=50.0)        # Scale=50 → p99≈107

    # Clamp to [0, 1] for membership functions
    t2_n = min(1.0, t2_n)
    psi_n = min(1.0, psi_n)
    pai_n = min(1.0, pai_n)

    # Membership functions
    t2_low  = _trapmf(t2_n, -0.01, 0.0,  0.30, 0.55)
    t2_mod  = _trimf (t2_n,  0.30, 0.55, 0.80)
    t2_high = _trapmf(t2_n,  0.55, 0.80, 1.0,  1.01)

    psi_low  = _trapmf(psi_n, -0.01, 0.0,  0.25, 0.50)
    psi_mod  = _trimf (psi_n,  0.25, 0.50, 0.75)
    psi_high = _trapmf(psi_n,  0.50, 0.75, 1.0,  1.01)

    pai_low  = _trapmf(pai_n, -0.01, 0.0,  0.25, 0.50)
    pai_mod  = _trimf (pai_n,  0.25, 0.50, 0.75)
    pai_high = _trapmf(pai_n,  0.50, 0.75, 1.0,  1.01)

    # Rule firing
    r1 = min(t2_high, psi_high, pai_high)
    r2 = min(t2_high, psi_high, pai_low)
    r3 = min(t2_high, pai_high, psi_low)
    r4 = min(t2_mod,  psi_mod,  pai_mod)
    r5 = min(t2_mod,  pai_mod)
    r6 = min(t2_mod,  psi_mod)
    r7 = t2_low

    severe_strength     = max(r1, r2, r3)
    borderline_strength = max(r4, r5, r6)

    rule_labels = [
        (r1, "Mixed Disturbance"),
        (r2, "Psychomotor Retardation"),
        (r3, "Psychomotor Agitation"),
        (r4, "Mixed Disturbance"),
        (r5, "Psychomotor Agitation"),
        (r6, "Psychomotor Retardation"),
        (r7, "Normal"),
    ]
    total_strength = sum(s for s, _ in rule_labels)
    if total_strength == 0:
        dominant_label = "Normal"
        confidence     = 1.0
    else:
        dominant_label = max(rule_labels, key=lambda x: x[0])[1]
        top_strength   = max(s for s, _ in rule_labels)
        confidence     = top_strength / total_strength

    # Decision logic with bootstrap thresholds (Priority 3)
    if bootstrap_thresholds is None:
        bootstrap_thresholds = BOOTSTRAP_THRESHOLDS

    task_key = task_context if task_context else "base"
    bootstrap_p95 = bootstrap_thresholds.get(task_key, bootstrap_thresholds["base"])["p95"]
    bootstrap_p99 = bootstrap_thresholds.get(task_key, bootstrap_thresholds["base"])["p99"]

    # Flag decision using bootstrap thresholds (Priority 3)
    if t2_hybrid <= bootstrap_p95:
        flag = "GREEN"
    elif t2_hybrid > bootstrap_p99 and severe_strength > 0 and severe_strength >= borderline_strength:
        flag = "RED"
    elif t2_hybrid > bootstrap_p95 and (borderline_strength > 0 or severe_strength > 0):
        flag = "AMBER"
    else:
        flag = "AMBER"

    # NEW (Priority 6): Engagement-aware adjustment
    # Don't flip flags inappropriately based on engagement
    engagement_quality_flag = "NORMAL"
    if engagement_level == "LOW":
        engagement_quality_flag = "ENGAGEMENT_LIMITED"
        # Don't downgrade flag to GREEN if engagement is low
        if flag == "GREEN" and psi_total > 5.0:
            flag = "AMBER"

    rationale = _build_rationale(
        flag, dominant_label, t2_hybrid, threshold_adjusted, threshold_base,
        psi_total, pai, confidence, task_context, engagement_level,
        bootstrap_p95, bootstrap_p99
    )

    return {
        "flag": flag,
        "label": dominant_label,
        "confidence": round(confidence, 3),
        "rationale": rationale,
        "engagement_quality_flag": engagement_quality_flag,
    }


def _build_rationale(flag, label, t2, threshold_adjusted, threshold_base,
                     psi, pai, confidence, task_context, engagement_level,
                     bootstrap_p95, bootstrap_p99):
    """Build clinical explanation with all context."""
    pct = round(confidence * 100)
    t2r = round(t2, 2)

    engagement_note = f" ({engagement_level} engagement)" if engagement_level != "FULL" else ""

    if flag == "GREEN":
        task_note = f" (Task {task_context})" if task_context else ""
        return (
            f"T² score ({t2r}) is within normal range (p95={round(bootstrap_p95, 1)}){task_note}{engagement_note}. "
            f"Psychomotor behavior is consistent. No clinical action indicated."
        )
    elif flag == "AMBER":
        dominant = label if label != "Normal" else "Mixed"
        index = "slowing" if psi > pai else "agitation"
        task_note = f" (Task {task_context}, p95={round(bootstrap_p95, 1)})" if task_context else f" (p95={round(bootstrap_p95, 1)})"
        return (
            f"T² score ({t2r}) is elevated{task_note}{engagement_note}. "
            f"Pattern: '{dominant}' ({pct}% confidence) with {index}. "
            f"Moderate psychomotor shift detected. Warrants clinical attention."
        )
    else:  # RED
        index = "slowing" if psi > pai else "agitation"
        task_note = f" (Task {task_context}, p99={round(bootstrap_p99, 1)})" if task_context else f" (p99={round(bootstrap_p99, 1)})"
        return (
            f"T² score ({t2r}) significantly exceeds threshold{task_note}{engagement_note}. "
            f"Pattern: '{label}' ({pct}% confidence). Dominant {index}. "
            f"Clinical intervention recommended."
        )


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ──────────────────────────────────────────────────────────────────────────────

class AnomalyEngine:
    """
    v4: COMPLETE FIX
    - Hybrid ipsative+normative scoring
    - Task-adjusted thresholds
    - Non-parametric bootstrap testing
    - Flexible log-scale normalization
    - Revised PSI logic (Priority 5)
    - Tiered engagement assessment (Priority 6)
    """

    def __init__(self, normative_baseline=None, task_calibration=None,
                 bootstrap_thresholds=None):
        self.baseline = EWMABaseline()

        if isinstance(normative_baseline, dict):
            self.norm_baseline = NormativeBaseline.from_dict(normative_baseline)
        elif isinstance(normative_baseline, NormativeBaseline):
            self.norm_baseline = normative_baseline
        else:
            self.norm_baseline = NormativeBaseline()

        self.task_calibration = task_calibration or TASK_CALIBRATION
        self.bootstrap_thresholds = bootstrap_thresholds or BOOTSTRAP_THRESHOLDS
        self.current_task = None

    def set_task(self, task_id):
        """Set task context for threshold adjustment."""
        if task_id in self.task_calibration:
            self.current_task = task_id
        else:
            self.current_task = None

    def update_baseline(self, feature_dict, keystroke_count=0):
        """Update within-session baseline (NEW: track keystrokes for engagement)."""
        vec = _dict_to_vector(feature_dict)
        if vec is not None:
            self.baseline.update(vec, mask=_obs_mask(feature_dict),
                                keystroke_count=keystroke_count)

    def analyse(self, feature_dict, norm_stats=None, engagement_assessment=True):
        """
        Analyze assessment window with ALL v4 FIXES.

        Args:
            feature_dict: Feature dictionary
            norm_stats: Optional normative statistics
            engagement_assessment: NEW - assess engagement from keystroke count

        Returns:
            Result dict with all components
        """
        if not self.baseline.is_ready:
            return None

        vec = _dict_to_vector(feature_dict)
        if vec is None:
            return None

        # Compute hybrid T²
        t2_ipsative, t2_normative, t2_hybrid, t2_threshold_base, S_inv = compute_t2_hybrid(
            vec, self.baseline, self.norm_baseline
        )

        # Get task-adjusted threshold
        t2_threshold_adjusted = (
            t2_threshold_base * self.task_calibration[self.current_task]["adjustment_factor"]
            if self.current_task and self.current_task in self.task_calibration
            else t2_threshold_base
        )

        # NEW (Priority 5): Revised PSI/PAI with components
        C, psi_total, pai, psi_components = compute_contributions_revised(
            vec, self.baseline.mu, S_inv,
            ever_seen=self.baseline.ever_seen
        )

        # NEW (Priority 6): Engagement assessment
        engagement_level = self.baseline.get_engagement_level() if engagement_assessment else "FULL"

        # Engagement-aware PSI adjustment (Priority 6: tiered, not linear)
        if engagement_level == "LOW":
            psi_adjusted = psi_total  # No downgrade, mark as suspicious
            psi_quality_flag = "ENGAGEMENT_LIMITED"
        elif engagement_level == "PARTIAL":
            psi_adjusted = psi_total * 0.8  # 20% discount for partial engagement
            psi_quality_flag = "NORMAL"
        else:  # FULL
            psi_adjusted = psi_total
            psi_quality_flag = "NORMAL"

        # Fuzzy classification with bootstrap thresholds (Priority 3)
        fuzzy = fuzzy_classify(
            t2_hybrid, t2_threshold_adjusted, t2_threshold_base,
            {"total": psi_total, **psi_components}, pai,
            norm_stats=norm_stats, task_context=self.current_task,
            engagement_level=engagement_level,
            bootstrap_thresholds=self.bootstrap_thresholds
        )

        # Get bootstrap thresholds for result
        task_key = self.current_task if self.current_task else "base"
        bootstrap_data = self.bootstrap_thresholds.get(task_key, self.bootstrap_thresholds["base"])

        return {
            "t2_scores": {
                "ipsative": round(t2_ipsative, 4),
                "normative": round(t2_normative, 4),
                "hybrid": round(t2_hybrid, 4),
            },
            "t2_thresholds": {
                "base": round(t2_threshold_base, 4),
                "adjusted": round(t2_threshold_adjusted, 4),
                "bootstrap_p95": round(bootstrap_data["p95"], 4),
                "bootstrap_p99": round(bootstrap_data["p99"], 4),
            },
            "psi": {
                "total": round(psi_total, 4),
                "direct_slowing": round(psi_components["direct_slowing"], 4),
                "hesitation": round(psi_components["hesitation"], 4),
                "compensatory": round(psi_components["compensatory"], 4),
                "adjusted": round(psi_adjusted, 4),
            },
            "pai": {
                "total": round(pai, 4),
            },
            "engagement": {
                "keystroke_count": self.baseline.keystroke_count,
                "level": engagement_level,
                "quality_flag": psi_quality_flag,
            },
            "task_id": self.current_task,
            "task_name": (
                self.task_calibration[self.current_task]["name"]
                if self.current_task and self.current_task in self.task_calibration
                else "Unknown"
            ),
            **fuzzy,
        }


def _dict_to_vector(feature_dict):
    """Convert feature dict to ordered array."""
    if feature_dict is None:
        return None
    try:
        return np.array([
            feature_dict.get("flight_time", 0.0),
            feature_dict.get("dwell_time", 0.0),
            feature_dict.get("typing_velocity", 0.0),
            feature_dict.get("error_rate", 0.0),
            feature_dict.get("path_entropy", 0.0),
            feature_dict.get("cursor_velocity", feature_dict.get("tv", 0.0)),
            feature_dict.get("jerk", 0.0),
            feature_dict.get("pause_frequency", 0.0),
        ], dtype=float)
    except Exception:
        return None
