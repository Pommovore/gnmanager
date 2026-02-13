
import sqlite3
import os
import sys

# DATABASE SELECTION LOGIC
# Priority: instance/gnmanager.db (Flask default) -> gnmanager.db (Legacy/Root)
db_candidates = ['instance/gnmanager.db', 'gnmanager.db']
target_db = None

print("Searching for database...")
for db in db_candidates:
    if os.path.exists(db):
        print(f"Found: {db}")
        if target_db is None:
            target_db = db

if not target_db:
    print("NO DATABASE FOUND!")
    sys.exit(1)

print(f"TARGETING DATABASE: {target_db}")

try:
    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(participant)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'is_photo_locked' in columns:
        print(f"Column 'is_photo_locked' ALREADY EXISTS in {target_db}.")
    else:
        print(f"Adding column 'is_photo_locked' to {target_db}...")
        cursor.execute("ALTER TABLE participant ADD COLUMN is_photo_locked BOOLEAN DEFAULT 0")
        conn.commit()
        print("Column added SUCCESSFULLY.")
        
except Exception as e:
    print(f"ERROR: {e}")
finally:
    if 'conn' in locals():
        conn.close()
