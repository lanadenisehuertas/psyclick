"""
anomaly_engine.py  —  PsyClick
Stages 2, 4, 5, 6+7 of the detection pipeline.

Stage 2  — Within-Session EWMA baseline builder
Stage 4  — Hotelling's T² multivariate anomaly detector
Stage 5  — Feature Contribution Analysis  →  PSI / PAI
Stage 6+7 — Fuzzy Logic Classifier + Heuristic Decision Tree
            (combined so the flag is produced by one call, not two)

Public API
----------
    engine = AnomalyEngine()
    engine.update_baseline(feature_vector)   # call during calibration
    result = engine.analyse(feature_vector)  # call during assessment
    result = {
        't2_score':    float,
        't2_threshold':float,
        'psi':         float,
        'pai':         float,
        'flag':        'GREEN' | 'AMBER' | 'RED',
        'label':       str,          # e.g. "Psychomotor Retardation"
        'confidence':  float,        # 0.0 – 1.0
        'rationale':   str,          # plain-language clinical note
    }
"""

import numpy as np
from scipy.stats import f as f_dist, chi2 as chi2_dist

# ── FEATURE ORDER (must match feature_extractor output) ───────────────────────
FEATURE_NAMES = [
    "flight_time",      # PSI
    "dwell_time",       # PSI
    "typing_velocity",  # PAI (inverted — low velocity → agitation)
    "error_rate",       # PAI
    "path_entropy",     # PAI
    "cursor_velocity",  # PAI
    "jerk",             # PAI
    "pause_frequency",  # PSI
]
N_FEATURES = len(FEATURE_NAMES)   # 8

# Which feature indices belong to PSI and PAI
_PSI_IDX = [0, 1, 7]              # flight_time, dwell_time, pause_frequency
_PAI_IDX = [2, 3, 4, 5, 6]       # typing_velocity, error_rate, path_entropy,
                                  # cursor_velocity, jerk

# Smoothing parameter for EWMA (lambda)
_LAMBDA = 0.2
# Physically-meaningful minimum standard deviations per feature.
# Prevents astronomically large z-scores when S[i,i] is near-zero
# (e.g. keyboard features after only mouse-only calibration windows,
# or when behaviour is so consistent that the EWMA covariance never
# rises above its seed value).
_MIN_STD = np.array([
    0.030,         # 0  flight_time      (30 ms — typical inter-key jitter)
    0.010,         # 1  dwell_time       (10 ms — key-hold jitter)
    1.00,          # 2  typing_velocity  (1 char/s — 1-σ within-session spread)
    0.030,         # 3  error_rate       (3 % — 1-σ backspace variation)
    0.30,          # 4  path_entropy     (0.3 bit — typical entropy fluctuation)
    50.0,          # 5  cursor_velocity  (50 px/s — 1-σ speed variation)
    200_000.0,     # 6  jerk             (200 000 px/s³ — 1-σ at 60Hz sampling)
    0.05,          # 7  pause_frequency  (0.05 pauses/s)
])


# ── STAGE 2: WITHIN-SESSION EWMA ─────────────────────────────────────────────
class EWMABaseline:
    """
    Builds an adaptive personal baseline during the calibration phase.

    mu_ewma(t)  = lambda * x(t) + (1 - lambda) * mu_ewma(t-1)
    S_ewma(t)   = lambda * outer(diff, diff) + (1 - lambda) * S_ewma(t-1)
    """

    def __init__(self):
        self.mu         = None                                 # mean vector (p,)
        self.S          = None                                 # covariance matrix (p, p)
        self.n          = 0                                    # number of windows seen
        self.ever_seen  = np.zeros(N_FEATURES, dtype=bool)    # which features had real data

    def update(self, x, mask=None):
        """
        Feed one feature vector (length 8) from the calibration phase.

        mask : boolean array of length p, or None (= all True).
               Unmasked dimensions are held at the current mean so they
               contribute diff=0 — preventing spurious cross-covariances
               between keyboard-only and mouse-only calibration windows.
        """
        x   = np.asarray(x, dtype=float)
        obs = mask if mask is not None else np.ones(N_FEATURES, dtype=bool)
        self.ever_seen |= obs  # track calibrated features
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
        # 1 window is enough to seed the baseline.
        # EWMA adapts as more windows arrive — we never block analysis
        # just because the user only completed one calibration pass.
        return self.n >= 1

