import sys
import time
import sqlite3
import math
import pandas as pd
import numpy as np
from pynput import keyboard, mouse
from datetime import datetime

# ==========================================
# PART 1: DATABASE MANAGER (Storage Layer)
# ==========================================
DB_NAME = "psyclick_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Updated Schema: Includes Cursor Speed
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            student_id TEXT PRIMARY KEY,
            baseline_mean_flight REAL,
            baseline_std_flight REAL,
            baseline_cursor_speed REAL,   -- NEW: Mouse Baseline
            baseline_std_cursor REAL,     -- NEW: Mouse Consistency
            last_calibrated TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            mean_flight REAL,
            mean_cursor_speed REAL,       -- NEW: Session Mouse Speed
            z_score_flight REAL,
            z_score_cursor REAL,          -- NEW: Cursor Z-Score
            is_anomaly BOOLEAN,
            timestamp TEXT,
            FOREIGN KEY(student_id) REFERENCES users(student_id)
        )
    ''')
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_NAME}")

def save_user_baseline(student_id, mean_flight, std_flight, mean_cursor, std_cursor):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (student_id, baseline_mean_flight, baseline_std_flight, baseline_cursor_speed, baseline_std_cursor, last_calibrated)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    ''', (student_id, mean_flight, std_flight, mean_cursor, std_cursor))
    conn.commit()
    conn.close()

