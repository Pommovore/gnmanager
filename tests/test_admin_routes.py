"""
Tests pour les routes d'administration (admin_routes.py).

Couvre :
- Dashboard
- Gestion utilisateurs (add, update, delete)
- Logs d'activité  
- Permissions RBAC
"""

import pytest
from models import User, ActivityLog
from tests.conftest import login, logout
from werkzeug.security import check_password_hash


class TestDashboard:
    """Tests de la route /dashboard."""
    
    def test_dashboard_requires_login(self, client):
        """Le dashboard nécessite une authentification."""
        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirect vers login
    
    def test_dashboard_regular_user(self, client, user_regular):
        """Un utilisateur régulier peut accéder au dashboard."""
        login(client, 'user@test.com', 'password123')
        response = client.get('/dashboard')
        assert response.status_code == 200
    
    def test_dashboard_shows_events(self, client, user_regular, event_sample):
        """Le dashboard affiche les événements."""
        login(client, 'user@test.com', 'password123')
        response = client.get('/dashboard')
        assert response.status_code == 200
        # Devrait afficher le nom de l'événement
        assert event_sample.name.encode() in response.data


class TestAdminUserManagement:
    """Tests de gestion des utilisateurs par les admins."""
    
    def test_add_user_as_admin(self, client, user_admin, db):
        """Un admin peut ajouter un utilisateur."""
        login(client, 'admin@test.com', 'admin123')
        
        response = client.post('/admin/user/add', data={
            'email': 'newadmin@test.com'
        }, follow_redirects=True)
        
        # Vérifier que l'utilisateur a été créé
        new_user = User.query.filter_by(email='newadmin@test.com').first()
        assert new_user is not None
    
    def test_add_user_as_regular_user(self, client, user_regular):
        """Un utilisateur régulier ne peut pas ajouter d'utilisateur."""
        login(client, 'user@test.com', 'password123')
        
        response = client.post('/admin/user/add', data={
            'email': 'unauthorized@test.com'
        }, follow_redirects=True)
        
        # Doit être refusé
        assert b'refus' in response.data.lower() or b'acc' in response.data.lower()
    
    def test_update_user_as_admin(self, client, user_admin, user_regular, db):
        """Un admin peut modifier un utilisateur."""
        login(client, 'admin@test.com', 'admin123')
        
        response = client.post(f'/admin/user/{user_regular.id}/update_full', data={
            'email': 'user@test.com',
            'nom': 'UpdatedNom',
            'prenom': 'UpdatedPrenom',
            'age': '30',
            'genre': 'Femme',
            'status': 'actif'
        }, follow_redirects=True)
        
        # Vérifier la mise à jour
        db.session.refresh(user_regular)
        assert user_regular.nom == 'UpdatedNom'
        assert user_regular.prenom == 'UpdatedPrenom'
    
    def test_admin_cannot_modify_creator(self, client, user_admin, user_creator, db):
        """Un sysadmin ne peut pas modifier un créateur."""
        login(client, 'admin@test.com', 'admin123')
        
        response = client.post(f'/admin/user/{user_creator.id}/update_full', data={
            'email': 'creator@test.com',
            'nom': 'ShouldNotChange',
            'prenom': 'Supreme',
            'status': 'sysadmin'  # Tentative de downgrade
        }, follow_redirects=True)
        
        # Doit être refusé
        db.session.refresh(user_creator)
        assert user_creator.role == 'createur'  # Role inchangé
    
    def test_delete_user_as_admin(self, client, user_admin, db):
        """Un admin peut supprimer un utilisateur."""
        # Créer un utilisateur à supprimer
        to_delete = User(
            email='todelete@test.com',
            nom='To',
            prenom='Delete',
            role='user'
        )
        db.session.add(to_delete)
        db.session.commit()
        user_id = to_delete.id
        
        login(client, 'admin@test.com', 'admin123')
        
        response = client.post(f'/admin/user/{user_id}/delete', follow_redirects=True)
        
        # Vérifier la suppression
        deleted_user = User.query.get(user_id)
        assert deleted_user is None
    
    def test_admin_cannot_delete_creator(self, client, user_admin, user_creator):
        """Un admin ne peut pas supprimer le créateur."""
        login(client, 'admin@test.com', 'admin123')
        
        response = client.post(f'/admin/user/{user_creator.id}/delete', follow_redirects=True)
        

        # Le créateur doit toujours exister
        creator = User.query.get(user_creator.id)
        assert creator is not None
        assert b'cr' in response.data.lower() or b'refus' in response.data.lower()
    
    def test_admin_cannot_delete_self(self, client, user_admin):
        """Un admin ne peut pas se supprimer lui-même."""
        login(client, 'admin@test.com', 'admin123')
        
        response = client.post(f'/admin/user/{user_admin.id}/delete', follow_redirects=True)
        
        # Doit être refusé
        admin = User.query.get(user_admin.id)
        assert admin is not None


