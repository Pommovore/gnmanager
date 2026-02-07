import sqlite3
import os

db_path = 'instance/gnmanager.db'
if not os.path.exists(db_path):
    # Try current dir
    db_path = 'gnmanager.db'

print(f"Using DB at: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Find all categories
cursor.execute("SELECT id, event_id, name FROM gforms_category")
all_cats = cursor.fetchall()

print(f"Total categories: {len(all_cats)}")
for c in all_cats:
    print(c)

# Find duplicates of 'généralités' per event
event_gen_cats = {}
for cid, eid, name in all_cats:
    if name.lower().strip() == 'généralités':
        if eid not in event_gen_cats:
            event_gen_cats[eid] = []
        event_gen_cats[eid].append((cid, name))

for eid, cats in event_gen_cats.items():
    if len(cats) > 1:
        print(f"Fixing duplicates for event {eid}: {cats}")
        # Keep 'Généralités' (capitalized) if it exists
        keep_id = None
        for cid, name in cats:
            if name == 'Généralités':
                keep_id = cid
                break
        if not keep_id:
            keep_id = cats[0][0]
        
        delete_ids = [cid for cid, name in cats if cid != keep_id]
        print(f"Keeping {keep_id}, deleting {delete_ids}")
        
        for did in delete_ids:
            cursor.execute("UPDATE gforms_field_mapping SET category_id = ? WHERE category_id = ?", (keep_id, did))
            cursor.execute("DELETE FROM gforms_category WHERE id = ?", (did,))

conn.commit()
conn.close()
print("Final check script finished.")
