
import pytest
from app import create_app, db
from models import User, Event, Participant, Role
from datetime import datetime
from flask import url_for

@pytest.fixture
def app():
    app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'SECRET_KEY': 'test'})
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

def test_casting_data_error(client, app):
    with app.app_context():
        # Setup data
        db.drop_all()
        db.create_all()
        
        # Create organizer user
        user = User(email='admin@test.com', nom='Admin', prenom='User', role='sysadmin')
        user.password_hash = 'hash'
        db.session.add(user)
        db.session.commit()
        
        # Create event
        event = Event(name="Test Event", date_start=datetime.now(), date_end=datetime.now(), location="Test")
        db.session.add(event)
        db.session.commit()
        
        # Create Participation (Organizer)
        part = Participant(event_id=event.id, user_id=user.id, type='Organisateur', registration_status='Validé')
        db.session.add(part)
        db.session.commit()
        
        # Create Role
        role = Role(event_id=event.id, name="Test Role", type="PJ", genre="Homme")
        db.session.add(role)
        db.session.commit()
        
        event_id = event.id
        user_id = user.id
        
        # Create Proposal and Assignment
        from models import CastingProposal, CastingAssignment
        proposal = CastingProposal(event_id=event_id, name="Prop 1")
        db.session.add(proposal)
        db.session.commit()
        
        assignment = CastingAssignment(proposal_id=proposal.id, role_id=role.id, participant_id=part.id, score=8, event_id=event_id)
        db.session.add(assignment)
        db.session.commit()
        user_id = user.id

    # Login
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True

    # Request
    print(f"Requesting /event/{event_id}/casting_data")
    response = client.get(f'/event/{event_id}/casting_data')
    
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print("Response Text:")
        print(response.text)
        
    assert response.status_code == 200