def get_user_baseline(student_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT baseline_mean_flight, baseline_std_flight, baseline_cursor_speed, baseline_std_cursor FROM users WHERE student_id=?", (student_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def save_session(student_id, mean_f, mean_c, z_f, z_c, is_anomaly):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sessions (student_id, mean_flight, mean_cursor_speed, z_score_flight, z_score_cursor, is_anomaly, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (student_id, mean_f, mean_c, z_f, z_c, is_anomaly))
    conn.commit()
    conn.close()

# ==========================================
# PART 2: DYNAMICS LOGGER (Sensors)
# ==========================================
class MultiLogger:
    def __init__(self):
        self.raw_data = [] 
        self.key_listener = None
        self.mouse_listener = None

    def on_key_press(self, key):
        try:
            k_char = key.char
        except AttributeError:
            k_char = str(key).replace("Key.", "")
        
        self.raw_data.append({
            'type': 'KEY',
            'val': k_char, 
            'time': time.perf_counter()
        })

    def on_mouse_move(self, x, y):
        # We capture X, Y coordinates
        self.raw_data.append({
            'type': 'MOUSE',
            'x': x,
            'y': y,
            'time': time.perf_counter()
        })

    def start_logging(self):
        self.raw_data = []
        # Start Keyboard Listener
        self.key_listener = keyboard.Listener(on_press=self.on_key_press)
        self.key_listener.start()
        
        # Start Mouse Listener
        self.mouse_listener = mouse.Listener(on_move=self.on_mouse_move)
        self.mouse_listener.start()

    def stop_logging(self):
        if self.key_listener: self.key_listener.stop()
        if self.mouse_listener: self.mouse_listener.stop()
        return self.raw_data

# ==========================================
# PART 3: FEATURE EXTRACTOR (Math)
# ==========================================
def extract_features(raw_data_list):
    if not raw_data_list: return None

    df = pd.DataFrame(raw_data_list)
    
    # --- 1. KEYBOARD METRICS ---
    keys = df[df['type'] == 'KEY'].copy()
    flight_stats = {'mean': 0.0, 'std': 0.0}
    
    if len(keys) >= 2:
        keys['prev_time'] = keys['time'].shift(1)
        keys['flight'] = keys['time'] - keys['prev_time']
        clean_keys = keys.dropna()
        clean_keys = clean_keys[clean_keys['flight'] < 2.0] # Remove long pauses
        if not clean_keys.empty:
            flight_stats['mean'] = clean_keys['flight'].mean()
            flight_stats['std'] = clean_keys['flight'].std()

    # --- 2. MOUSE METRICS ---
    mice = df[df['type'] == 'MOUSE'].copy()
    cursor_stats = {'speed': 0.0, 'std': 0.0}
    
    if len(mice) >= 2:
        # Calculate Euclidean Distance between consecutive points
        mice['prev_x'] = mice['x'].shift(1)
        mice['prev_y'] = mice['y'].shift(1)
        mice['prev_time'] = mice['time'].shift(1)
        
        # Distance = sqrt((x2-x1)^2 + (y2-y1)^2)
        mice['dist'] = np.sqrt((mice['x'] - mice['prev_x'])**2 + (mice['y'] - mice['prev_y'])**2)
        mice['dt'] = mice['time'] - mice['prev_time']
        
        # Speed = Distance / Time (Pixels per Second)
        # Avoid division by zero
        mice = mice[mice['dt'] > 0.001]
        mice['speed'] = mice['dist'] / mice['dt']
        
        if not mice.empty:
            cursor_stats['speed'] = mice['speed'].mean()
            cursor_stats['std'] = mice['speed'].std()

    return {
        'mean_flight': flight_stats['mean'],
        'std_flight': flight_stats['std'],
        'mean_cursor': cursor_stats['speed'],
        'std_cursor': cursor_stats['std']
    }

# ==========================================
# PART 4: ANOMALY ENGINE (Logic)
# ==========================================
def analyze_session(student_id, current_metrics):
    baseline = get_user_baseline(student_id)
    if not baseline: return None, None, "NOT_CALIBRATED"

    # Unpack Baseline (Keyboard Mean/Std, Mouse Mean/Std)
    b_mean_f, b_std_f, b_mean_c, b_std_c = baseline
    
    # --- Z-Score Calculation ---
    # Flight Time Z-Score
    if b_std_f == 0: z_flight = 0.0
    else: z_flight = (current_metrics['mean_flight'] - b_mean_f) / b_std_f
    
    # Cursor Speed Z-Score
    if b_std_c == 0: z_cursor = 0.0
    else: z_cursor = (current_metrics['mean_cursor'] - b_mean_c) / b_std_c
    
    # --- Anomaly Logic (Check BOTH) ---
    # We flag if EITHER metric is > 2.0 Sigma
    is_anomaly = abs(z_flight) > 2.0 or abs(z_cursor) > 2.0
    
    return z_flight, z_cursor, is_anomaly

# ==========================================
# PART 5: MAIN CONTROLLER (UI)
# ==========================================
def run_calibration(student_id):
    print(f"\n--- 🔵 CALIBRATION MODE: {student_id} ---")
    print("INSTRUCTION: Type the sentence AND move your mouse around a bit.")
    print("SENTENCE:    The quick brown fox jumps over the lazy dog.")
    
    logger = MultiLogger()
    logger.start_logging()
    
    user_input = input("TYPE HERE >> ")
    
    raw_logs = logger.stop_logging()
    metrics = extract_features(raw_logs)

    if metrics and (metrics['mean_flight'] > 0 or metrics['mean_cursor'] > 0):
        save_user_baseline(
            student_id, 
            metrics['mean_flight'], metrics['std_flight'],
            metrics['mean_cursor'], metrics['std_cursor']
        )
        print(f"✅ SUCCESS: Baseline Saved.")
        print(f"   Typing Speed: {metrics['mean_flight']:.4f}s latency")
        print(f"   Cursor Speed: {metrics['mean_cursor']:.2f} px/sec")
    else:
        print("❌ Error: Not enough activity detected.")

def run_session(student_id):
    print(f"\n--- 🟢 SESSION MODE: {student_id} ---")
    print("INSTRUCTION: Answer honestly. (Move mouse naturally as you think/type)")
    print("QUESTION:    How are you feeling right now?")
    
    logger = MultiLogger()
    logger.start_logging()
    
    user_input = input("ANSWER >> ")
    
    raw_logs = logger.stop_logging()
    metrics = extract_features(raw_logs)
    
    if not metrics:
        print("❌ Error: No data.")
        return

    z_f, z_c, is_anomaly = analyze_session(student_id, metrics)
    
    if is_anomaly == "NOT_CALIBRATED":
        print(f"⚠️ Error: Student {student_id} is not calibrated.")
        return

    save_session(student_id, metrics['mean_flight'], metrics['mean_cursor'], z_f, z_c, is_anomaly)

    print("\n" + "="*45)
    print(f"PSYCLICK REPORT: {student_id}")
    print(f"Keyboard Z-Score: {z_f:.2f} σ")
    print(f"Cursor   Z-Score: {z_c:.2f} σ")
    print("-" * 45)
    
    if is_anomaly:
        print("🚩 ANOMALY DETECTED")
        
        # Logic for Slowing (High Latency OR Low Cursor Speed)
        if z_f > 2.0 or z_c < -2.0:
            print("Type: Psychomotor SLOWING (Depression Marker)")
            print("      (Slow typing or sluggish mouse movement)")
            
        # Logic for Agitation (Fast/Erratic Typing OR High Cursor Speed)
        elif z_f < -2.0 or z_c > 2.0:
            print("Type: Psychomotor AGITATION (Anxiety Marker)")
            print("      (Erratic typing or jittery mouse movement)")
    else:
        print("✅ STATUS: Normal Range")
    print("="*45)

def main():
    init_db()
    while True:
        print("\n=== PsyClick Backend System (Keyboard + Mouse) ===")
        print("1. Calibrate")
        print("2. Analyze Session")
        print("3. Exit")
        choice = input("Select: ")
        
        if choice == '1':
            sid = input("Enter Student ID: ")
            if sid: run_calibration(sid)
        elif choice == '2':
            sid = input("Enter Student ID: ")
            if sid: run_session(sid)
        elif choice == '3':
            break

if __name__ == "__main__":
    main()