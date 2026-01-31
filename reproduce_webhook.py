
import json
from app import create_app
from models import db, User, Participant, Event, FormResponse
from constants import RegistrationStatus, ParticipantType
from werkzeug.security import generate_password_hash

def test_webhook_update():
    app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False})
    
    with app.app_context():
        # Clean db
        db.create_all()
        User.query.delete()
        Participant.query.delete()
        Event.query.delete()
        FormResponse.query.delete()
        
        # Create Dummy Event and User
        event = Event(name="Test Event", date_start=None, date_end=None, 
                      webhook_secret="SECRET123", is_casting_validated=False)
        db.session.add(event)
        
        user = User(email="test@example.com", nom="Test", prenom="User", 
                    password_hash="...", role="user", is_banned=False, is_deleted=False)
        db.session.add(user)
        db.session.commit()
        
        # Helper to get participant
        def get_p():
            return Participant.query.filter_by(user_id=user.id, event_id=event.id).first()

        # 1. First Call: Should create Participant and add comment
        client = app.test_client()
        payload = {
            "responseId": "RESP_001",
            "formId": "FORM_001",
            "email": "test@example.com",
            "timestamp": "2026-01-01T12:00:00.000Z",
            "answers": {
                "Question 1": "Permis A",
                "Question 2": "Végétarien"
            }
        }
        
        headers = {'Authorization': 'Bearer SECRET123', 'Content-Type': 'application/json'}
        resp = client.post('/api/webhook/gform', data=json.dumps(payload), headers=headers)
        
        print(f"Response 1: {resp.status_code}")
        print(f"Response 1 Body: {resp.get_json()}")
        
        p = get_p()
        if p:
            print(f"Participant Created: {p.id}")
            print(f"Global Comment (Len {len(p.global_comment or '')}):\n{p.global_comment}")
        else:
            print("Participant NOT created.")

        # 2. Second Call: Should append to comment
        payload2 = {
            "responseId": "RESP_002", # different response ID implies new submission usually, or same if update
            "formId": "FORM_001",
            "email": "test@example.com",
            "timestamp": "2026-01-02T12:00:00.000Z",
            "answers": {
                "Question 3": "Nouveau détail"
            }
        }
        
        resp = client.post('/api/webhook/gform', data=json.dumps(payload2), headers=headers)
        print(f"\nResponse 2: {resp.status_code}")
        
        db.session.refresh(p)
        print(f"Global Comment After Update:\n{p.global_comment}")

if __name__ == "__main__":
    test_webhook_update()
