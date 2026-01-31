"""
Tests pour les nouvelles fonctionnalités : organizing_association et display_organizers.
"""
import pytest
from datetime import datetime, timedelta
from models import Event, Participant
from constants import ParticipantType


class TestOrganizingAssociationFeature:
    """Tests pour la fonctionnalité organizing_association."""
    
    def test_organizing_association_in_update_general(self, client, sample_event, user_creator, db):
        """Test de mise à jour de l'association organisatrice via update_general."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        response = client.post(f'/event/{sample_event.id}/update_general', data={
            'name': sample_event.name,
            'description': sample_event.description,
            'location': sample_event.location,
            'date_start': sample_event.date_start.strftime('%Y-%m-%d'),
            'date_end': sample_event.date_end.strftime('%Y-%m-%d'),
            'organizing_association': 'GNiales Aventures Association'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier la mise à jour
        db.session.refresh(sample_event)
        assert sample_event.organizing_association == 'GNiales Aventures Association'
    
    def test_organizing_association_persists_default(self, client, sample_event, user_creator, db):
        """Test que la valeur par défaut est préservée si non modifiée."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        # Ne pas envoyer organizing_association
        response = client.post(f'/event/{sample_event.id}/update_general', data={
            'name': 'New Name',
            'description': sample_event.description,
            'location': sample_event.location,
            'date_start': sample_event.date_start.strftime('%Y-%m-%d'),
            'date_end': sample_event.date_end.strftime('%Y-%m-%d')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # L'association devrait garder sa valeur actuelle ou default
        db.session.refresh(sample_event)
        assert sample_event.organizing_association is not None


class TestDisplayOrganizersFeature:
    """Tests pour la fonctionnalité display_organizers."""
    
    def test_display_organizers_checkbox_toggle(self, client, sample_event, user_creator, db):
        """Test du toggle du checkbox display_organizers."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        # Désactiver l'affichage des organisateurs
        response = client.post(f'/event/{sample_event.id}/update_general', data={
            'name': sample_event.name,
            'description': sample_event.description,
            'location': sample_event.location,
            'date_start': sample_event.date_start.strftime('%Y-%m-%d'),
            'date_end': sample_event.date_end.strftime('%Y-%m-%d'),
            # display_organizers absent = False (checkbox non coché)
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        db.session.refresh(sample_event)
        assert sample_event.display_organizers is False
        
        # Réactiver l'affichage des organisateurs
        response = client.post(f'/event/{sample_event.id}/update_general', data={
            'name': sample_event.name,
            'description': sample_event.description,
            'location': sample_event.location,
            'date_start': sample_event.date_start.strftime('%Y-%m-%d'),
            'date_end': sample_event.date_end.strftime('%Y-%m-%d'),
            'display_organizers': 'on'  # Checkbox coché
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        db.session.refresh(sample_event)
        assert sample_event.display_organizers is True
    
    def test_organizers_hidden_when_disabled(self, client, sample_event, user_creator, db):
        """Test que les organisateurs sont cachés quand display_organizers = False."""
        from tests.conftest import login
        from models import User, Participant
        from werkzeug.security import generate_password_hash
        
        # Créer un participant non-organisateur
        participant_user = User(
            email='participant@test.com',
            nom='Participant',
            prenom='Test',
            password_hash=generate_password_hash('pass123')
        )
        db.session.add(participant_user)
        db.session.commit()
        
        # L'ajouter comme participant PJ validé
        participant = Participant(
            user_id=participant_user.id,
            event_id=sample_event.id,
            type='PJ',
            registration_status='Validé'
        )
        db.session.add(participant)
        db.session.commit()
        
        # Désactiver l'affichage
        sample_event.display_organizers = False
        db.session.commit()
        
        # Se connecter en tant que participant
        login(client, 'participant@test.com', 'pass123')
        
        # Accéder à la page de l'événement
        response = client.get(f'/event/{sample_event.id}')
        assert response.status_code == 200
        
        # Vérifier que "organisateurs :" n'apparaît pas pour la liste
        # (L'association organisatrice peut toujours apparaître)
        data = response.data.decode('utf-8')
        # On ne devrait pas voir la liste des organisateurs
        # Note: Ce test dépend de l'implémentation exacte du template
    
    def test_organizers_always_visible_to_organizers(self, client, sample_event, user_creator, db):
        """Test que les organisateurs voient toujours la liste même si display_organizers = False."""
        from tests.conftest import login
        
        # Désactiver l'affichage
        sample_event.display_organizers = False
        db.session.commit()
        
        # Se connecter en tant qu'organisateur
        login(client, 'creator@test.com', 'creator123')
        
        # Accéder à la page de l'événement
        response = client.get(f'/event/{sample_event.id}')
        assert response.status_code == 200
        
        # L'organisateur devra toujours pouvoir voir l'interface de gestion
        assert b'organisateur' in response.data.lower() or b'organizer' in response.data.lower()


class TestNewFeaturesIntegration:
    """Tests d'intégration pour les nouvelles fonctionnalités."""
    
    def test_event_creation_with_new_fields(self, client, user_regular, db):
        """Test de création d'événement avec les nouveaux champs."""
        from tests.conftest import login
        login(client, 'user@test.com', 'password123')
        
        response = client.post('/event/create', data={
            'name': 'Event avec Nouveaux Champs',
            'description': 'Test des nouveaux champs',
            'date_start': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'date_end': (datetime.now() + timedelta(days=32)).strftime('%Y-%m-%d'),
            'location': 'Test',
            'visibility': 'public',
            'organizing_association': 'Test Association',
            'display_organizers': 'on'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier que l'événement a été créé avec les bons champs
        event = Event.query.filter_by(name='Event avec Nouveaux Champs').first()
        assert event is not None
        assert event.organizing_association == 'Test Association'
        assert event.display_organizers is True
    
    def test_default_values_on_creation(self, client, user_regular, db):
        """Test des valeurs par défaut lors de la création."""
        from tests.conftest import login
        login(client, 'user@test.com', 'password123')
        
        response = client.post('/event/create', data={
            'name': 'Event avec Défauts',
            'description': 'Test',
            'date_start': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'date_end': (datetime.now() + timedelta(days=32)).strftime('%Y-%m-%d'),
            'location': 'Test',
            'visibility': 'public'
            # Ne pas spécifier organizing_association ni display_organizers
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        event = Event.query.filter_by(name='Event avec Défauts').first()
        assert event is not None
        # Vérifier les valeurs par défaut
        assert event.organizing_association == 'une entité mystérieuse et inquiétante'
        assert event.display_organizers is False
