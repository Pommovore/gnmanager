"""
Configuration et fixtures pytest pour GN Manager.

Ce module fournit des fixtures réutilisables pour tous les tests:
- app: Application Flask de test
- client: Client HTTP de test
- db: Base de données de test
- auth_client: Client authentifié
- Sample data: Utilisateurs, événements, participants de test
"""

import pytest
import os
import sys
import tempfile

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Event, Participant, Role
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


@pytest.fixture(scope='function')
def app():
    """
    Crée une instance Flask configurée pour les tests.
    
    Utilise une base de données SQLite en mémoire et désactive CSRF.
    """
    # Créer un fichier temporaire pour la base de données de test
    db_fd, db_path = tempfile.mkstemp()
    
    # Configuration de test
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['TESTING'] = 'true'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Créer toutes les tables
    with app.app_context():
        db.create_all()
        
    yield app
    
    # Nettoyage
    with app.app_context():
        db.session.remove()
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def client(app):
    """Client HTTP de test Flask."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def sample_user(app):
    """Crée un utilisateur de test standard."""
    with app.app_context():
        user = User(
            email='user@test.com',
            password_hash=generate_password_hash('password123'),
            nom='Test',
            prenom='User',
            age=25,
            genre='H',
            role='user'
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture(scope='function')
def sample_admin(app):
    """Crée un administrateur de test."""
    with app.app_context():
        admin = User(
            email='admin@test.com',
            password_hash=generate_password_hash('admin123'),
            nom='Admin',
            prenom='Test',
            role='sysadmin'
        )
        db.session.add(admin)
        db.session.commit()
        return admin


@pytest.fixture(scope='function')
def sample_creator(app):
    """Crée un compte créateur de test."""
    with app.app_context():
        creator = User(
            email='creator@test.com',
            password_hash=generate_password_hash('creator123'),
            nom='Creator',
            prenom='System',
            role='createur'
        )
        db.session.add(creator)
        db.session.commit()
        return creator


@pytest.fixture(scope='function')
def sample_event(app, sample_user):
    """Crée un événement de test."""
    with app.app_context():
        event = Event(
            name='Test GN Event',
            description='A test GN event',
            date_start=datetime.now() + timedelta(days=30),
            date_end=datetime.now() + timedelta(days=32),
            location='Test Location',
            visibility='public',
            statut='Inscriptions ouvertes'
        )
        db.session.add(event)
        db.session.commit()
        
        # Ajouter le créateur comme organisateur
        organizer = Participant(
            user_id=sample_user.id,
            event_id=event.id,
            type='organisateur',
            registration_status='Validé'
        )
        db.session.add(organizer)
        db.session.commit()
        
        return event


@pytest.fixture(scope='function')
def sample_participant(app, sample_event):
    """Crée un participant de test (PJ)."""
    with app.app_context():
        user = User(
            email='participant@test.com',
            password_hash=generate_password_hash('pass123'),
            nom='Participant',
            prenom='Test',
            role='user'
        )
        db.session.add(user)
        db.session.commit()
        
        participant = Participant(
            user_id=user.id,
            event_id=sample_event.id,
            type='PJ',
            group='Groupe A',
            registration_status='En attente'
        )
        db.session.add(participant)
        db.session.commit()
        
        return participant


@pytest.fixture(scope='function')
def auth_client(client, sample_user):
    """
    Client authentifié avec un utilisateur standard.
    
    Simule une session de connexion.
    """
    with client:
        client.post('/login', data={
            'email': 'user@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        yield client


@pytest.fixture(scope='function')
def admin_client(client, sample_admin):
    """
    Client authentifié avec un administrateur.
    """
    with client:
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        }, follow_redirects=True)
        yield client
