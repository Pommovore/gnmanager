import sqlite3
import os

db_path = 'instance/gnmanager.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables found:")
    for table in tables:
        print(f"- {table[0]}")
    
    # Check explicitly for gforms tables
    gforms_tables = ['gforms_category', 'gforms_field_mapping', 'gforms_submission']
    existing_tables = [t[0] for t in tables]
    
    missing = [t for t in gforms_tables if t not in existing_tables]
    
    if missing:
        print(f"\nMISSING GFORMS TABLES: {missing}")
        exit(1)
    else:
        print("\nAll GForms tables are present.")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    exit(1)
