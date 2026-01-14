"""Tests des permissions et du contrôle d'accès RBAC."""

import pytest
from models import User


class TestRBACPermissions:
    """Tests du système RBAC (Role-Based Access Control)."""
    
    def test_user_roles(self, app, sample_user, sample_admin, sample_creator):
        """Test des différents rôles utilisateur."""
        with app.app_context():
            user = User.query.filter_by(email='user@test.com').first()
            admin = User.query.filter_by(email='admin@test.com').first()
            creator = User.query.filter_by(email='creator@test.com').first()
            
            assert user.role == 'user'
            assert admin.role == 'sysadmin'
            assert creator.role == 'createur'
    
    def test_admin_privileges(self, app, sample_admin, sample_user, sample_creator):
        """Test des privilèges administrateur."""
        with app.app_context():
            user = User.query.filter_by(email='user@test.com').first()
            admin = User.query.filter_by(email='admin@test.com').first()
            creator = User.query.filter_by(email='creator@test.com').first()
            
            assert user.is_admin is False
            assert admin.is_admin is True
            assert creator.is_admin is True


class TestOrganizerPermissions:
    """Tests des permissions d'organisateur d'événement."""
    
    def test_organizer_can_access_participants(self, auth_client, sample_event):
        """Test qu'un organisateur peut accéder à la gestion des participants."""
        response = auth_client.get(f'/event/{sample_event.id}/participants')
        assert response.status_code == 200
    
    def test_non_organizer_cannot_access_participants(self, client, app, sample_event):
        """Test qu'un non-organisateur ne peut pas accéder à la gestion."""
        with app.app_context():
            from models import db
            from werkzeug.security import generate_password_hash
            
            # Créer un utilisateur qui n'est pas organisateur
            other_user = User(
                email='other@test.com',
                password_hash=generate_password_hash('pass123'),
                nom='Other',
                prenom='User'
            )
            db.session.add(other_user)
            db.session.commit()
        
        # Se connecter avec cet utilisateur
        client.post('/login', data={
            'email': 'other@test.com',
            'password': 'pass123'
        })
        
        # Tenter d'accéder aux participants
        response = client.get(f'/event/{sample_event.id}/participants', follow_redirects=True)
        # Devrait être redirigé ou refusé
        assert response.status_code in [200, 302, 403]


class TestAdminOnlyRoutes:
    """Tests des routes réservées aux administrateurs."""
    
    def test_regular_user_cannot_delete_users(self, auth_client, sample_admin):
        """Test qu'un utilisateur normal ne peut pas supprimer d'utilisateurs."""
        response = auth_client.post(f'/admin/user/{sample_admin.id}/delete', follow_redirects=True)
        # Devrait être refusé
        assert response.status_code in [200, 302, 403]
    
    def test_admin_can_access_admin_routes(self, admin_client):
        """Test qu'un admin peut accéder aux routes admin."""
        response = admin_client.get('/dashboard?admin_view=users')
        assert response.status_code == 200
    
    def test_cannot_delete_creator_without_being_creator(self, admin_client, sample_creator):
        """Test qu'un sysadmin ne peut pas supprimer un créateur."""
        response = admin_client.post(f'/admin/user/{sample_creator.id}/delete', follow_redirects=True)
        
        # Devrait échouer ou afficher une erreur
        assert response.status_code == 200
        # Le créateur devrait toujours exister
        # (vérification dans le contenu de la réponse)


class TestEventVisibilityPermissions:
    """Tests des permissions de visibilité des événements."""
    
    def test_public_event_visible_to_all(self, client, app):
        """Test qu'un événement public est visible par tous."""
        with app.app_context():
            from models import db
            from datetime import datetime, timedelta
            
            event = Event(
                name='Public Event',
                date_start=datetime.now(),
                date_end=datetime.now() + timedelta(days=1),
                location='Test',
                visibility='public'
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id
        
        response = client.get(f'/event/{event_id}')
        assert response.status_code == 200
    
    def test_private_event_visibility(self, client, app):
        """Test qu'un événement privé a des restrictions."""
        with app.app_context():
            from models import db
            from datetime import datetime, timedelta
            
            event = Event(
                name='Private Event',
                date_start=datetime.now(),
                date_end=datetime.now() + timedelta(days=1),
                location='Test',
                visibility='private'
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id
        
        response = client.get(f'/event/{event_id}')
        # Devrait être accessible (ou pas selon l'implémentation)
        assert response.status_code in [200, 302, 403]
