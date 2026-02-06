import sqlite3

DB_NAME = "psyclick_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intake_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            
            -- 1. Keyboard Baseline (Motor Speed)
            kbase_mean REAL, kbase_std REAL,
            
            -- 2. Mouse Baseline (Kinematics)
            mbase_hv REAL, mbase_vv REAL, mbase_tv REAL, 
            mbase_ta REAL, mbase_jerk REAL, mbase_curve REAL,
            
            -- 3. PHQ-9 Data
            phq_score INTEGER,
            phq_hv REAL, phq_vv REAL, phq_tv REAL, 
            phq_ta REAL, phq_jerk REAL, phq_curve REAL,
            
            -- 4. GAD-7 Data
            gad_score INTEGER,
            gad_hv REAL, gad_vv REAL, gad_tv REAL, 
            gad_ta REAL, gad_jerk REAL, gad_curve REAL,
            
            -- 5. Emotional Task Data
            task_k_mean REAL, task_k_std REAL,
            
            -- 6. Final Analysis (Z-Scores)
            k_z_score REAL,    -- Typing Speed Z-Score
            m_z_score REAL     -- Mouse Agitation (Jerk) Z-Score
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} ready with Kinematic columns.")

def save_full_intake(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO intake_sessions (
            student_id, 
            kbase_mean, kbase_std,
            mbase_hv, mbase_vv, mbase_tv, mbase_ta, mbase_jerk, mbase_curve,
            phq_score, phq_hv, phq_vv, phq_tv, phq_ta, phq_jerk, phq_curve,
            gad_score, gad_hv, gad_vv, gad_tv, gad_ta, gad_jerk, gad_curve,
            task_k_mean, task_k_std,
            k_z_score, m_z_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['student_id'],
        data['kbase']['mean_flight'], data['kbase']['std_flight'],
        
        data['mbase']['hv'], data['mbase']['vv'], data['mbase']['tv'], 
        data['mbase']['ta'], data['mbase']['jerk'], data['mbase']['curvature'],
        
        data['phq']['score'], 
        data['phq']['mouse']['hv'], data['phq']['mouse']['vv'], data['phq']['mouse']['tv'], 
        data['phq']['mouse']['ta'], data['phq']['mouse']['jerk'], data['phq']['mouse']['curvature'],
        
        data['gad']['score'], 
        data['gad']['mouse']['hv'], data['gad']['mouse']['vv'], data['gad']['mouse']['tv'], 
        data['gad']['mouse']['ta'], data['gad']['mouse']['jerk'], data['gad']['mouse']['curvature'],
        
        data['task']['mean_flight'], data['task']['std_flight'],
        data['k_z_score'], data['m_z_score']
    ))
    
    conn.commit()
    conn.close()
    print(">> Intake Session (with Kinematics) Saved.")