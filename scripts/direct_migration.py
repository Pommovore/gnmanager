
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
    cursor.execute("PRAGMA table_info(user)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'profile_photo_url' in columns:
        print(f"Column 'profile_photo_url' ALREADY EXISTS in {target_db}.")
    else:
        print(f"Adding column 'profile_photo_url' to {target_db}...")
        cursor.execute("ALTER TABLE user ADD COLUMN profile_photo_url VARCHAR(200)")
        conn.commit()
        print("Column added SUCCESSFULLY.")
        
except Exception as e:
    print(f"ERROR: {e}")
finally:
    if 'conn' in locals():
        conn.close()
