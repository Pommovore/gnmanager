import sqlite3
import os

def migrate():
    db_path = 'instance/gnmanager.db'
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add phone column
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN phone VARCHAR(20)")
            print("Added column 'phone' to table 'user'.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("Column 'phone' already exists.")
            else:
                raise

        # Add discord column
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN discord VARCHAR(100)")
            print("Added column 'discord' to table 'user'.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("Column 'discord' already exists.")
            else:
                raise

        # Add facebook column
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN facebook VARCHAR(200)")
            print("Added column 'facebook' to table 'user'.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("Column 'facebook' already exists.")
            else:
                raise

        conn.commit()
    except Exception as e:
        print(f"An error occurred during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
