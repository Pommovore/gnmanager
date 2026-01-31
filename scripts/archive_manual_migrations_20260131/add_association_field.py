import sqlite3
import os

def migrate():
    db_path = 'instance/gnmanager.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add organizing_association column
        cursor.execute("ALTER TABLE event ADD COLUMN organizing_association VARCHAR(150) DEFAULT 'une entité mystérieuse et inquiétante'")
        print("Column organizing_association added successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column organizing_association already exists.")
        else:
            print(f"Error: {e}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
