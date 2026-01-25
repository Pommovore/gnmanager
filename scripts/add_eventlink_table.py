import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from app import create_app
    from models import db, Event, EventLink
    
    app = create_app()

    with app.app_context():
        # Create the table
        print("Creating table event_link...")
        # This detects the new model and creates the table if not exists
        db.create_all() 
        
        # Migrate data from org_link_url/title to new table
        print("Migrating existing links...")
        try:
            events = Event.query.all()
            count = 0
            for event in events:
                if event.org_link_url:
                    # Check if link already exists to avoid duplication if run multiple times
                    existing = EventLink.query.filter_by(event_id=event.id, url=event.org_link_url).first()
                    if not existing:
                        link = EventLink(
                            event_id=event.id,
                            title=event.org_link_title or "Site Web",
                            url=event.org_link_url,
                            position=0
                        )
                        db.session.add(link)
                        count += 1
            
            db.session.commit()
            print(f"Migration complete. {count} links migrated.")
        except Exception as e:
            print(f"Error during data migration: {e}")
            db.session.rollback()
            sys.exit(1)

except Exception as e:
    print(f"Critical error: {e}")
    sys.exit(1)
