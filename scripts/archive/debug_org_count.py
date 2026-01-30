import sqlite3
import os

db_path = 'instance/gnmanager.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Find the event
event_name_query = '%Berlin 1936%'
cursor.execute("SELECT id, name FROM event WHERE name LIKE ?", (event_name_query,))
event = cursor.fetchone()

if not event:
    print("Event not found")
    exit(0)

event_id = event['id']
print(f"Event Found: ID={event_id}, Name={event['name']}")

# Count participants by type
cursor.execute("""
    SELECT type, registration_status, COUNT(*) as count 
    FROM participant 
    WHERE event_id = ? 
    GROUP BY type, registration_status
""", (event_id,))

rows = cursor.fetchall()
print("\nParticipants for this event:")
for row in rows:
    print(f"Type: {row['type']}, Status: {row['registration_status']}, Count: {row['count']}")

# Check for any participant that might be an organizer but has a different type/status string
cursor.execute("SELECT * FROM participant WHERE event_id = ?", (event_id,))
all_participants = cursor.fetchall()

print(f"\nTotal participants: {len(all_participants)}")

conn.close()
