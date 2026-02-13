
import sqlite3
import os

# Try to find the database file
db_path = 'gnmanager.db'
if not os.path.exists(db_path):
    # Try instance folder if it exists (Flask default for some configs)
    if os.path.exists('instance/gnmanager.db'):
        db_path = 'instance/gnmanager.db'

print(f"Checking database at: {db_path}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        print("Columns in 'user' table:")
        found = False
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
            if col[1] == 'profile_photo_url':
                found = True
        
        if found:
            print("\nSUCCESS: profile_photo_url column exists.")
        else:
            print("\nFAILURE: profile_photo_url column MISSING.")
            
    except Exception as e:
        print(f"Error reading database: {e}")
    finally:
        conn.close()
else:
    print("Database file not found.")
