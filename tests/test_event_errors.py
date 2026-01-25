"""
Tests for Event error scenarios.

Covers:
- Event creation errors
- Update errors (not found, permission denied, invalid data)
- Delete errors
- Join errors
"""

import pytest
from models import Event, Participant
from constants import ParticipantType

class TestEventErrors:
    
    def test_update_nonexistent_event(self, client, user_creator):
        """Test authentication required for non-existent event update."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        response = client.post('/event/99999/update_general', data={
            'name': 'Ghost Event'
        }, follow_redirects=True)
        
        # Should be 404
        assert response.status_code == 404
    
    def test_delete_nonexistent_event(self, client, user_creator):
        """Test deleting non-existent event."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        response = client.post('/event/99999/delete', follow_redirects=True)
        assert response.status_code == 404

    def test_unauthorized_update(self, client, sample_event, db):
        """Test non-organizer cannot update event."""
        from models import User
        from werkzeug.security import generate_password_hash
        from tests.conftest import login
        
        # Create a user who is NOT organizer
        hacker = User(email='hacker@test.com', nom='Hacker', prenom='Hack', password_hash=generate_password_hash('pass'))
        db.session.add(hacker)
        db.session.commit()
        
        login(client, 'hacker@test.com', 'pass')
        
        response = client.post(f'/event/{sample_event.id}/update_general', data={
            'name': 'Hacked Event'
        }, follow_redirects=True)
        
        # Should be 403 or redirect with flash message saying unauthorized
        # Based on implementation, usually redirects to detail or dashboard
        # Let's verify status code is OK but change didn't happen
        assert response.status_code in [200, 302, 403]
        
        # Verify NO change
        db.session.refresh(sample_event)
        assert sample_event.name != 'Hacked Event'
    
    def test_invalid_date_update(self, client, sample_event, user_creator, db):
        """Test updating event with invalid dates (end < start)."""
        from tests.conftest import login
        from datetime import datetime, timedelta
        login(client, 'creator@test.com', 'creator123')
        
        start = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')
        end_invalid = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
        
        response = client.post(f'/event/{sample_event.id}/update_general', data={
            'name': 'Bad Dates',
            'date_start': start,
            'date_end': end_invalid,
            'location': 'Nowhere'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Check for the actual error message we implemented
        assert b'interieure' in response.data.lower() or b'anterieure' in response.data.lower() or b'date de fin' in response.data.lower()
        
        db.session.refresh(sample_event)
        assert sample_event.name != 'Bad Dates'

    def test_join_nonexistent_event(self, auth_client):
        """Test joining a ghost event."""
        response = auth_client.post('/event/99999/join', data={'type': 'PJ'})
        assert response.status_code == 404

    def test_casting_access_denied(self, client, sample_event, db):
        """Test non-organizer cannot access casting."""
        from models import User, Role
        from werkzeug.security import generate_password_hash
        from tests.conftest import login
        
        # Regular user
        login(client, 'user@test.com', 'password123')
        
        routes = [
            f'/event/{sample_event.id}/casting_data',
            f'/event/{sample_event.id}/casting/auto_assign'
        ]
        
        for route in routes:
            response = client.get(route) if 'data' in route else client.post(route)
            # Accept 403 (Forbidden) or 302 (Redirect to login)
            assert response.status_code in [403, 302]
            if response.status_code == 302:
                # If redirected, it should preserve the next parameter typically
                pass
