import pytest
import json
from datetime import datetime
from models import GFormsCategory, GFormsSubmission, GFormsFieldMapping, User, Participant, Event, FormResponse
from constants import ParticipantType

def test_gforms_category_model(db, event_sample):
    """Test GFormsCategory model creation and defaults."""
    category = GFormsCategory(
        event_id=event_sample.id,
        name="Test Category",
        color="blue",
        position=1
    )
    db.session.add(category)
    db.session.commit()
    
    assert category.id is not None
    assert category.name == "Test Category"
    assert category.color == "blue"
    assert category.position == 1
    
    # Test defaults
    default_cat = GFormsCategory(event_id=event_sample.id, name="Default")
    db.session.add(default_cat)
    db.session.commit()
    assert default_cat.color == "neutral"
    assert default_cat.position == 0

def test_gforms_mapping_uniqueness(db, event_sample):
    """Test that field mappings must be unique per event/field."""
    from sqlalchemy.exc import IntegrityError
    
    cat = GFormsCategory(event_id=event_sample.id, name="Cat 1")
    db.session.add(cat)
    db.session.commit()
    
    m1 = GFormsFieldMapping(event_id=event_sample.id, field_name="Field A", category_id=cat.id)
    db.session.add(m1)
    db.session.commit()
    
    m2 = GFormsFieldMapping(event_id=event_sample.id, field_name="Field A", category_id=cat.id)
    db.session.add(m2)
    
    with pytest.raises(IntegrityError):
        db.session.commit()
    
    db.session.rollback()

def test_webhook_processing(client, db, event_sample):
    """Test full webhook processing flow."""
    # Setup event secret
    secret = "test_webhook_secret_123"
    event_sample.webhook_secret = secret
    db.session.commit()
    
    payload = {
        "responseId": "RESP_12345",
        "formId": "FORM_ABC",
        "email": "new.user@test.com",
        "timestamp": "2024-01-01T12:00:00.000Z",
        "answers": {
            "Prénom": "Jean",
            "Nom": "Dupont",
            "Régime": "Végétarien"
        }
    }
    
    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json"
    }
    
    response = client.post('/api/webhook/gform', data=json.dumps(payload), headers=headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["action"] == "created"
    
    # Verify User creation
    user = User.query.filter_by(email="new.user@test.com").first()
    assert user is not None
    
    # Verify Participant creation
    participant = Participant.query.filter_by(user_id=user.id, event_id=event_sample.id).first()
    assert participant is not None
    assert "Prénom: Jean" in participant.global_comment
    
    # Verify GFormsSubmission
    submission = GFormsSubmission.query.filter_by(event_id=event_sample.id, email="new.user@test.com").first()
    assert submission is not None
    assert submission.type_ajout == "créé"
    raw = json.loads(submission.raw_data)
    assert raw["Régime"] == "Végétarien"
    
    # Verify Auto-Mapping of fields
    mappings = GFormsFieldMapping.query.filter_by(event_id=event_sample.id).all()
    fields = [m.field_name for m in mappings]
    assert "Prénom" in fields
    assert "Nom" in fields
    assert "Régime" in fields
    
    # Check default category creation
    default_cat = GFormsCategory.query.filter_by(event_id=event_sample.id, name="Généralités").first()
    assert default_cat is not None
    assert mappings[0].category_id == default_cat.id

def test_organizer_routes_access(client, db, event_sample, user_regular, user_creator):
    """Test access control for GForms routes."""
    # Setup
    event_sample.webhook_secret = "secret"
    db.session.commit()
    
    # 1. Anonymous -> Redirect to login
    resp = client.get(f'/event/{event_sample.id}/gforms')
    assert resp.status_code == 302
    
    # 2. Regular User (not participant) -> 403 or redirect depending on check
    # Actually @organizer_required usually returns 403 or redirects to home
    from tests.conftest import login
    login(client, 'user@test.com', 'password123')
    resp = client.get(f'/event/{event_sample.id}/gforms')
    # Depending on implementation of organizer_required, likely 403
    assert resp.status_code == 403
    
    # 3. Organizer (Creator) -> 200
    login(client, 'creator@test.com', 'creator123')
    resp = client.get(f'/event/{event_sample.id}/gforms')
    assert resp.status_code == 200
