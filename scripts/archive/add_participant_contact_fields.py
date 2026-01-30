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
        # Add participant_phone column
        try:
            cursor.execute("ALTER TABLE participant ADD COLUMN participant_phone VARCHAR(20)")
            print("Added column 'participant_phone' to table 'participant'.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("Column 'participant_phone' already exists.")
            else:
                raise

        # Add participant_discord column
        try:
            cursor.execute("ALTER TABLE participant ADD COLUMN participant_discord VARCHAR(100)")
            print("Added column 'participant_discord' to table 'participant'.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("Column 'participant_discord' already exists.")
            else:
                raise

        # Add participant_facebook column
        try:
            cursor.execute("ALTER TABLE participant ADD COLUMN participant_facebook VARCHAR(200)")
            print("Added column 'participant_facebook' to table 'participant'.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("Column 'participant_facebook' already exists.")
            else:
                raise

        # Add share_phone column (boolean, default True)
        try:
            cursor.execute("ALTER TABLE participant ADD COLUMN share_phone BOOLEAN DEFAULT 1")
            print("Added column 'share_phone' to table 'participant'.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("Column 'share_phone' already exists.")
            else:
                raise

        # Add share_discord column (boolean, default True)
        try:
            cursor.execute("ALTER TABLE participant ADD COLUMN share_discord BOOLEAN DEFAULT 1")
            print("Added column 'share_discord' to table 'participant'.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("Column 'share_discord' already exists.")
            else:
                raise

        # Add share_facebook column (boolean, default True)
        try:
            cursor.execute("ALTER TABLE participant ADD COLUMN share_facebook BOOLEAN DEFAULT 1")
            print("Added column 'share_facebook' to table 'participant'.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("Column 'share_facebook' already exists.")
            else:
                raise

        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"An error occurred during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