class TestAdminLogs:
    """Tests des logs d'activité."""
    
    def test_logs_page_requires_admin(self, client, user_regular):
        """Un utilisateur régulier ne peut pas accéder aux logs."""
        login(client, 'user@test.com', 'password123')
        response = client.get('/admin/logs', follow_redirects=True)
        
        assert b'refus' in response.data.lower() or b'acc' in response.data.lower()
    
    def test_logs_page_as_admin(self, client, user_admin):
        """Un admin peut accéder aux logs."""
        login(client, 'admin@test.com', 'admin123')
        response = client.get('/admin/logs')
        
        assert response.status_code == 200
    
    def test_logs_show_activity(self, client, user_admin, db):
        """Les logs affichent les activités."""
        import json
        # Créer un log d'inscription (type supporté par le template)
        log = ActivityLog(
            user_id=user_admin.id,
            action_type='user_registration',
            details=json.dumps({
                'nom': 'LogNom',
                'prenom': 'LogPrenom',
                'email': 'log@test.com'
            })
        )
        db.session.add(log)
        db.session.commit()
        
        login(client, 'admin@test.com', 'admin123')
        response = client.get('/admin/logs')
        
        assert b'Inscription' in response.data
        assert b'LogNom' in response.data
        assert b'log@test.com' in response.data
    
    def test_mark_logs_viewed(self, client, user_admin, db):
        """Un admin peut marquer les logs comme consultés."""
        # Créer des logs non vus
        log = ActivityLog(
            user_id=user_admin.id,
            action_type='test',
            details='test',
            is_viewed=False
        )
        db.session.add(log)
        db.session.commit()
        
        login(client, 'admin@test.com', 'admin123')
        response = client.post('/admin/logs/mark-viewed')
        
        assert response.status_code == 200
        
        # Vérifier que le log est marqué comme vu
        db.session.refresh(log)
        assert log.is_viewed == True


class TestProfileUpdate:
    """Tests de mise à jour de profil."""
    
    def test_update_own_profile(self, client, user_regular, db):
        """Un utilisateur peut mettre à jour son profil."""
        login(client, 'user@test.com', 'password123')
        
        response = client.post('/profile', data={
            'nom': 'NewNom',
            'prenom': 'NewPrenom',
            'age': '28',
            'genre': 'X'
        }, follow_redirects=True)
        
        # Vérifier la mise à jour
        db.session.refresh(user_regular)
        assert user_regular.nom == 'NewNom'
        assert user_regular.prenom == 'NewPrenom'
        assert user_regular.age == 28
    
    def test_update_password(self, client, user_regular, db):
        """Un utilisateur peut changer son mot de passe."""
        login(client, 'user@test.com', 'password123')
        
        response = client.post('/profile', data={
            'nom': user_regular.nom,
            'prenom': user_regular.prenom,
            'new_password': 'newpassword456',
            'confirm_password': 'newpassword456'
        }, follow_redirects=True)
        
        # Vérifier que le mot de passe a changé
        db.session.refresh(user_regular)
        assert check_password_hash(user_regular.password_hash, 'newpassword456')
    
    def test_password_mismatch(self, client, user_regular):
        """Les mots de passe non concordants doivent être rejetés."""
        login(client, 'user@test.com', 'password123')
        
        response = client.post('/profile', data={
            'nom': user_regular.nom,
            'prenom': user_regular.prenom,
            'new_password': 'newpassword456',
            'confirm_password': 'differentpassword'
        }, follow_redirects=True)
        
        assert b'correspondent pas' in response.data.lower() or b'mismatch' in response.data.lower()


