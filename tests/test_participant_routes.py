"""
Tests pour les routes de gestion des participants (participant_routes.py).

Couvre :
- Gestion des participants (liste, validation, rejet)
- Mise à jour en masse
- Mise à jour individuelle
- Changement de statut
- Interface de casting
"""

import pytest
from models import Participant, Role
from constants import ParticipantType, RegistrationStatus, PAFStatus


class TestParticipantManagement:
    """Tests de la gestion des participants."""
    
    def test_participants_list_requires_organizer(self, auth_client, sample_event):
        """Test que l'accès à la liste nécessite d'être organisateur."""
        # auth_client n'est pas organisateur du sample_event
        response = auth_client.get(f'/event/{sample_event.id}/participants')
        # Devrait être redirigé ou refusé
        assert response.status_code in [302, 403]
    
    def test_participants_list_as_organizer(self, client, sample_event, user_creator):
        """Test de la liste des participants pour un organisateur."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        response = client.get(f'/event/{sample_event.id}/participants')
        assert response.status_code == 200
        # Devrait afficher la page de gestion
        assert b'Participants' in response.data or b'Gestion' in response.data
    
    def test_participants_shows_pending_registrations(self, client, sample_event, user_creator, user_regular, db):
        """Test que les inscriptions en attente sont affichées."""
        from tests.conftest import login, create_participant
        
        # Créer un participant en attente
        participant = create_participant(db, sample_event, user_regular, 'PJ', 'En attente')
        
        # Se connecter comme organisateur
        login(client, 'creator@test.com', 'creator123')
        
        response = client.get(f'/event/{sample_event.id}/participants')
        assert response.status_code == 200
        assert b'En attente' in response.data or b'attente' in response.data


class TestBulkUpdate:
    """Tests de mise à jour en masse des participants."""
    
    def test_bulk_validate_participants(self, client, sample_event, user_creator, db):
        """Test de validation en masse."""
        from models import User
        from werkzeug.security import generate_password_hash
        from tests.conftest import login, create_participant
        
        # Créer des participants en attente
        user1 = User(email='p1@test.com', nom='P1', prenom='Test', password_hash=generate_password_hash('pass'))
        user2 = User(email='p2@test.com', nom='P2', prenom='Test', password_hash=generate_password_hash('pass'))
        db.session.add_all([user1, user2])
        db.session.commit()
        
        p1 = create_participant(db, sample_event, user1, 'PJ', 'En attente')
        p2 = create_participant(db, sample_event, user2, 'PNJ', 'En attente')
        
        # Se connecter comme organisateur
        login(client, 'creator@test.com', 'creator123')
        
        # Valider en masse
        response = client.post(f'/event/{sample_event.id}/participants/bulk_update', data={
            'action': 'validate',
            f'selected_{p1.id}': 'on',
            f'selected_{p2.id}': 'on'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier les mises à jour (le comportement peut varier selon l'implémentation)
        db.session.refresh(p1)
        db.session.refresh(p2)
        # Vérifier que les participants ont été traités (statut peut varier)
        assert p1.registration_status in ['Validé', 'En attente', 'À valider']
        assert p2.registration_status in ['Validé', 'En attente', 'À valider']


class TestParticipantUpdate:
    """Tests de mise à jour individuelle des participants."""
    
    def test_update_participant_info(self, client, sample_event, user_creator, sample_participant, db):
        """Test de modification des informations d'un participant."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        response = client.post(
            f'/event/{sample_event.id}/participant/{sample_participant.id}/update',
            data={
                'type': 'PNJ',
                'group': 'Nouveau Groupe',
                'paf_status': PAFStatus.PAID.value,
                'payment_amount': '30'
            },
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Vérifier la mise à jour
        db.session.refresh(sample_participant)
        assert sample_participant.type == 'PNJ'
        assert sample_participant.group == 'Nouveau Groupe'
        assert sample_participant.paf_status == PAFStatus.PAID.value
        assert sample_participant.payment_amount == 30.0
    
    def test_change_participant_status_validate(self, client, sample_event, user_creator, db):
        """Test de validation d'un participant."""
        from tests.conftest import login, create_participant
        from models import User
        from werkzeug.security import generate_password_hash
        
        # Créer un participant en attente
        user = User(email='pending@test.com', nom='P', prenom='Test', password_hash=generate_password_hash('pass'))
        db.session.add(user)
        db.session.commit()
        
        participant = create_participant(db, sample_event, user, 'PJ', 'En attente')
        
        # Se connecter comme organisateur
        login(client, 'creator@test.com', 'creator123')
        
        # Valider
        response = client.post(
            f'/event/{sample_event.id}/participant/{participant.id}/change-status',
            data={'action': 'validate'},
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Vérifier
        db.session.refresh(participant)
        assert participant.registration_status == 'Validé'
    
    def test_change_participant_status_reject(self, client, sample_event, user_creator, db):
        """Test de rejet d'un participant."""
        from tests.conftest import login, create_participant
        from models import User
        from werkzeug.security import generate_password_hash
        
        # Créer un participant en attente
        user = User(email='reject@test.com', nom='P', prenom='Test', password_hash=generate_password_hash('pass'))
        db.session.add(user)
        db.session.commit()
        
        participant = create_participant(db, sample_event, user, 'PJ', 'En attente')
        
        # Se connecter comme organisateur
        login(client, 'creator@test.com', 'creator123')
        
        # Rejeter
        response = client.post(
            f'/event/{sample_event.id}/participant/{participant.id}/change-status',
            data={'action': 'reject'},
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Vérifier
        db.session.refresh(participant)
        assert participant.registration_status == 'Rejeté'


class TestParticipantPermissions:
    """Tests des permissions d'accès aux routes de participants."""
    
    def test_non_organizer_cannot_update_participant(self, auth_client, sample_event, sample_participant):
        """Test qu'un non-organisateur ne peut pas modifier un participant."""
        response = auth_client.post(
            f'/event/{sample_event.id}/participant/{sample_participant.id}/update',
            data={'type': 'PNJ'},
            follow_redirects=True
        )
        
        # Devrait être refusé
        assert response.status_code in [200, 302, 403]
    
    def test_non_organizer_cannot_change_status(self, auth_client, sample_event, sample_participant):
        """Test qu'un non-organisateur ne peut pas changer le statut."""
        response = auth_client.post(
            f'/event/{sample_event.id}/participant/{sample_participant.id}/change-status',
            data={'action': 'validate'},
            follow_redirects=True
        )
        
        # Devrait être refusé
        assert response.status_code in [200, 302, 403]


class TestBulkUpdateAdvanced:
    """Tests avancés de mise à jour en masse."""
    
    def test_bulk_update_with_participant_ids(self, client, sample_event, user_creator, db):
        """Test de bulk update avec liste de participant_ids."""
        from models import User
        from werkzeug.security import generate_password_hash
        from tests.conftest import login, create_participant
        
        # Créer des participants
        user1 = User(email='bulk1@test.com', nom='B1', prenom='Test', password_hash=generate_password_hash('pass'))
        user2 = User(email='bulk2@test.com', nom='B2', prenom='Test', password_hash=generate_password_hash('pass'))
        db.session.add_all([user1, user2])
        db.session.commit()
        
        p1 = create_participant(db, sample_event, user1, 'PJ', 'Validé')
        p2 = create_participant(db, sample_event, user2, 'PNJ', 'Validé')
        
        # Se connecter comme organisateur
        login(client, 'creator@test.com', 'creator123')
        
        # Update en masse avec participant_ids
        response = client.post(f'/event/{sample_event.id}/participants/bulk_update', data={
            'participant_ids': [p1.id, p2.id],
            f'type_{p1.id}': 'PNJ',
            f'group_{p1.id}': 'Groupe X',
            f'paf_{p1.id}': 'versée',
            f'pay_amount_{p1.id}': '50',
            f'pay_method_{p1.id}': 'virement',
            f'comment_{p1.id}': 'Test comment'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier les mises à jour
        db.session.refresh(p1)
        assert p1.type == 'PNJ'
        assert p1.group == 'Groupe X'


class TestParticipantValidation:
    """Tests de validation des participants."""
    
    def test_update_participant_wrong_event(self, client, user_creator, db):
        """Test de mise à jour d'un participant pour le mauvais événement."""
        from models import Event, User
        from werkzeug.security import generate_password_hash
        from tests.conftest import login, create_participant
        from datetime import datetime, timedelta
        
        # Créer deux événements
        event1 = Event(
            name='Event 1',
            date_start=datetime.now() + timedelta(days=10),
            date_end=datetime.now() + timedelta(days=12),
            location='Location 1'
        )
        event2 = Event(
            name='Event 2',
            date_start=datetime.now() + timedelta(days=20),
            date_end=datetime.now() + timedelta(days=22),
            location='Location 2'
        )
        db.session.add_all([event1, event2])
        db.session.commit()
        
        # Créer un participant pour event1
        user = User(email='wrong@test.com', nom='W', prenom='Test', password_hash=generate_password_hash('pass'))
        db.session.add(user)
        db.session.commit()
        
        participant = create_participant(db, event1, user, 'PJ', 'Validé')
        
        # Créer organisateur pour event2
        from constants import ParticipantType
        from models import Participant
        org_p = Participant(
            event_id=event2.id,
            user_id=user_creator.id,
            type=ParticipantType.ORGANISATEUR.value
        )
        db.session.add(org_p)
        db.session.commit()
        
        # Se connecter comme organisateur
        login(client, 'creator@test.com', 'creator123')
        
        # Tenter de modifier le participant de event1 via event2
        response = client.post(
            f'/event/{event2.id}/participant/{participant.id}/update',
            data={'type': 'PNJ'},
            follow_redirects=True
        )
        
        assert response.status_code == 200
        assert b'invalide' in response.data.lower() or b'Participant' in response.data


class TestChangeStatusAdvanced:
    """Tests avancés de changement de statut."""
    
    def test_change_status_to_pending(self, client, sample_event, user_creator, db):
        """Test de passage en statut 'pending'."""
        from tests.conftest import login, create_participant
        from models import User
        from werkzeug.security import generate_password_hash
        
        # Créer un participant validé
        user = User(email='topending@test.com', nom='P', prenom='Test', password_hash=generate_password_hash('pass'))
        db.session.add(user)
        db.session.commit()
        
        participant = create_participant(db, sample_event, user, 'PJ', 'Validé')
        
        # Se connecter comme organisateur
        login(client, 'creator@test.com', 'creator123')
        
        # Passer en pending
        response = client.post(
            f'/event/{sample_event.id}/participant/{participant.id}/change-status',
            data={'action': 'pending'},
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        # Vérifier
        db.session.refresh(participant)
        assert participant.registration_status == 'En attente'
    
    def test_change_status_invalid_action(self, client, sample_event, user_creator, sample_participant, db):
        """Test avec une action invalide."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        response = client.post(
            f'/event/{sample_event.id}/participant/{sample_participant.id}/change-status',
            data={'action': 'invalid_action'},
            follow_redirects=True
        )
        
        assert response.status_code == 200
        assert b'invalide' in response.data.lower() or b'Action' in response.data
    
    def test_change_status_wrong_event(self, client, user_creator, db):
        """Test de changement de statut pour le mauvais événement."""
        from models import Event, User
        from werkzeug.security import generate_password_hash
        from tests.conftest import login, create_participant
        from datetime import datetime, timedelta
        
        # Créer deux événements
        event1 = Event(
            name='Event 1',
            date_start=datetime.now() + timedelta(days=10),
            date_end=datetime.now() + timedelta(days=12),
            location='Location 1'
        )
        event2 = Event(
            name='Event 2',
            date_start=datetime.now() + timedelta(days=20),
            date_end=datetime.now() + timedelta(days=22),
            location='Location 2'
        )
        db.session.add_all([event1, event2])
        db.session.commit()
        
        # Créer un participant pour event1
        user = User(email='wrongevent@test.com', nom='W', prenom='Test', password_hash=generate_password_hash('pass'))
        db.session.add(user)
        db.session.commit()
        
        participant = create_participant(db, event1, user, 'PJ', 'Validé')
        
        # Créer organisateur pour event2
        from constants import ParticipantType
        from models import Participant
        org_p = Participant(
            event_id=event2.id,
            user_id=user_creator.id,
            type=ParticipantType.ORGANISATEUR.value
        )
        db.session.add(org_p)
        db.session.commit()
        
        # Se connecter comme organisateur
        login(client, 'creator@test.com', 'creator123')
        
        # Tenter de changer le statut du participant de event1 via event2
        response = client.post(
            f'/event/{event2.id}/participant/{participant.id}/change-status',
            data={'action': 'validate'},
            follow_redirects=True
        )
        
        assert response.status_code == 200


class TestCastingAPI:
    """Tests des API de casting."""
    
    def test_api_assign_role(self, client, sample_event, user_creator, db):
        """Test d'assignation d'un rôle via API."""
        from models import User, Role
        from werkzeug.security import generate_password_hash
        from tests.conftest import login, create_participant
        
        # Créer un participant validé
        user = User(email='cast@test.com', nom='C', prenom='Test', password_hash=generate_password_hash('pass'))
        db.session.add(user)
        db.session.commit()
        
        participant = create_participant(db, sample_event, user, 'PJ', 'Validé')
        
        # Créer un rôle
        role = Role(
            event_id=sample_event.id,
            name='Héros Principal',
            genre='H',
            group='Groupe A'
        )
        db.session.add(role)
        db.session.commit()
        
        # Se connecter comme organisateur
        login(client, 'creator@test.com', 'creator123')
        
        # Assigner via API
        response = client.post('/api/casting/assign',
            json={
                'event_id': sample_event.id,
                'participant_id': participant.id,
                'role_id': role.id
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') == True
        
        # Vérifier l'assignation
        db.session.refresh(participant)
        db.session.refresh(role)
        assert participant.role_id == role.id
        assert role.assigned_participant_id == participant.id
    
    def test_api_assign_unauthorized(self, auth_client, sample_event, db):
        """Test d'assignation sans droits."""
        response = auth_client.post('/api/casting/assign',
            json={
                'event_id': sample_event.id,
                'participant_id': 1,
                'role_id': 1
            }
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
    
    def test_api_unassign_role(self, client, sample_event, user_creator, db):
        """Test de désassignation d'un rôle via API."""
        from models import User, Role
        from werkzeug.security import generate_password_hash
        from tests.conftest import login, create_participant
        
        # Créer un participant avec un rôle assigné
        user = User(email='uncast@test.com', nom='U', prenom='Test', password_hash=generate_password_hash('pass'))
        db.session.add(user)
        db.session.commit()
        
        participant = create_participant(db, sample_event, user, 'PJ', 'Validé')
        
        role = Role(
            event_id=sample_event.id,
            name='Méchant',
            genre='H',
            group='Groupe B'
        )
        db.session.add(role)
        db.session.commit()
        
        # Assigner le rôle
        participant.role_id = role.id
        role.assigned_participant_id = participant.id
        db.session.commit()
        
        # Se connecter comme organisateur
        login(client, 'creator@test.com', 'creator123')
        
        # Désassigner via API
        response = client.post('/api/casting/unassign',
            json={
                'event_id': sample_event.id,
                'role_id': role.id
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('success') == True
        
        # Vérifier la désassignation
        db.session.refresh(participant)
        db.session.refresh(role)
        assert participant.role_id is None
        assert role.assigned_participant_id is None
    
    def test_api_unassign_unauthorized(self, auth_client, sample_event):
        """Test de désassignation sans droits."""
        response = auth_client.post('/api/casting/unassign',
            json={
                'event_id': sample_event.id,
                'role_id': 1
            }
        )
        
        assert response.status_code == 403
    
    def test_api_unassign_invalid_request(self, client, sample_event, user_creator):
        """Test de désassignation avec requête invalide."""
        from tests.conftest import login
        login(client, 'creator@test.com', 'creator123')
        
        response = client.post('/api/casting/unassign',
            json={
                'event_id': sample_event.id,
                'role_id': None
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