def _obs_mask(feature_dict):
    """
    Returns a boolean array (length p) indicating which features are genuinely
    observed in this calibration window.  Unobserved slots are held at the
    current EWMA mean during the update so they contribute diff=0 and do not
    introduce spurious cross-modal covariances.

    keyboard dict  (extract_features)       → has "flight_time"
    mouse dict     (extract_mouse_features) → has "path_entropy"
    combined dict  (assessment window)      → has both → all True
    """
    has_kbd   = "flight_time"   in feature_dict
    has_mouse = "path_entropy"  in feature_dict
    return np.array([
        has_kbd,    # 0  flight_time
        has_kbd,    # 1  dwell_time
        has_kbd,    # 2  typing_velocity
        has_kbd,    # 3  error_rate
        has_mouse,  # 4  path_entropy
        has_mouse,  # 5  cursor_velocity
        has_mouse,  # 6  jerk
        has_kbd or has_mouse,  # 7  pause_frequency (computed by both modalities)
    ])



# ── STAGE 4: HOTELLING'S T² ───────────────────────────────────────────────────
def _covariance_inverse(S, n):
    """
    Return the precision matrix (S^-1) in original feature space.

    Operates in correlation space so condition number is bounded by
    1/shrinkage (~6.7) regardless of feature scale differences.
    (jerk ~10^5 px/s³ vs flight_time ~0.1 s creates a 6-order magnitude
    gap; shrinking toward diagonal of raw S still gives κ ~10^9, making
    S_inv[jerk] astronomical and T² explode to ~10^16.)

    Ledoit-Wolf ridge on R:   R_reg = (1-α)*R + α*I
    Precision in raw space:   S_inv = D⁻¹ @ R_inv @ D⁻¹  where D = diag(std)
    """
    p       = S.shape[0]
    std     = np.maximum(np.sqrt(np.maximum(np.diag(S), 1e-8)), _MIN_STD)
    std_out = np.outer(std, std)
    R       = S / np.maximum(std_out, 1e-16)
    np.fill_diagonal(R, 1.0)                        # floating-point safety

    shrinkage = 0.15 if n < 5 * p else 0.05        # relax slightly for large n
    R_reg     = (1.0 - shrinkage) * R + shrinkage * np.eye(p)
    R_inv     = np.linalg.inv(R_reg)

    return R_inv / std_out                          # S⁻¹ = D⁻¹ R⁻¹ D⁻¹

def _t2_threshold(n, p=N_FEATURES, alpha=0.05):
    """
    F-distribution threshold for Hotelling's T² (Tracy et al., 1992):
        T²_threshold = [p(n-1) / (n-p)] * F(alpha; p, n-p)

    When n ≤ p the F-distribution is undefined (df2 = n-p ≤ 0).
    In that regime we use the chi-squared critical value χ²(1-α; p), which is
    the large-sample limiting distribution of T² under multivariate normality
    and remains valid when Ledoit-Wolf shrinkage guarantees S invertibility.
    """
    if n <= p:
        return float(chi2_dist.ppf(1.0 - alpha, p))   # ≈ 15.51 for p=8, α=0.05
    f_crit = f_dist.ppf(1.0 - alpha, p, n - p)
    return (p * (n - 1) / (n - p)) * f_crit


def compute_t2(x, baseline):
    """
    Compute T² score and threshold for a single assessment window.
    Features never seen during calibration (baseline.ever_seen[i] == False) are
    zeroed out so they do not contribute to T².  Without this, keyboard-only
    calibration would leave mouse feature means at 0, and even a normal jerk
    value (e.g. 800 000 px/s³) would produce a catastrophic z-score vs mu=0.

    Returns (t2_score, t2_threshold, precision_matrix)
    """
    diff   = (x - baseline.mu) * baseline.ever_seen.astype(float)
    S_inv  = _covariance_inverse(baseline.S, baseline.n)
    t2     = float(baseline.n * diff @ S_inv @ diff)
    thresh = _t2_threshold(baseline.n)
    return t2, thresh, S_inv


# ── STAGE 5: FEATURE CONTRIBUTION (PSI / PAI) ────────────────────────────────
def compute_contributions(x, mu, S_inv, ever_seen=None):
    diff = x - mu
    if ever_seen is not None:
        diff = diff * ever_seen.astype(float)   # ignore uncalibrated features
    weighted = S_inv @ diff
    C   = diff * weighted  # Magnitude of contribution
    
    # PSI: sum contributions from slowing features (diff > 0 = slower than baseline).
    # Use max(0, C[idx]) because cross-covariance in S⁻¹ can make C[idx] negative
    # even when diff[idx] > 0 — without the clamp, genuine slowing is silently zeroed.

    psi = 0.0
    for idx in _PSI_IDX:
        if diff[idx] > 0:
            psi += max(0.0, C[idx])
            
    
    # PAI: sum all agitation contributions (directional logic not needed —
    # higher path_entropy, jerk, error_rate all indicate agitation regardless).
    pai = 0.0
    for idx in _PAI_IDX:
        pai += C[idx]
        
    return C, float(psi), float(pai)


