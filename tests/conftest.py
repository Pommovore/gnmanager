"""
Configuration pytest pour GN Manager.

Ce fichier configure l'environnement de test avec :
- Fixtures communes (client, app, db)
- Configuration de la base de données de test
- Helpers pour les tests
"""

import pytest
import os
from app import create_app
from models import db as _db, User, Event, Participant, Role
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='session')
def app():
    """
    Fixture Flask app pour les tests.
    
    Crée une application Flask configurée pour les tests avec :
    - Base de données SQLite en mémoire
    - TESTING=True
    - WTF_CSRF_ENABLED=False pour simplifier les tests
    """
    # Set testing environment
    os.environ['TESTING'] = '1'
    
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost.localdomain',
        'SECRET_KEY': 'test-secret-key-for-testing-only'
    }
    
    app = create_app(test_config)
    
    return app


@pytest.fixture(scope='function')
def db(app):
    """
    Fixture base de données.
    
    Crée toutes les tables avant chaque test et les supprime après.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app, db):
    """
    Fixture client de test Flask.
    
    Permet de faire des requêtes HTTP vers l'application.
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """Fixture pour tester les commandes CLI."""
    return app.test_cli_runner()


# Fixtures utilisateurs

@pytest.fixture
def user_regular(db):
    """Crée un utilisateur régulier pour les tests."""
    user = User(
        email='user@test.com',
        nom='Test',
        prenom='User',
        age=25,
        role='user',
        password_hash=generate_password_hash('password123')
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_user(user_regular):
    """Alias pour les anciens tests."""
    return user_regular


@pytest.fixture
def user_admin(db):
    """Crée un administrateur système pour les tests."""
    admin = User(
        email='admin@test.com',
        nom='Admin',
        prenom='System',
        age=30,
        role='sysadmin',
        password_hash=generate_password_hash('admin123')
    )
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def sample_admin(user_admin):
    """Alias pour les anciens tests."""
    return user_admin


@pytest.fixture
def user_creator(db):
    """Crée un créateur (super admin) pour les tests."""
    creator = User(
        email='creator@test.com',
        nom='Creator',
        prenom='Supreme',
        age=35,
        role='createur',
        password_hash=generate_password_hash('creator123')
    )
    db.session.add(creator)
    db.session.commit()
    return creator


@pytest.fixture
def sample_creator(user_creator):
    """Alias pour les anciens tests."""
    return user_creator


# Fixtures événements

@pytest.fixture
def event_sample(db, user_creator):
    """Crée un événement de test."""
    from datetime import datetime, timedelta
    import json
    
    event = Event(
        name='Test Event',
        description='Event for testing',
        date_start=datetime.now() + timedelta(days=30),
        date_end=datetime.now() + timedelta(days=32),
        location='Test Location',
        statut='En préparation',
        groups_config=json.dumps({
            "PJ": ["Groupe A", "Groupe B"],
            "PNJ": ["Groupe C"],
            "Organisateur": ["général", "coordinateur"]
        })
    )
    db.session.add(event)
    db.session.commit()
    
    # Ajouter le créateur comme organisateur
    participant = Participant(
        event_id=event.id,
        user_id=user_creator.id,
        type='Organisateur',  # Fixed: must match ParticipantType.ORGANISATEUR.value
        group='général',
        registration_status='Validé'
    )
    db.session.add(participant)
    db.session.commit()
    
    return event


@pytest.fixture
def sample_event(event_sample):
    """Alias pour les anciens tests."""
    return event_sample


@pytest.fixture
def sample_participant(db, event_sample, user_regular):
    """Alias pour les anciens tests."""
    return create_participant(db, event_sample, user_regular)


# Clients authentifiés

@pytest.fixture
def auth_client(client, user_regular):
    """Client connecté en tant qu'utilisateur régulier."""
    login(client, 'user@test.com', 'password123')
    return client


@pytest.fixture
def admin_client(client, user_admin):
    """Client connecté en tant qu'administrateur."""
    login(client, 'admin@test.com', 'admin123')
    return client


# Helpers de test

def login(client, email, password):
    """
    Helper pour se connecter.
    
    Args:
        client: Client de test Flask
        email: Email de l'utilisateur
        password: Mot de passe
        
    Returns:
        Response de la requête de login
    """
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


def logout(client):
    """Helper pour se déconnecter."""
    return client.get('/logout', follow_redirects=True)


def create_participant(db, event, user, participant_type='PJ', status='Validé'):
    """
    Helper pour créer un participant.
    
    Args:
        db: Session database
        event: Événement
        user: Utilisateur
        participant_type: Type (PJ, PNJ, organisateur)
        status: Statut d'inscription
        
    Returns:
        Participant créé
    """
    participant = Participant(
        event_id=event.id,
        user_id=user.id,
        type=participant_type,
        group='Test Group',
        registration_status=status
    )
    db.session.add(participant)
    db.session.commit()
    return participant
