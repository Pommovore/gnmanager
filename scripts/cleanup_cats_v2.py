from app import create_app
from models import db, GFormsCategory, GFormsFieldMapping
import sqlalchemy as sa

app = create_app()
with app.app_context():
    print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
    cats = GFormsCategory.query.all()
    print(f"Found {len(cats)} categories total.")
    for c in cats:
        print(f"ID: {c.id}, Event: {c.event_id}, Name: '{c.name}'")
    
    # Clean up
    events = db.session.query(GFormsCategory.event_id).distinct().all()
    for (eid,) in events:
        event_cats = GFormsCategory.query.filter_by(event_id=eid).all()
        seen = {} # lower_name -> category_id
        for cat in event_cats:
            ln = cat.name.lower().strip()
            if ln == 'généralités':
                # We preferentially want 'Généralités'
                if ln in seen:
                    existing_id = seen[ln]
                    existing_cat = GFormsCategory.query.get(existing_id)
                    
                    # Decide which to keep. Keep the one named 'Généralités'
                    if cat.name == 'Généralités':
                        keep = cat
                        remove = existing_cat
                    else:
                        keep = existing_cat
                        remove = cat
                    
                    print(f"Merging {remove.name} (ID {remove.id}) into {keep.name} (ID {keep.id}) for Event {eid}")
                    # Update mappings
                    mappings = GFormsFieldMapping.query.filter_by(category_id=remove.id).all()
                    for m in mappings:
                        m.category_id = keep.id
                    
                    db.session.delete(remove)
                    db.session.flush()
                    seen[ln] = keep.id
                else:
                    seen[ln] = cat.id
    db.session.commit()
    print("Cleanup finished.")
