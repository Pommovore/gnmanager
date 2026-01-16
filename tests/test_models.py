"""Tests unitaires pour les modèles SQLAlchemy de GN Manager."""

import pytest
from models import User, Event, Participant, Role, ActivityLog
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta


class TestUserModel:
    """Tests du modèle User."""
    
    def test_create_user(self, app, db):
        """Test de création d'un utilisateur."""
        with app.app_context():
            from models import db
            user = User(
                email='test@example.com',
                password_hash=generate_password_hash('password'),
                nom='Doe',
                prenom='John'
            )
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.email == 'test@example.com'
            assert user.nom == 'Doe'
            assert user.prenom == 'John'
    
    def test_user_is_admin_property(self, app, sample_admin, sample_user, sample_creator):
        """Test de la propriété is_admin."""
        with app.app_context():
            from models import User
            
            # Recharger les utilisateurs depuis la DB
            admin = User.query.filter_by(email='admin@test.com').first()
            user = User.query.filter_by(email='user@test.com').first()
            creator = User.query.filter_by(email='creator@test.com').first()
            
            assert admin.is_admin is True
            assert user.is_admin is False
            assert creator.is_admin is True
    
    def test_password_hashing(self, app):
        """Test du hashage de mot de passe."""
        password = 'securepassword123'
        hashed = generate_password_hash(password)
        
        assert hashed != password
        assert check_password_hash(hashed, password) is True
        assert check_password_hash(hashed, 'wrongpassword') is False

    def test_user_session_cleanup(self, app, db):
        """Vérifie que la DB est nettoyée entre les tests."""
        with app.app_context():
            assert User.query.count() == 0


class TestEventModel:
    """Tests du modèle Event."""
    
    def test_create_event(self, app, db):
        """Test de création d'un événement."""
        with app.app_context():
            from models import db
            event = Event(
                name='Mon GN',
                description='Super événement',
                date_start=datetime(2026, 6, 1),
                date_end=datetime(2026, 6, 3),
                location='Paris',
                visibility='public'
            )
            db.session.add(event)
            db.session.commit()
            
            assert event.id is not None
            assert event.name == 'Mon GN'
            assert event.visibility == 'public'
            assert event.statut == 'En préparation'
    
    def test_event_external_links(self, app, db):
        """Test des liens externes de l'événement."""
        with app.app_context():
            from models import db
            event = Event(
                name='GN avec liens',
                date_start=datetime.now(),
                date_end=datetime.now() + timedelta(days=1),
                location='Test',
                org_link_url='https://example.org',
                org_link_title='Mon Asso',
                google_form_url='https://forms.gle/test'
            )
            db.session.add(event)
            db.session.commit()
            
            assert event.org_link_url == 'https://example.org'
            assert event.org_link_title == 'Mon Asso'
            assert event.google_form_url == 'https://forms.gle/test'


class TestParticipantModel:
    """Tests du modèle Participant."""
    
    def test_create_participant(self, app, sample_user, sample_event):
        """Test de création d'un participant."""
        with app.app_context():
            from models import db, Participant
            
            participant = Participant(
                user_id=sample_user.id,
                event_id=sample_event.id,
                type='PJ',
                group='Groupe A',
                registration_status='Validé',
                paf_status='versée',
                payment_amount=25.0
            )
            db.session.add(participant)
            db.session.commit()
            
            assert participant.id is not None
            assert participant.type == 'PJ'
            assert participant.registration_status == 'Validé'
            assert participant.paf_status == 'versée'
            assert participant.payment_amount == 25.0
    
    def test_participant_status_values(self, app, sample_user, sample_event):
        """Test des différents statuts de participant."""
        with app.app_context():
            from models import db, Participant
            
            statuses = ['En attente', 'Validé', 'Rejeté']
            
            for status in statuses:
                p = Participant(
                    user_id=sample_user.id,
                    event_id=sample_event.id,
                    type='PNJ',
                    registration_status=status
                )
                db.session.add(p)
                db.session.commit()
                
                assert p.registration_status == status


class TestRoleModel:
    """Tests du modèle Role."""
    
    def test_create_role(self, app, sample_event):
        """Test de création d'un rôle."""
        with app.app_context():
            from models import db
            
            role = Role(
                event_id=sample_event.id,
                name='Guerrier mystérieux',
                genre='H',
                group='Combattants'
            )
            db.session.add(role)
            db.session.commit()
            
            assert role.id is not None
            assert role.name == 'Guerrier mystérieux'
            assert role.genre == 'H'
    
    def test_role_assignment(self, app, sample_event, sample_participant):
        """Test d'assignation d'un rôle à un participant."""
        with app.app_context():
            from models import db, Role
            
            role = Role(
                event_id=sample_event.id,
                name='Rôle assigné',
                assigned_participant_id=sample_participant.id
            )
            db.session.add(role)
            db.session.commit()
            
            assert role.assigned_participant_id == sample_participant.id
            assert role.assigned_participant is not None


class TestActivityLogModel:
    """Tests du modèle ActivityLog."""
    
    def test_create_activity_log(self, app, sample_user):
        """Test de création d'un log d'activité."""
        with app.app_context():
            from models import db
            
            log = ActivityLog(
                user_id=sample_user.id,
                action_type='Test Action',
                details='Test details'
            )
            db.session.add(log)
            db.session.commit()
            
            assert log.id is not None
            assert log.user_id == sample_user.id
            assert log.action_type == 'Test Action'
            assert log.is_viewed is False
    
    def test_log_timestamp(self, app, sample_user):
        """Test que le timestamp est automatiquement créé."""
        with app.app_context():
            from models import db
            
            log = ActivityLog(
                user_id=sample_user.id,
                action_type='timestamp_test',
                details='test'
            )
            db.session.add(log)
            db.session.commit()
            
            assert log.created_at is not None
            assert isinstance(log.created_at, datetime)
