import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gnmanager.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add display_organizers column with default 1 (True)
        cursor.execute("ALTER TABLE event ADD COLUMN display_organizers BOOLEAN DEFAULT 1")
        print("Column 'display_organizers' added successfully to 'event' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'display_organizers' already exists.")
        else:
            print(f"An error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
