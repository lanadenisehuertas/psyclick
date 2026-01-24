from scipy.stats import zscore
import sqlite3

DB_NAME = "psyclick_data.db"

def calculate_z_score(current_value, baseline_mean, baseline_std):
    """
    The Mathematical Core:
    Z = (X - μ) / σ
    """
    if baseline_std == 0: return 0 # Avoid division by zero
    return (current_value - baseline_mean) / baseline_std

def analyze_session(student_id, current_metrics):
    """
    Compares current session metrics against the stored database baseline.
    Returns: (z_score, is_anomaly)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Fetch User's Ipsative Baseline (Individual Norm)
    cursor.execute("SELECT baseline_mean_flight, baseline_std_flight FROM users WHERE student_id=?", (student_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return None, "User not calibrated"

    base_mean, base_std = result
    curr_mean = current_metrics['mean_flight']

    # 2. Perform Z-Score Analysis
    z_score = calculate_z_score(curr_mean, base_mean, base_std)
    
    # 3. Flagging Logic (Threshold > 2.0 Sigma)
    # If Z > 2.0 (Significantly Slower) OR Z < -2.0 (Significantly Erratic/Fast)
    is_anomaly = abs(z_score) > 2.0
    
    return z_score, is_anomaly