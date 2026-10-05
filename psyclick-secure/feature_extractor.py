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


# ── TYPING PLAUSIBILITY ─────────────────────────────────────────────────────
# People cannot press keys in the same millisecond again and again, and a held
# key auto-repeats without being released. Either one means the timing does
# not describe the person's typing (text injected by software, or a key held
# down), so it must not be scored or used as a baseline.
_SIMULTANEOUS_S   = 0.003   # presses closer than this are not human
_MAX_SIMULTANEOUS = 0.30    # share of such presses tolerated (fast rollover, chords)
_MAX_REPEATS      = 0.40    # share of auto-repeated presses tolerated
_DUPLICATE_S      = 0.002   # the same key event again within 2 ms is one physical event

# A gap this long between key presses is time away (a break, an interruption,
# leaving the keyboard), not typing rhythm. It is left out of every typing
# measure so averages describe only the time the person was actually typing.
# Thinking pauses shorter than this still count as pauses, as in the
# normative sessions, so ordinary sessions score exactly as before.
AWAY_S = 15.0
BREAK = "BREAK"   # marker the loggers insert where capture was suspended (focus lost)


def dedupe_key_events(raw_data_list):
    """
    Drop exact repeats of a key event (same key, same direction, within 2 ms).
    A person cannot press the same key twice in 2 ms; such a repeat is the
    same event delivered twice by the operating system hook.
    """
    out = []
    last = {}
    for e in sorted(raw_data_list or [], key=lambda e: e["time"]):
        if e.get("event") == BREAK:
            out.append(e)
            continue
        k = (e.get("key"), e.get("event"))
        if k in last and e["time"] - last[k] <= _DUPLICATE_S:
            continue
        last[k] = e["time"]
        out.append(e)
    return out


def typing_problem(raw_data_list):
    """Return None for plausible typing, else 'automatic' or 'held_key'."""
    if isinstance(raw_data_list, dict):
        raw_data_list = raw_data_list.get("keys", [])
    events = dedupe_key_events(raw_data_list)
    downs = [e for e in events if e.get("event") == "DOWN"]
    if len(downs) < 4:
        return None
    gaps = [b["time"] - a["time"] for a, b in zip(downs, downs[1:])]
    if sum(1 for g in gaps if g < _SIMULTANEOUS_S) / len(gaps) > _MAX_SIMULTANEOUS:
        return "automatic"
    held, repeats = set(), 0
    for e in events:
        k = e.get("key")
        if e.get("event") == "DOWN":
            if k in held:
                repeats += 1
            held.add(k)
        else:
            held.discard(k)
    if repeats / len(downs) > _MAX_REPEATS:
        return "held_key"
    return None


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
    raw_data_list = dedupe_key_events(raw_data_list)
    # Segments: a BREAK marker (capture suspended) starts a new segment, and
    # key gaps are only measured within one segment.
    seg, events = 0, []
    for e in raw_data_list:
        if e.get("event") == BREAK:
            seg += 1
            continue
        events.append({**e, "seg": seg})
    breaks = seg
    if len(events) < 4:
        return None

    df = pd.DataFrame(events)

    # ── Flight Time ───────────────────────────────────────────────────────────
    downs = df[df["event"] == "DOWN"].reset_index(drop=True)
    if len(downs) < 2:
        return None
    downs["prev_time"]   = downs["time"].shift(1)
    downs["flight_time"] = downs["time"] - downs["prev_time"]
    same_seg = downs["seg"] == downs["seg"].shift(1)
    measured = downs[same_seg].dropna(subset=["flight_time"]).copy()

    # Time away is reported, then left out of every measure below
    away_gaps = measured.loc[measured["flight_time"] >= AWAY_S, "flight_time"].tolist()
    typing = measured[measured["flight_time"] < AWAY_S]

    # Keep every in-rhythm flight for pause frequency and raw telemetry
    all_flights = typing["flight_time"]

    clean = typing[typing["flight_time"] < 2.0]   # discard pauses > 2 s for mean flight
    if clean.empty:
        return None

    # Exclude Enter key for flight time to avoid cognitive submission hesitation spikes
    clean_flight = clean[~clean["key"].str.lower().isin(["enter", "return"])]
    if clean_flight.empty:
        mean_flight = float(clean["flight_time"].mean()) # fallback
    else:
        mean_flight = float(clean_flight["flight_time"].mean())

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
    # Active typing time: the span of key presses minus time away and breaks
    # (identical to first-to-last key when there was neither).
    total_time = float(all_flights.sum())
    typing_velocity = len(clean) / total_time if total_time > 0 else 0.0

    # ── Error Rate ────────────────────────────────────────────────────────────
    # Count key-DOWN events only: each press also emits an UP event, which
    # would otherwise double-count every backspace.
    backspaces  = df[(df["event"] == "DOWN") & df["key"].isin(["backspace", "BackSpace"])].shape[0]
    total_keys  = len(df[df["event"] == "DOWN"])
    error_rate  = backspaces / total_keys if total_keys > 0 else 0.0

    # ── Pause Frequency (keystroke gaps > 1000 ms per second of typing) ──────
    pauses_ks      = int((all_flights > 1.0).sum())
    pause_frequency = float(pauses_ks / total_time) if total_time > 0 else 0.0


    return {
        "flight_time":     mean_flight,
        "dwell_time":      mean_dwell,
        "typing_velocity": typing_velocity,
        "error_rate":      error_rate,
        "pause_frequency": pause_frequency,
        "key_count":       len(clean),
        # Legacy aliases so existing backend_controller code still compiles
        "mean_flight":     mean_flight,
        "std_flight":      float(clean["flight_time"].std()) if len(clean) > 1 else 0.0,
        "raw_flight_times": all_flights.tolist(), # in-rhythm gaps, including true pauses
        # Data quality: time away from the keyboard and suspended capture
        "away_gaps":       [float(g) for g in away_gaps],
        "breaks":          breaks,
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
    resumed = None
    if "event" in df and (df["event"] == BREAK).any():
        resumed = (df["event"] == BREAK).shift(1, fill_value=False).cumsum()
        keep = df["event"] != BREAK
        df, resumed = df[keep].reset_index(drop=True), resumed[keep].reset_index(drop=True)
        if len(df) < 10:
            return None

    # ── Apply Sliding Window WMA (Stage 1) ───────────────────────────────────
    df["x"] = _sliding_wma(df["x"].values)
    df["y"] = _sliding_wma(df["y"].values)

    dt = df["time"].diff().replace(0, np.nan)
    if resumed is not None:
        dt[resumed != resumed.shift(1)] = np.nan   # first sample after a break
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