# ── STAGE 6+7: FUZZY LOGIC + HEURISTIC DECISION TREE ────────────────────────
#
# The Fuzzy Logic Classifier converts T², PSI, PAI into graded membership
# degrees across Normal / Borderline / Concerning / Severe.
# The Heuristic Decision Tree then maps those memberships to the final flag.
#
# Rule table:
#   R1: T²=High  AND PSI=High AND PAI=Low  → Retardation,  High Concern
#   R2: T²=Mod   AND PAI=Mod              → Agitation,    Borderline
#   R3: T²=Low                            → Normal
#   R4: PSI=High AND PAI=High             → Mixed,        Amber
#
# Membership functions are triangular (trimf) over normalised [0,1] inputs.

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


def _normalise(val, lo, hi):
    """Clamp and scale val to [0, 1] between lo and hi."""
    return max(0.0, min(1.0, (val - lo) / (hi - lo + 1e-9)))


def fuzzy_classify(t2, threshold, psi, pai):
    """
    Fuzzy Logic Classifier + Heuristic Decision Tree (Stage 6+7).

    Six clinical rules (priority-ordered, Mamdani min-conjunction):
      R1  T²=H  PSI=H  PAI=H  → Mixed Disturbance,        Severe    → RED
      R2  T²=H  PSI=H  PAI=L  → Psychomotor Retardation,  Severe    → RED
      R3  T²=H  PAI=H  PSI=L  → Psychomotor Agitation,    Severe    → RED
      R4  T²=M  PSI=M  PAI=M  → Mixed Disturbance,        Borderline→ AMBER
      R5  T²=M  PAI=M         → Psychomotor Agitation,    Borderline→ AMBER
      R6  T²=M  PSI=M         → Psychomotor Retardation,  Borderline→ AMBER
      R7  T²=L               → Normal Behavior                      → GREEN
    """

    t2_ratio = t2 / (threshold + 1e-9)
    t2_n     = _normalise(t2_ratio,       0.0, 2.0)
    psi_n    = _normalise(max(psi, 0.0),  0.0, 5.0)
    pai_n    = _normalise(max(pai, 0.0),  0.0, 5.0)


    # ── Membership degrees ────────────────────────────────────────────────────
    # T² memberships
    # Note: bounds extend 0.01 past [0,1] so that x clamped to exactly 0.0
    # or 1.0 by _normalise still lands inside the plateau, not on the dead zone.
    t2_low  = _trapmf(t2_n, -0.01, 0.0,  0.30, 0.55)
    t2_mod  = _trimf (t2_n,  0.30, 0.55, 0.80)
    t2_high = _trapmf(t2_n,  0.55, 0.80, 1.0,  1.01)

    # PSI memberships
    psi_low  = _trapmf(psi_n, -0.01, 0.0,  0.25, 0.50)
    psi_mod  = _trimf (psi_n,  0.25, 0.50, 0.75)
    psi_high = _trapmf(psi_n,  0.50, 0.75, 1.0,  1.01)


    # PAI memberships
    pai_low  = _trapmf(pai_n, -0.01, 0.0,  0.25, 0.50)
    pai_mod  = _trimf (pai_n,  0.25, 0.50, 0.75)
    pai_high = _trapmf(pai_n,  0.50, 0.75, 1.0,  1.01)

    # ── Rule firing strengths (min-conjunction) ───────────────────────────────
    r_normal      = t2_low                                          # R3
    r_retardation = min(t2_high, psi_high, pai_low)                 # R1
    r_agitation   = min(t2_mod,  pai_mod)                           # R2
    r_mixed       = min(psi_high, pai_high)                         # R4

    # Rule firing strengths
    r1 = min(t2_high, psi_high, pai_high)   # Mixed,        Severe
    r2 = min(t2_high, psi_high, pai_low)    # Retardation,  Severe
    r3 = min(t2_high, pai_high, psi_low)    # Agitation,    Severe
    r4 = min(t2_mod,  psi_mod,  pai_mod)    # Mixed,        Borderline
    r5 = min(t2_mod,  pai_mod)              # Agitation,    Borderline
    r6 = min(t2_mod,  psi_mod)              # Retardation,  Borderline
    r7 = t2_low                             # Normal

    severe_strength     = max(r1, r2, r3)
    borderline_strength = max(r4, r5, r6)

    # Dominant label: highest-firing rule wins
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

    # Flag from severity tier of dominant rule set
    if severe_strength > 0 and severe_strength >= borderline_strength:
        flag = "RED"
    elif borderline_strength > 0:
        flag = "AMBER"
    else:
        flag = "GREEN"

    # Override: T² below threshold always GREEN regardless of PSI/PAI
    if t2_ratio <= 1.0:
        flag = "GREEN"
    rationale = _build_rationale(flag, dominant_label, t2, threshold, psi, pai, confidence)

    return {
        "flag":       flag,
        "label":      dominant_label,
        "confidence": round(confidence, 3),
        "rationale":  rationale,
    }


