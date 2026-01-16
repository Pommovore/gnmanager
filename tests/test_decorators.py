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


class TestCreatorOnly:
    """Tests du décorateur @creator_only (si implémenté)."""
    
    def test_creator_can_access_creator_only_routes(self, client, user_creator):
        """Le créateur peut accéder aux routes réservées."""
        login(client, 'creator@test.com', 'creator123')
        # Tester une route réservée au créateur si elle existe
        # Par exemple, promouvoir quelqu'un en créateur
        pass  # À implémenter si nécessaire
    
    def test_admin_cannot_access_creator_only(self, client, user_admin):
        """Un admin ne peut pas accéder aux routes réservées au créateur."""
        login(client, 'admin@test.com', 'admin123')
        # Tester le blocage
        pass  # À implémenter si nécessaire


class TestParticipantRequired:
    """Tests du décorateur @participant_required (si implémenté)."""
    
    def test_participant_can_access(self, client, user_regular, event_sample, db):
        """Un participant peut accéder aux routes protégées."""
        create_participant(db, event_sample, user_regular, 'PJ')
        
        login(client, 'user@test.com', 'password123')
        response = client.get(f'/event/{event_sample.id}')
        assert response.status_code == 200
    
    def test_non_participant_cannot_access(self, client, user_regular, event_sample):
        """Un non-participant ne peut pas accéder."""
        login(client, 'user@test.com', 'password123')
        # Tentative d'accès à une route réservée aux participants
        # Dépend de l'implémentation exacte
        pass  # À compléter selon l'implémentation
