import sqlite3
import os

db_path = 'instance/gnmanager.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Categories in GFormsCategory:")
cursor.execute("SELECT id, event_id, name FROM gforms_category;")
rows = cursor.fetchall()
for row in rows:
    print(row)

print("\nCleaning up duplicates...")
# Map to find duplicates (case insensitive)
# We want to keep 'Généralités' and remove 'généralités' (lowercase) or others if they exist for the same event
# Actually let's just find where we have multiple 'généralités' (any case) per event_id

cursor.execute("SELECT id, event_id, name FROM gforms_category WHERE LOWER(name) = 'généralités';")
gen_cats = cursor.fetchall()

event_to_cats = {}
for cid, eid, name in gen_cats:
    if eid not in event_to_cats:
        event_to_cats[eid] = []
    event_to_cats[eid].append((cid, name))

for eid, cats in event_to_cats.items():
    if len(cats) > 1:
        print(f"Found duplicates for Event {eid}: {cats}")
        # Keep the one named 'Généralités' (capitalized) if it exists, otherwise pick the first one
        keep_id = None
        for cid, name in cats:
            if name == 'Généralités':
                keep_id = cid
                break
        
        if keep_id is None:
            keep_id = cats[0][0]
        
        delete_ids = [cid for cid, name in cats if cid != keep_id]
        print(f"Keeping ID {keep_id}, deleting IDs {delete_ids}")
        
        # Before deleting, update all field mappings that point to these IDs
        for del_id in delete_ids:
            cursor.execute("UPDATE gforms_field_mapping SET category_id = ? WHERE category_id = ?", (keep_id, del_id))
            cursor.execute("DELETE FROM gforms_category WHERE id = ?", (del_id,))

conn.commit()
conn.close()
print("Cleanup done.")
