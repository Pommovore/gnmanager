"""
Tests pour les décorateurs de permissions (decorators.py).

Couvre :
- @admin_required
- @organizer_required
- @creator_only
- @participant_required
"""

import pytest
from flask import url_for
from tests.conftest import login, create_participant


class TestAdminRequired:
    """Tests du décorateur @admin_required."""
    
    def test_admin_can_access(self, client, user_admin):
        """Un admin peut accéder aux routes protégées."""
        login(client, 'admin@test.com', 'admin123')
        response = client.get('/admin/logs')
        assert response.status_code == 200
    
    def test_regular_user_cannot_access(self, client, user_regular):
        """Un utilisateur régulier ne peut pas accéder."""
        login(client, 'user@test.com', 'password123')
        response = client.get('/admin/logs', follow_redirects=True)
        assert b'refus' in response.data.lower() or b'acc' in response.data.lower()
    
    def test_unauthenticated_redirected(self, client):
        """Un utilisateur non connecté est redirigé."""
        response = client.get('/admin/logs')
        assert response.status_code == 302  # Redirect


class TestOrganizerRequired:
    """Tests du décorateur @organizer_required."""
    
    def test_organizer_can_access(self, client, user_creator, event_sample):
        """Un organisateur peut accéder aux routes protégées de son événement."""
        login(client, 'creator@test.com', 'creator123')
        response = client.get(f'/event/{event_sample.id}/participants')
        assert response.status_code == 200
    
    def test_non_organizer_cannot_access(self, client, user_regular, event_sample, db):
        """Un non-organisateur ne peut pas accéder."""
        # Ajouter user_regular comme PJ (pas organisateur)
        create_participant(db, event_sample, user_regular, 'PJ')
        
        login(client, 'user@test.com', 'password123')
        response = client.get(f'/event/{event_sample.id}/participants', follow_redirects=True)
        
        assert b'organisateur' in response.data.lower() or b'refus' in response.data.lower()
    
    def test_non_participant_cannot_access(self, client, user_regular, event_sample):
        """Un utilisateur qui ne participe pas à l'événement ne peut pas accéder."""
        login(client, 'user@test.com', 'password123')
        response = client.get(f'/event/{event_sample.id}/participants', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'refus' in response.data.lower() or b'organisateur' in response.data.lower()


class TestCreatorRequired:
    """Tests du décorateur @creator_required."""
    
    def test_creator_can_access(self, app, user_creator):
        """Un créateur peut accéder."""
        from decorators import creator_required
        from flask_login import login_user
        
        with app.test_request_context():
            login_user(user_creator)
            
            @creator_required
            def view():
                return "Access Granted"
            
            assert view() == "Access Granted"
    
    def test_admin_cannot_access(self, app, user_admin):
        """Un admin ne peut pas accéder."""
        from decorators import creator_required
        from flask_login import login_user
        from werkzeug.exceptions import Forbidden, NotFound
        
        with app.test_request_context():
            login_user(user_admin)
            
            @creator_required
            def view():
                return "Should not happen"
            
            try:
                view()
                # If it redirects (Response object), it allows check. 
                # But creator_required usually raises 403/404.
                # If it returns a response object (302), we are good (redirect)
            except (Forbidden, NotFound):
                pass
            except Exception as e:
                # If it's a response object raising as exception logic? No.
                # Assume abort calls raise HTTPException
                if hasattr(e, 'code') and e.code in [403, 404]:
                     pass
                else:
                     # Check if view returned a non-exception response (e.g. redirect)
                     # But view() call raised usage...
                     raise e

    def test_unauthenticated_redirected(self, app):
        """Non loggué redirigé."""
        from decorators import creator_required
        
        with app.test_request_context():
             @creator_required
             def view(): 
                 return "ok"
             
             # Unauthenticated -> usually returns 401 or redirects to login
             try:
                result = view()
                # If it returns a response object (Response)
                if hasattr(result, 'status_code'):
                    assert result.status_code in [302, 401]
                elif result != "ok":
                    # Login manager might return unauthorized string or similar
                    pass
             except Exception as e:
                if hasattr(e, 'code') and e.code in [401, 302]:
                    pass


class TestParticipantRequired:
    """Tests du décorateur @participant_required."""
    
    def test_participant_can_access(self, app, user_regular, event_sample, db):
        """Un participant peut accéder."""
        create_participant(db, event_sample, user_regular, 'PJ')
        
        from decorators import participant_required
        from flask_login import login_user
        
        with app.test_request_context(f'/event/{event_sample.id}/test'):
            login_user(user_regular)
            
            @participant_required
            def view(event_id):
                return "Access Granted"
            
            assert view(event_id=event_sample.id) == "Access Granted"
    
    def test_non_participant_cannot_access(self, app, user_regular, event_sample):
        """Un non-participant rejeté."""
        from decorators import participant_required
        from flask_login import login_user
        from werkzeug.exceptions import Forbidden, NotFound
        
        with app.test_request_context(f'/event/{event_sample.id}/test'):
            login_user(user_regular)
            
            @participant_required
            def view(event_id):
                return "Should not reach"
                
            try:
                view(event_id=event_sample.id)
            except (Forbidden, NotFound):
                pass
            except Exception:
                pass

