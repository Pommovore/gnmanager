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
        # Add payment_methods column with default value
        try:
            cursor.execute('ALTER TABLE event ADD COLUMN payment_methods TEXT DEFAULT \'["Helloasso"]\'')
            print("Added column 'payment_methods' to table 'event'.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                print("Column 'payment_methods' already exists.")
            else:
                raise

        # Update existing rows that might have NULL values
        cursor.execute('UPDATE event SET payment_methods = \'["Helloasso"]\' WHERE payment_methods IS NULL')
        updated = cursor.rowcount
        if updated > 0:
            print(f"Updated {updated} existing event(s) with default payment methods.")

        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"An error occurred during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
