
import pytest
from app import create_app, db
from models import User, Event, Role

@pytest.fixture
def app():
    app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'SECRET_KEY': 'test'})
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_template_present(client, app):
    with app.app_context():
        db.drop_all()
        db.create_all()
        u = User(email='test@test.com', role='sysadmin')
        db.session.add(u)
        e = Event(name="Test Render", date_start=db.func.now(), date_end=db.func.now())
        db.session.add(e)
        db.session.commit()
        
        # Add organizer participant
        from models import Participant
        # status and type usage depends on model definition, assuming common values from previous files
        p = Participant(event_id=e.id, user_id=u.id, type='Organisateur', registration_status='Validé')
        db.session.add(p)
        db.session.commit()
        
        with client.session_transaction() as sess:
            sess['_user_id'] = str(u.id)
            sess['_fresh'] = True
            
        resp = client.get(f'/event/{e.id}/casting')
        print(f"STATUS CODE: {resp.status_code}")
        if resp.status_code == 302:
            print(f"REDIRECT TO: {resp.headers.get('Location')}")
        content = resp.data.decode('utf-8')
        
        print("\n--- CONTENT CHECK ---")
        if 'id="casting-content-template"' in content:
            print("FOUND TEMPLATE")
        else:
            print("NOT FOUND TEMPLATE")
            
        if 'js/casting.js' in content:
            print("FOUND SCRIPT")
            if content.find('js/casting.js') > content.find('id="casting-content-template"'):
                print("SCRIPT AFTER TEMPLATE")
            else:
                print("SCRIPT BEFORE TEMPLATE")
