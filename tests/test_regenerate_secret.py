
import pytest
from models import Event, Participant
from constants import ParticipantType, RegistrationStatus

class TestRegenerateSecret:
    """Tests for the regenerate_secret route."""

    def test_regenerate_secret_success(self, client, sample_event, user_creator, db):
        """Test that an organizer can successfully regenerate the webhook secret."""
        # Login as the creator (who is an organizer of sample_event)
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        old_secret = sample_event.webhook_secret
        
        # Make the request
        response = client.post(f'/event/{sample_event.id}/regenerate_secret')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['new_secret'] is not None
        assert data['new_secret'] != old_secret
        
        # Verify database update
        db.session.refresh(sample_event)
        assert sample_event.webhook_secret == data['new_secret']

    def test_regenerate_secret_forbidden_for_pj(self, client, sample_event, user_regular, db):
        """Test that a PJ participant cannot regenerate the secret."""
        # Add user_regular as a PJ
        participant = Participant(
            event_id=sample_event.id,
            user_id=user_regular.id,
            type=ParticipantType.PJ.value,
            registration_status=RegistrationStatus.VALIDATED.value
        )
        db.session.add(participant)
        db.session.commit()
        
        # Login as PJ
        from tests.conftest import login
        login(client, 'user@test.com', 'password123')
        
        # Make the request
        response = client.post(f'/event/{sample_event.id}/regenerate_secret')
        
        # Should be forbidden
        assert response.status_code == 403

    def test_regenerate_secret_forbidden_for_non_participant(self, client, sample_event, user_regular):
        """Test that a non-participant user cannot regenerate the secret."""
        # Login as user_regular (not a participant)
        from tests.conftest import login
        login(client, 'user@test.com', 'password123')
        
        # Make the request
        response = client.post(f'/event/{sample_event.id}/regenerate_secret')
        
        # Should be forbidden
        assert response.status_code == 403

    def test_regenerate_secret_unauthorized(self, client, sample_event):
        """Test that an unauthenticated user cannot access the route."""
        # No login
        
        # Make the request
        response = client.post(f'/event/{sample_event.id}/regenerate_secret')
        
        # Should redirect to login
        assert response.status_code == 302