class TestRBAC:
    """Tests des permissions RBAC (Role-Based Access Control)."""
    
    def test_creator_can_promote_to_admin(self, client, user_creator, user_regular, db):
        """Le créateur peut promouvoir un utilisateur en admin."""
        login(client, 'creator@test.com', 'creator123')
        
        response = client.post(f'/admin/user/{user_regular.id}/update_full', data={
            'email': user_regular.email,
            'nom': user_regular.nom,
            'prenom': user_regular.prenom,
            'status': 'sysadmin'
        }, follow_redirects=True)
        
        db.session.refresh(user_regular)
        assert user_regular.role == 'sysadmin'
    
    def test_admin_cannot_promote_to_creator(self, client, user_admin, user_regular, db):
        """Un admin ne peut pas promouvoir quelqu'un en créateur."""
        login(client, 'admin@test.com', 'admin123')
        
        response = client.post(f'/admin/user/{user_regular.id}/update_full', data={
            'email': user_regular.email,
            'nom': user_regular.nom,
            'prenom': user_regular.prenom,
            'status': 'createur'
        }, follow_redirects=True)
        
        db.session.refresh(user_regular)
        # Le rôle ne devrait pas changer en créateur
        assert user_regular.role != 'createur'
class TestUserEvents:
    """Tests de la vue des événements utilisateur."""
    
    def test_user_events_requires_admin(self, client, user_regular, user_admin, db):
        """La vue nécessite des droits d'admin."""
        # Non authentifié
        response = client.get(f'/admin/user/{user_regular.id}/events')
        assert response.status_code == 302
        
        # Authentifié mais non admin
        login(client, 'user@test.com', 'password123')
        response = client.get(f'/admin/user/{user_regular.id}/events', follow_redirects=True)
        assert response.status_code == 200
        assert b'acc' in response.data.lower() or b'refus' in response.data.lower()
        
    def test_user_events_display(self, client, user_admin, user_regular, sample_event, db):
        """Affiche correctement les événements d'un utilisateur."""
        from models import Participant, Role
        from constants import ParticipantType, RegistrationStatus
        
        # Inscrire l'utilisateur à l'événement 1
        p1 = Participant(
            event_id=sample_event.id,
            user_id=user_regular.id,
            type=ParticipantType.PJ.value,
            registration_status=RegistrationStatus.VALIDATED.value
        )
        db.session.add(p1)
        db.session.commit()
        
        login(client, 'admin@test.com', 'admin123')
        response = client.get(f'/admin/user/{user_regular.id}/events')
        
        assert response.status_code == 200
        # Vérifier présence infos utilisateur
        assert user_regular.email.encode() in response.data
        assert user_regular.nom.encode() in response.data
        
        # Vérifier présence événement
        assert sample_event.name.encode() in response.data
        assert b'PJ' in response.data
        assert b'Valid' in response.data.replace(b'\xc3\xa9', b'e') # Gérer encodage Validé
        
    def test_user_events_with_role(self, client, user_admin, user_regular, sample_event, db):
        """Affiche le rôle assigné à l'utilisateur."""
        from models import Participant, Role
        from constants import ParticipantType
        
        # Créer un rôle
        role = Role(
            event_id=sample_event.id,
            name='Super Héros',
            genre='H',
            group='Groupe A'
        )
        db.session.add(role)
        db.session.commit()
        
        # Inscrire avec rôle
        p = Participant(
            event_id=sample_event.id,
            user_id=user_regular.id,
            type=ParticipantType.PJ.value,
            role_id=role.id
        )
        db.session.add(p)
        role.assigned_participant_id = p.id
        db.session.commit()
        
        login(client, 'admin@test.com', 'admin123')
        response = client.get(f'/admin/user/{user_regular.id}/events')
        
        assert response.status_code == 200
        assert b'Super H' in response.data
        
    def test_user_events_empty(self, client, user_admin, user_regular):
        """Gère correctement un utilisateur sans événements."""
        login(client, 'admin@test.com', 'admin123')
        response = client.get(f'/admin/user/{user_regular.id}/events')
        
        assert response.status_code == 200
        assert b'aucun' in response.data.lower()
