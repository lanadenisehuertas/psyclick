import sqlite3
import os

DB_NAME = "psyclick_data.db"

def init_db():
    """Initializes the SQLite database with the required tables."""
    # Connect and ensure tables exist
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Users Table (Stores the Personal Baseline)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            student_id TEXT PRIMARY KEY,
            baseline_mean_flight REAL,
            baseline_std_flight REAL,
            last_calibrated TEXT
        )
    ''')

    # 2. Sessions Table (Stores Z-Scores & Flags)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            mean_flight REAL,
            z_score REAL,
            is_anomaly BOOLEAN,
            timestamp TEXT,
            FOREIGN KEY(student_id) REFERENCES users(student_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} ready.")

def save_user_baseline(student_id, mean, std):
    """Saves or updates a user's baseline stats."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (student_id, baseline_mean_flight, baseline_std_flight, last_calibrated)
        VALUES (?, ?, ?, datetime('now'))
    ''', (student_id, mean, std))
    conn.commit()
    conn.close()

def get_user_baseline(student_id):
    """Retrieves (mean, std) for a student. Returns None if not found."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT baseline_mean_flight, baseline_std_flight FROM users WHERE student_id=?", (student_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def save_session(student_id, mean_flight, z_score, is_anomaly):
    """Logs the session result."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sessions (student_id, mean_flight, z_score, is_anomaly, timestamp)
        VALUES (?, ?, ?, ?, datetime('now'))
    ''', (student_id, mean_flight, z_score, is_anomaly))
    conn.commit()
    conn.close()