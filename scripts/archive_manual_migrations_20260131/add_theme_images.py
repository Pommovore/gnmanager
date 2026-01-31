import sqlite3
import os

# Database path (adjust if necessary)
DB_PATH = 'instance/gnmanager.db'

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(event)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'background_image_light' not in columns:
            print("Adding background_image_light column...")
            cursor.execute("ALTER TABLE event ADD COLUMN background_image_light VARCHAR(200)")
        
        if 'background_image_dark' not in columns:
            print("Adding background_image_dark column...")
            cursor.execute("ALTER TABLE event ADD COLUMN background_image_dark VARCHAR(200)")
            
        # We don't drop background_image to avoid data loss during dev, but it's deprecated in code
        
        conn.commit()
        print("Migration successful.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()