def _build_rationale(flag, label, t2, threshold, psi, pai, confidence):
    pct = round(confidence * 100)
    t2r = round(t2, 2)
    thr = round(threshold, 2)

    if flag == "GREEN":
        return (
            f"T\u00b2 score ({t2r}) is within the session baseline threshold ({thr}). "
            f"Psychomotor behavior is statistically consistent with the calibration phase. "
            f"No clinical action indicated."
        )
    elif flag == "AMBER":
        dominant = label if label != "Normal" else "Mixed"
        index    = "PSI" if "Retardation" in label else "PAI" if "Agitation" in label else "PSI & PAI"
        return (
            f"T\u00b2 score ({t2r}) exceeds the session threshold ({thr}). "
            f"Pattern classified as \u2018{dominant}\u2019 ({pct}% confidence). "
            f"Elevated {index} index suggests moderate psychomotor shift. "
            f"Warrants clinical attention at next appointment."
        )
    else:  # RED
        index = "PSI (slowing)" if psi > pai else "PAI (agitation)"
        return (
            f"T\u00b2 score ({t2r}) significantly exceeds the session threshold ({thr}). "
            f"Pattern classified as \u2018{label}\u2019 ({pct}% confidence). "
            f"Dominant deviation in {index}. "
            f"Clinical intervention recommended."
        )


# ── PUBLIC INTERFACE ──────────────────────────────────────────────────────────
class AnomalyEngine:
    """
    Stateful engine for one session.

    Usage:
        engine = AnomalyEngine()
        # --- calibration phase ---
        engine.update_baseline(vec)   # call for each calibration window
        # --- assessment phase ---
        result = engine.analyse(vec)  # call for each assessment window
    """

    def __init__(self):
        self.baseline = EWMABaseline()

    def update_baseline(self, feature_dict):
        """Accept a feature dict from extract_features / extract_mouse_features."""
        vec = _dict_to_vector(feature_dict)
        if vec is not None:
            self.baseline.update(vec, mask=_obs_mask(feature_dict))

    def analyse(self, feature_dict):
        """
        Run the full Stage 4-7 pipeline on one assessment window.
        Returns the result dict (flag, label, confidence, rationale, scores).
        Returns None if baseline is not ready.
        """
        if not self.baseline.is_ready:
            return None
        vec = _dict_to_vector(feature_dict)
        if vec is None:
            return None

        t2, thresh, S_inv = compute_t2(vec, self.baseline)
        C, psi, pai       = compute_contributions(vec, self.baseline.mu, S_inv,
                                                  ever_seen=self.baseline.ever_seen)
        fuzzy             = fuzzy_classify(t2, thresh, psi, pai)

        return {
            "t2_score":    round(t2, 4),
            "t2_threshold":round(thresh, 4),
            "psi":         round(psi, 4),
            "pai":         round(pai, 4),
            **fuzzy,
        }


def _dict_to_vector(feature_dict):
    """Convert a feature dict to the ordered 8-element numpy array."""
    if feature_dict is None:
        return None
    try:
        return np.array([
            feature_dict.get("flight_time",     0.0),
            feature_dict.get("dwell_time",       0.0),
            feature_dict.get("typing_velocity",  0.0),
            feature_dict.get("error_rate",       0.0),
            feature_dict.get("path_entropy",     0.0),
            feature_dict.get("cursor_velocity",  feature_dict.get("tv", 0.0)),
            feature_dict.get("jerk",             0.0),
            feature_dict.get("pause_frequency",  0.0),
        ], dtype=float)
    except Exception:
        return None
