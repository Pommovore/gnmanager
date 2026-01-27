import os
import secrets
from app import create_app
from models import db, Event
from dotenv import load_dotenv

load_dotenv()

def backfill_secrets():
    """Génère des secrets webhook pour les événements qui n'en ont pas."""
    # Ensure SECRET_KEY is set to avoid app factory error
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = 'dev-secret-key-for-script'
        
    
    """Génère des secrets webhook pour les événements qui n'en ont pas."""
    app = create_app()
    with app.app_context():
        events = Event.query.filter(Event.webhook_secret == None).all()
        print(f"Found {len(events)} events without secrets.")
        
        for event in events:
            secret = secrets.token_hex(16).upper()
            event.webhook_secret = secret
            print(f"Generated secret for event: {event.name}")
            
        db.session.commit()
        print("Done.")

if __name__ == "__main__":
    backfill_secrets()
