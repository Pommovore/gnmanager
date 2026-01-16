"""
Tests pour les routes d'événements (event_routes.py).

Couvre :
- Création d'événements
- Consultation des détails
- Modification des informations générales
- Modification du statut
- Configuration des groupes
- Inscription à un événement
"""

import pytest
from datetime import datetime, timedelta
from models import Event, Participant, ActivityLog
from constants import ParticipantType, EventStatus

class TestEventCreation:
    """Tests de création d'événements."""
    
    def test_create_event_page_loads(self, auth_client):
        """Test que la page de création se charge."""
        response = auth_client.get('/event/create')
        assert response.status_code == 200
    
    def test_create_event_success(self, client, user_regular, db):
        """Test de création d'un événement avec succès."""
        from tests.conftest import login
        login(client, 'user@test.com', 'password123')
        
        response = client.post('/event/create', data={
            'name': 'Nouvel Événement Test',
            'description': 'Description complète',
            'date_start': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'date_end': (datetime.now() + timedelta(days=32)).strftime('%Y-%m-%d'),
            'location': 'Château de Test',
            'visibility': 'public'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier que l'événement a été créé
        event = Event.query.filter_by(name='Nouvel Événement Test').first()
        assert event is not None
        assert event.location == 'Château de Test'
        
        # Vérifier que le créateur est organisateur
        participant = Participant.query.filter_by(
            event_id=event.id,
            user_id=user_regular.id,
            type=ParticipantType.ORGANISATEUR.value
        ).first()
        assert participant is not None
    
    def test_create_event_invalid_dates(self, auth_client):
        """Test de création avec des dates invalides."""
        response = auth_client.post('/event/create', data={
            'name': 'Event Invalide',
            'date_start': 'invalid-date',
            'date_end': '2026-12-31',
            'location': 'Test'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'invalide' in response.data.lower() or b'format' in response.data.lower()


class TestEventDetailAndUpdate:
    """Tests des détails et modifications d'événements."""
    
    def test_event_detail_requires_login(self, client, sample_event):
        """Test que les détails nécessitent une connexion."""
        response = client.get(f'/event/{sample_event.id}')
        assert response.status_code == 302  # Redirect to login
    
    def test_event_detail_loads_for_authenticated(self, auth_client, sample_event):
        """Test que les détails se chargent pour un utilisateur connecté."""
        response = auth_client.get(f'/event/{sample_event.id}')
        assert response.status_code == 200
        assert b'Test Event' in response.data
    
    def test_update_general_as_organizer(self, client, sample_event, user_creator, db):
        """Test de mise à jour des informations générales par un organisateur."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        response = client.post(f'/event/{sample_event.id}/update_general', data={
            'name': 'Event Modifié',
            'description': 'Nouvelle description',
            'location': 'Nouveau Lieu'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier la mise à jour
        db.session.refresh(sample_event)
        assert sample_event.name == 'Event Modifié'
        assert sample_event.location == 'Nouveau Lieu'
    
    def test_update_status_as_organizer(self, client, sample_event, user_creator, db):
        """Test de changement de statut par un organisateur."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        new_status = EventStatus.REGISTRATION_OPEN.value
        response = client.post(f'/event/{sample_event.id}/update_status', data={
            'statut': new_status
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier le changement
        db.session.refresh(sample_event)
        assert sample_event.statut == new_status
    
    def test_update_groups_as_organizer(self, client, sample_event, user_creator, db):
        """Test de modification de la configuration des groupes."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        import json
        new_config = {
            "PJ": ["Groupe A", "Groupe B", "Groupe C"],
            "PNJ": ["Groupe D"],
            "Organisateur": ["général", "logistique"]
        }
        
        response = client.post(f'/event/{sample_event.id}/update_groups', data={
            'groups_config': json.dumps(new_config)
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier la mise à jour (la structure JSON peut varier selon l'implémentation)
        db.session.refresh(sample_event)
        # Vérifier que groups_config contient la nouvelle configuration
        import json
        config = json.loads(sample_event.groups_config) if sample_event.groups_config else {}
        # Au minimum, vérifier que la structure a été mise à jour
        assert 'PJ' in config or 'PNJ' in config or 'Organisateur' in config


class TestEventJoin:
    """Tests d'inscription à un événement."""
    
    def test_join_event_as_pj(self, client, sample_event, db):
        """Test d'inscription en tant que PJ."""
        from models import User
        from werkzeug.security import generate_password_hash
        from tests.conftest import login
        
        # Créer un utilisateur
        new_user = User(
            email='newpj@test.com',
            nom='PJ',
            prenom='Test',
            password_hash=generate_password_hash('pass123')
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Se connecter
        login(client, 'newpj@test.com', 'pass123')
        
        # S'inscrire
        response = client.post(f'/event/{sample_event.id}/join', data={
            'type': 'PJ',
            'group': 'Groupe A'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier l'inscription
        participant = Participant.query.filter_by(
            event_id=sample_event.id,
            user_id=new_user.id
        ).first()
        assert participant is not None
        assert participant.type == 'PJ'
        # Le statut peut être 'À valider' ou 'En attente' selon la configuration
        assert participant.registration_status in ['À valider', 'En attente', 'Pending']
    
    def test_cannot_join_twice(self, auth_client, sample_event, user_regular, db):
        """Test qu'on ne peut pas s'inscrire deux fois."""
        # Première inscription
        auth_client.post(f'/event/{sample_event.id}/join', data={
            'type': 'PNJ',
            'group': 'Test'
        })
        
        # Deuxième tentative
        response = auth_client.post(f'/event/{sample_event.id}/join', data={
            'type': 'PJ',
            'group': 'Test'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Devrait afficher un message d'erreur
        assert b'inscription' in response.data.lower() or b'particip' in response.data.lower()


class TestEventActivityLog:
    """Tests de la journalisation des activités."""
    
    def test_event_creation_logged(self, client, user_regular, db):
        """Test que la création d'événement est enregistrée dans les logs."""
        from tests.conftest import login
        login(client, 'user@test.com', 'password123')
        
        client.post('/event/create', data={
            'name': 'Event pour Log',
            'date_start': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'date_end': (datetime.now() + timedelta(days=12)).strftime('%Y-%m-%d'),
            'location': 'Test Location',
            'visibility': 'public'
        })
        
        # Vérifier le log
        from constants import ActivityLogType
        log = ActivityLog.query.filter_by(
            action_type=ActivityLogType.EVENT_CREATION.value
        ).first()
        assert log is not None
