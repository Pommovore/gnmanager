import sqlite3
import os

db_path = 'instance/gnmanager.db'
if not os.path.exists(db_path):
    print("Database not found")
    exit(1)

try:
    conn = sqlite3.connect(db_path, timeout=5)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(gforms_field_mapping);")
    columns = cursor.fetchall()
    for col in columns:
        print(col)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
