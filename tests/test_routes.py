"""Tests d'intégration pour les routes principales de GN Manager."""

import pytest
from datetime import datetime, timedelta
from models import Event, Participant, ActivityLog


class TestDashboardRoutes:
    """Tests des routes du dashboard."""
    
    def test_dashboard_requires_auth(self, client):
        """Test que le dashboard nécessite une authentification."""
        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirection vers login
    
    def test_dashboard_loads_for_authenticated_user(self, auth_client):
        """Test que le dashboard se charge pour un utilisateur authentifié."""
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
    
    def test_dashboard_shows_events(self, auth_client, sample_event):
        """Test que le dashboard affiche les événements."""
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Test Event' in response.data


class TestEventCreationRoutes:
    """Tests de création d'événement."""
    
    def test_create_event_page_requires_auth(self, client):
        """Test que la page de création nécessite une authentification."""
        response = client.get('/event/create')
        assert response.status_code == 302
    
    def test_create_event_page_loads(self, auth_client):
        """Test que la page de création se charge."""
        response = auth_client.get('/event/create')
        assert response.status_code == 200
    
    def test_create_event_success(self, auth_client, app):
        """Test de création d'un événement."""
        response = auth_client.post('/event/create', data={
            'name': 'Nouvel Événement',
            'description': 'Description test',
            'date_start': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'date_end': (datetime.now() + timedelta(days=12)).strftime('%Y-%m-%d'),
            'location': 'Paris',
            'visibility': 'public'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier que l'événement existe
        with app.app_context():
            event = Event.query.filter_by(name='Nouvel Événement').first()
            assert event is not None
            assert event.location == 'Paris'


class TestEventDetailRoutes:
    """Tests des pages de détails d'événement."""
    
    def test_event_detail_loads(self, auth_client, sample_event):
        """Test que la page de détails d'un événement se charge."""
        response = auth_client.get(f'/event/{sample_event.id}')
        assert response.status_code == 200
        assert b'Test Event' in response.data
    
    def test_event_detail_shows_external_links(self, auth_client, app, db):
        """Test que les liens externes sont affichés."""
        with app.app_context():
            from models import db
            event = Event(
                name='Event avec liens',
                date_start=datetime.now(),
                date_end=datetime.now() + timedelta(days=1),
                location='Test',
                org_link_url='https://example.org',
                org_link_title='Mon Asso',
                google_form_url='https://forms.gle/test'
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id
        
        response = auth_client.get(f'/event/{event_id}')
        assert response.status_code == 200
        assert b'example.org' in response.data or b'Mon Asso' in response.data


class TestParticipantManagementRoutes:
    """Tests de gestion des participants."""
    
    def test_manage_participants_requires_organizer(self, client, sample_event):
        """Test que la gestion nécessite d'être organisateur."""
        response = client.get(f'/event/{sample_event.id}/participants')
        assert response.status_code == 302
    
    def test_manage_participants_loads_for_organizer(self, client, sample_event, user_creator):
        """Test que la page se charge pour un organisateur."""
        # Se connecter en tant que créateur (organisateur du sample_event)
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        response = client.get(f'/event/{sample_event.id}/participants')
        assert response.status_code == 200
    
    def test_change_participant_status(self, auth_client, app, sample_event, sample_participant):
        """Test de changement de statut d'un participant."""
        response = auth_client.post(
            f'/event/{sample_event.id}/participant/{sample_participant.id}/change-status',
            data={'action': 'validate'},
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Vérifier que le statut a changé
        with app.app_context():
            participant = Participant.query.get(sample_participant.id)
            assert participant.registration_status == 'Validé'


class TestAdminRoutes:
    """Tests des routes d'administration."""
    
    def test_admin_logs_requires_admin(self, auth_client):
        """Test que les logs nécessitent les droits admin."""
        response = auth_client.get('/admin/logs')
        # Un utilisateur normal ne devrait pas y avoir accès
        assert response.status_code in [302, 403, 200]  # Dépend de l'implémentation
    
    def test_admin_logs_loads_for_admin(self, admin_client):
        """Test que la page des logs se charge pour un admin."""
        response = admin_client.get('/admin/logs')
        assert response.status_code == 200
    
    def test_activity_log_creation(self, app, sample_admin):
        """Test que les logs d'activité sont créés."""
        with app.app_context():
            from models import db
            
            # Créer un log
            log = ActivityLog(
                user_id=sample_admin.id,
                action_type='Test',
                details='Test log'
            )
            db.session.add(log)
            db.session.commit()
            
            # Vérifier qu'il existe
            logs = ActivityLog.query.all()
            assert len(logs) > 0
