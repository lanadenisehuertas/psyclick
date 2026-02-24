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
from scipy.stats import f as f_dist

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


# ── STAGE 2: WITHIN-SESSION EWMA ─────────────────────────────────────────────
class EWMABaseline:
    """
    Builds an adaptive personal baseline during the calibration phase.

    mu_ewma(t)  = lambda * x(t) + (1 - lambda) * mu_ewma(t-1)
    S_ewma(t)   = lambda * outer(diff, diff) + (1 - lambda) * S_ewma(t-1)
    """

    def __init__(self):
        self.mu   = None        # mean vector (p,)
        self.S    = None        # covariance matrix (p, p)
        self.n    = 0           # number of windows seen

    def update(self, x):
        """Feed one feature vector (length 8) from the calibration phase."""
        x = np.asarray(x, dtype=float)
        if self.mu is None:
            self.mu = x.copy()
            self.S  = np.eye(N_FEATURES) * 1e-4   # tiny seed — avoids singular start
        else:
            diff    = x - self.mu
            self.mu = _LAMBDA * x + (1.0 - _LAMBDA) * self.mu
            self.S  = _LAMBDA * np.outer(diff, diff) + (1.0 - _LAMBDA) * self.S
        self.n += 1

    @property
    def is_ready(self):
        # 1 window is enough to seed the baseline.
        # EWMA adapts as more windows arrive — we never block analysis
        # just because the user only completed one calibration pass.
        return self.n >= 1


# ── STAGE 4: HOTELLING'S T² ───────────────────────────────────────────────────
def _covariance_inverse(S, n):
    """
    Return the precision matrix (S^-1).
    Applies deterministic analytical shrinkage for small samples (n < 20)
    to guarantee invertibility without relying on stochastic data generation.
    """
    p = S.shape[0]
    
    if n < 20:
        # Deterministic Shrinkage (Ledoit-Wolf approximation)
        # Shrinks the empirical covariance matrix towards a scaled identity matrix
        shrinkage = 0.15  # 15% shrinkage intensity for small n
        mu_trace = np.trace(S) / p
        S_shrunk = (1.0 - shrinkage) * S + (shrinkage * mu_trace * np.eye(p))
        return np.linalg.inv(S_shrunk)
    else:
        try:
            return np.linalg.inv(S)
        except np.linalg.LinAlgError:
            # Last-resort regularisation if matrix is computationally singular
            S_reg = S + np.eye(p) * 1e-6
            return np.linalg.inv(S_reg)

def _t2_threshold(n, p=N_FEATURES, alpha=0.05):
    """
    F-distribution threshold for Hotelling's T² (Tracy et al., 1992):
        T²_threshold = [p(n-1) / (n-p)] * F(alpha; p, n-p)
    """
    if n <= p:
        return float("inf")           # not enough calibration data
    f_crit = f_dist.ppf(1.0 - alpha, p, n - p)
    return (p * (n - 1) / (n - p)) * f_crit


def compute_t2(x, baseline):
    """
    Compute T² score and threshold for a single assessment window.

    Returns (t2_score, t2_threshold, precision_matrix)
    """
    diff   = x - baseline.mu
    S_inv  = _covariance_inverse(baseline.S, baseline.n)
    t2     = float(baseline.n * diff @ S_inv @ diff)
    thresh = _t2_threshold(baseline.n)
    return t2, thresh, S_inv


# ── STAGE 5: FEATURE CONTRIBUTION (PSI / PAI) ────────────────────────────────
def compute_contributions(x, mu, S_inv):
    diff = x - mu
    weighted = S_inv @ diff
    C   = diff * weighted  # Magnitude of contribution
    
    # Optional: Only count towards PSI if the user actually slowed down (diff > 0)
    # Only count towards PAI if the user became more erratic
    psi = 0.0
    for idx in _PSI_IDX:
        # e.g., If flight time (diff) is positive, they are slower. 
        if diff[idx] > 0: psi += C[idx]
            
    pai = 0.0
    for idx in _PAI_IDX:
        # Add directional logic depending on the specific PAI feature
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
    Fuzzy Logic Classifier + Heuristic Decision Tree (combined Stage 6+7).

    Inputs
    ------
    t2        : raw T² score
    threshold : F-distribution threshold for the current session
    psi       : Psychomotor Slowing Index  (sum of PSI contributions)
    pai       : Psychomotor Agitation Index (sum of PAI contributions)

    Returns
    -------
    dict: flag, label, confidence, rationale
    """
    # ── Normalise inputs to [0, 1] ───────────────────────────────────────────
    # T² is expressed as a ratio to threshold (0 = baseline, 2 = double threshold)
    t2_ratio = t2 / (threshold + 1e-9)
    t2_n     = _normalise(t2_ratio,  0.0, 2.0)

    # PSI and PAI can be negative (within-normal); clamp before normalising
    psi_n = _normalise(max(psi, 0), 0.0, 5.0)
    pai_n = _normalise(max(pai, 0), 0.0, 5.0)

    # ── Membership degrees ────────────────────────────────────────────────────
    # T² memberships
    t2_low  = _trapmf(t2_n, 0.0, 0.0, 0.30, 0.55)
    t2_mod  = _trimf (t2_n, 0.30, 0.55, 0.80)
    t2_high = _trapmf(t2_n, 0.55, 0.80, 1.0,  1.0)

    # PSI memberships
    psi_low  = _trapmf(psi_n, 0.0, 0.0, 0.25, 0.50)
    psi_high = _trapmf(psi_n, 0.40, 0.65, 1.0, 1.0)

    # PAI memberships
    pai_low  = _trapmf(pai_n, 0.0, 0.0, 0.25, 0.50)
    pai_mod  = _trimf (pai_n, 0.30, 0.55, 0.80)
    pai_high = _trapmf(pai_n, 0.40, 0.65, 1.0, 1.0)

    # ── Rule firing strengths (min-conjunction) ───────────────────────────────
    r_normal      = t2_low                                          # R3
    r_retardation = min(t2_high, psi_high, pai_low)                 # R1
    r_agitation   = min(t2_mod,  pai_mod)                           # R2
    r_mixed       = min(psi_high, pai_high)                         # R4

    # ── Centroid defuzzification (weighted average of rule strengths) ─────────
    rules = {
        "Normal":                r_normal,
        "Psychomotor Retardation": r_retardation,
        "Psychomotor Agitation":   r_agitation,
        "Mixed Disturbance":       r_mixed,
    }
    total_strength = sum(rules.values())
    if total_strength == 0:
        dominant_label = "Normal"
        confidence     = 1.0
    else:
        dominant_label = max(rules, key=rules.get)
        confidence     = rules[dominant_label] / total_strength

    # ── Heuristic Decision Tree → final flag ─────────────────────────────────
    # The flag is NOT derived from T² thresholds alone; it is derived from
    # the fuzzy output so the classification is always graded and consistent.
    if dominant_label == "Normal" or t2_ratio <= 1.0:
        flag     = "GREEN"
        severity = "No psychomotor anomaly detected."
    elif t2_ratio <= 1.5 or dominant_label in ("Psychomotor Agitation", "Mixed Disturbance"):
        flag     = "AMBER"
        severity = "Moderate deviation — warrants clinical attention."
    else:
        flag     = "RED"
        severity = "Significant anomaly — clinical intervention recommended."

    # ── Plain-language rationale ──────────────────────────────────────────────
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
            self.baseline.update(vec)

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
        C, psi, pai       = compute_contributions(vec, self.baseline.mu, S_inv)
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
