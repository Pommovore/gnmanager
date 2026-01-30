import sqlite3
import os

db_path = 'instance/gnmanager.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE participant ADD COLUMN info_payement TEXT")
    print("Column 'info_payement' added to 'participant' table.")
except sqlite3.OperationalError:
    print("Column 'info_payement' already exists or other error.")

conn.commit()
conn.close()
