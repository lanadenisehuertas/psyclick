import pandas as pd
import numpy as np

def extract_features(raw_data_list):
    """
    Safely calculates Flight Time metrics.
    Returns: Dict with metrics OR None if insufficient data.
    """
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