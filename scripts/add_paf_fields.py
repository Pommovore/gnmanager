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
        # Check Event table columns
        cursor.execute("PRAGMA table_info(event)")
        event_columns = [info[1] for info in cursor.fetchall()]
        
        if 'paf_config' not in event_columns:
            print("Adding paf_config column to Event...")
            cursor.execute("ALTER TABLE event ADD COLUMN paf_config TEXT DEFAULT '[]'")
        
        # Check Participant table columns
        cursor.execute("PRAGMA table_info(participant)")
        participant_columns = [info[1] for info in cursor.fetchall()]
            
        if 'paf_type' not in participant_columns:
            print("Adding paf_type column to Participant...")
            cursor.execute("ALTER TABLE participant ADD COLUMN paf_type VARCHAR(50)")
        
        conn.commit()
        print("Migration successful.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    run_migration()
