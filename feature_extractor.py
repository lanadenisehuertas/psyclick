import pandas as pd
import numpy as np

def extract_features(raw_data_list):
    """
    Safely calculates Flight Time metrics.
    Returns: Dict with metrics OR None if insufficient data.
    """

    if isinstance(raw_data_list, dict):
        raw_data_list = raw_data_list.get('keys', [])
    # 1. Safety Check: Need at least 2 events to calculate intervals
    if not raw_data_list or len(raw_data_list) < 2:
        return None

    df = pd.DataFrame(raw_data_list)
    
    # 2. Filter for Key DOWN events only (Simplest calculation for Flight Time)
    downs = df[df['event'] == 'DOWN'].reset_index(drop=True)
    
    if len(downs) < 2:
        return None

    # 3. Calculate Flight Time (Latency between consecutive presses)
    # Flight Time = Time(Current_Key) - Time(Previous_Key)
    downs['prev_time'] = downs['time'].shift(1)
    downs['flight_time'] = downs['time'] - downs['prev_time']
    
    # 4. Clean Data (Remove first row which is NaN, and outliers > 2 seconds)
    clean_data = downs.dropna().copy()
    clean_data = clean_data[clean_data['flight_time'] < 2.0] # Remove pauses > 2s

    if clean_data.empty:
        return None

    # 5. Return Stats
    metrics = {
        'mean_flight': clean_data['flight_time'].mean(),
        'std_flight': clean_data['flight_time'].std(),
        'key_count': len(clean_data)
    }
    
    # Fix: If std is NaN (only 1 valid interval), set to 0
    if pd.isna(metrics['std_flight']):
        metrics['std_flight'] = 0.0

    return metrics

def extract_mouse_features(mouse_data):
    if len(mouse_data) < 5: return None
    
    df = pd.DataFrame(mouse_data)
    dt = df['time'].diff().fillna(0)
    dx = df['x'].diff().fillna(0)
    dy = df['y'].diff().fillna(0)

    # 1. Velocities (px/s)
    hv = (dx / dt).replace([np.inf, -np.inf], 0).fillna(0)
    vv = (dy / dt).replace([np.inf, -np.inf], 0).fillna(0)
    tv = np.sqrt(hv**2 + vv**2)

    # 2. Acceleration & Jerk (Derivatives of TV)
    ta = (tv.diff() / dt).fillna(0)
    jerk = (ta.diff() / dt).fillna(0)

    # 3. Curvature
    # C = |x'y'' - y'x''| / (x'^2 + y'^2)^(3/2)
    ddx = (hv.diff() / dt).fillna(0)
    ddy = (vv.diff() / dt).fillna(0)
    numerator = np.abs(hv * ddy - vv * ddx)
    denominator = np.power(tv, 3)
    curvature = (numerator / denominator).replace([np.inf, -np.inf], 0).fillna(0)

    return {
        'hv': hv.mean(), 'vv': vv.mean(), 'tv': tv.mean(),
        'ta': ta.mean(), 'jerk': jerk.mean(), 'curvature': curvature.mean()
    }