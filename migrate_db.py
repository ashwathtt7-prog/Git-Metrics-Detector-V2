import sqlite3
import os

db_path = "backend/data/metrics.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(analysis_jobs)")
    columns = [c[1] for c in cursor.fetchall()]
    
    if "current_stage" not in columns:
        print("Adding current_stage column...")
        cursor.execute("ALTER TABLE analysis_jobs ADD COLUMN current_stage INTEGER DEFAULT 1")
        
    if "logs" not in columns:
        print("Adding logs column...")
        cursor.execute("ALTER TABLE analysis_jobs ADD COLUMN logs TEXT")
        
    conn.commit()
    conn.close()
    print("Database migration complete.")
else:
    print("Database not found, init_db will handle creation.")
