"""
feature_extractor.py  —  PsyClick
Stage 1 (Sliding Window WMA) + Stage 3 (Feature Extraction).

Produces an 8-feature vector from HAL-corrected key/mouse data:
    [flight_time, dwell_time, typing_velocity, error_rate,
     path_entropy, cursor_velocity, jerk, pause_frequency]

The Sliding Window WMA (Gaussian kernel [0.1, 0.2, 0.4, 0.2, 0.1])
is applied to cursor coordinates before mouse features are computed.
This attenuates high-frequency noise (>8 Hz) while preserving clinically
relevant hesitation patterns (<2 Hz) — Winter (2009).
"""

import numpy as np
import pandas as pd

# ── STAGE 1: SLIDING WINDOW WMA ───────────────────────────────────────────────
_KERNEL = np.array([0.1, 0.2, 0.4, 0.2, 0.1])   # Gaussian-approximate, 5-tap


def _sliding_wma(values):
    """
    Apply the weighted moving average to a 1-D array.
    Edges are handled by reflecting the signal so no boundary artefacts
    distort the first/last clinical windows.
    """
    arr = np.asarray(values, dtype=float)
    if len(arr) < len(_KERNEL):
        return arr                      # too short to filter — return as-is
    # np.convolve with 'same' gives the correct length; divide by kernel sum
    out = np.convolve(arr, _KERNEL, mode="same")
    # Normalise edges where the kernel partially overlaps the signal
    norm = np.convolve(np.ones_like(arr), _KERNEL, mode="same")
    return out / norm


# ── STAGE 3: KEYSTROKE FEATURE EXTRACTION ────────────────────────────────────
def extract_features(raw_data_list):
    """
    Converts HAL-corrected keystroke events into the 4 keyboard biomarkers.

    Returns dict with keys:
        flight_time      — mean latency between consecutive key presses (s)
        dwell_time       — mean key-hold duration (s)
        typing_velocity  — keystrokes per second
        error_rate       — proportion of backspace events
        key_count        — total valid keystrokes (for window size reference)
    """
    if isinstance(raw_data_list, dict):
        raw_data_list = raw_data_list.get("keys", [])
    if not raw_data_list or len(raw_data_list) < 4:
        return None

    df = pd.DataFrame(raw_data_list)

    # ── Flight Time ───────────────────────────────────────────────────────────
    downs = df[df["event"] == "DOWN"].reset_index(drop=True)
    if len(downs) < 2:
        return None
    downs["prev_time"]   = downs["time"].shift(1)
    downs["flight_time"] = downs["time"] - downs["prev_time"]
    clean = downs.dropna().copy()
    clean = clean[clean["flight_time"] < 2.0]   # discard pauses > 2 s
    if clean.empty:
        return None
    mean_flight = float(clean["flight_time"].mean())

    # EXTRACT REAL RAW DATA FOR SPECTROGRAM
    raw_flight_times = clean["flight_time"].tolist()

    # ── Dwell Time ────────────────────────────────────────────────────────────
    ups   = df[df["event"] == "UP"].reset_index(drop=True)
    dwell_times = []
    for _, dn_row in downs.iterrows():
        # Find the matching UP event for the same key after this DOWN time
        match = ups[(ups["key"] == dn_row["key"]) & (ups["time"] > dn_row["time"])]
        if not match.empty:
            dwell = float(match.iloc[0]["time"]) - float(dn_row["time"])
            if 0 < dwell < 1.0:           # ignore held keys > 1 s
                dwell_times.append(dwell)
    mean_dwell = float(np.mean(dwell_times)) if dwell_times else 0.0

    # ── Typing Velocity ───────────────────────────────────────────────────────
    total_time = float(downs["time"].iloc[-1] - downs["time"].iloc[0])
    typing_velocity = len(clean) / total_time if total_time > 0 else 0.0

    # ── Error Rate ────────────────────────────────────────────────────────────
    backspaces  = df[df["key"].isin(["backspace", "BackSpace"])].shape[0]
    total_keys  = len(df[df["event"] == "DOWN"])
    error_rate  = backspaces / total_keys if total_keys > 0 else 0.0

    return {
        "flight_time":     mean_flight,
        "dwell_time":      mean_dwell,
        "typing_velocity": typing_velocity,
        "error_rate":      error_rate,
        "key_count":       len(clean),
        # Legacy aliases so existing backend_controller code still compiles
        "mean_flight":     mean_flight,
        "std_flight":      float(clean["flight_time"].std()) if len(clean) > 1 else 0.0,
        "raw_flight_times": raw_flight_times # Real data payload
    }


# ── STAGE 3: MOUSE FEATURE EXTRACTION ────────────────────────────────────────
def extract_mouse_features(mouse_data):
    """
    Converts HAL-corrected mouse events into the 4 mouse biomarkers.

    Stage 1 (Sliding Window WMA) is applied to x and y coordinates
    before any derivative is computed.
    """
    if len(mouse_data) < 10:
        return None

    df = pd.DataFrame(mouse_data).sort_values("time").reset_index(drop=True)

    # ── Apply Sliding Window WMA (Stage 1) ───────────────────────────────────
    df["x"] = _sliding_wma(df["x"].values)
    df["y"] = _sliding_wma(df["y"].values)

    dt = df["time"].diff().replace(0, np.nan)
    dx = df["x"].diff()
    dy = df["y"].diff()

    # ── Cursor Velocity (px/s) ────────────────────────────────────────────────
    vx = (dx / dt).replace([np.inf, -np.inf], np.nan).fillna(0)
    vy = (dy / dt).replace([np.inf, -np.inf], np.nan).fillna(0)
    tv = np.sqrt(vx**2 + vy**2)
    cursor_velocity = float(tv.mean())

    # ── Jerk (3rd derivative of position, px/s³) ─────────────────────────────
    ta   = (tv.diff() / dt).fillna(0)
    jerk_series = (ta.diff() / dt).fillna(0)
    jerk = float(jerk_series.abs().mean())

    # ── Path Entropy ──────────────────────────────────────────────────────────
    # Discretise movement angles into 8 octants; compute Shannon entropy
    angles = np.arctan2(dy.fillna(0), dx.fillna(0))
    bins   = np.linspace(-np.pi, np.pi, 9)
    counts, _ = np.histogram(angles, bins=bins)
    counts = counts[counts > 0]
    probs  = counts / counts.sum()
    path_entropy = float(-np.sum(probs * np.log2(probs))) if len(probs) > 0 else 0.0

    # ── Pause Frequency (gaps > 500 ms per second of recording) ──────────────
    total_duration = float(df["time"].iloc[-1] - df["time"].iloc[0])
    pauses = (dt > 0.5).sum()
    pause_frequency = float(pauses / total_duration) if total_duration > 0 else 0.0

    # EXTRACT REAL X/Y COORDS OF HESITATIONS FOR HEATMAP
    pauses_df = df[dt > 0.5]
    pause_coords = list(zip(pauses_df["x"], pauses_df["y"])) if not pauses_df.empty else []

    return {
        "path_entropy":    path_entropy,
        "cursor_velocity": cursor_velocity,
        "jerk":            jerk,
        "pause_frequency": pause_frequency,
        # Legacy aliases used by existing backend_controller / database_manager
        "hv":        cursor_velocity,
        "vv":        cursor_velocity,
        "tv":        cursor_velocity,
        "ta":        float(ta.mean()),
        "curvature": 0.0,
        "pause_coords": pause_coords # Real data payload
    }
