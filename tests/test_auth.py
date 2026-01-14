"""Tests pour les fonctionnalités d'authentification."""

import pytest
from auth import generate_password, send_email
from models import User, PasswordResetToken, AccountValidationToken
from werkzeug.security import check_password_hash


class TestPasswordGeneration:
    """Tests de génération de mot de passe."""
    
    def test_generate_password_format(self):
        """Test que le mot de passe généré a le bon format."""
        password = generate_password()
        
        assert len(password) == 9
        assert password[:4].isalpha()  # 4 premières lettres
        assert password[4:].isdigit()  # 5 derniers chiffres
    
    def test_generate_password_uniqueness(self):
        """Test que les mots de passe générés sont différents."""
        passwords = [generate_password() for _ in range(10)]
        
        # Au moins quelques mots de passe doivent être différents
        assert len(set(passwords)) > 5


class TestAuthenticationRoutes:
    """Tests des routes d'authentification."""
    
    def test_login_page_loads(self, client):
        """Test que la page de login se charge."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'connexion' in response.data.lower()
    
    def test_register_page_loads(self, client):
        """Test que la page d'inscription se charge."""
        response = client.get('/register')
        assert response.status_code == 200
    
    def test_successful_login(self, client, sample_user):
        """Test d'une connexion réussie."""
        response = client.post('/login', data={
            'email': 'user@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Devrait rediriger vers le dashboard
        assert b'dashboard' in response.data.lower() or b'événement' in response.data.lower()
    
    def test_failed_login_wrong_password(self, client, sample_user):
        """Test d'une connexion échouée (mauvais mot de passe)."""
        response = client.post('/login', data={
            'email': 'user@test.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Devrait afficher une erreur
        assert b'erreur' in response.data.lower() or b'incorrect' in response.data.lower()
    
    def test_failed_login_nonexistent_user(self, client):
        """Test d'une connexion échouée (utilisateur inexistant)."""
        response = client.post('/login', data={
            'email': 'nonexistent@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_logout(self, auth_client):
        """Test de déconnexion."""
        response = auth_client.get('/logout', follow_redirects=True)
        
        assert response.status_code == 200
        # Devrait rediriger vers login
        assert b'login' in response.data.lower() or b'connexion' in response.data.lower()
    
    def test_register_new_user(self, client, app):
        """Test d'enregistrement d'un nouvel utilisateur."""
        response = client.post('/register', data={
            'email': 'newuser@test.com',
            'nom': 'New',
            'prenom': 'User',
            'age': '30',
            'genre': 'H'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier que l'utilisateur a été créé
        with app.app_context():
            user = User.query.filter_by(email='newuser@test.com').first()
            assert user is not None
            assert user.nom == 'New'
            assert user.prenom == 'User'
    
    def test_register_duplicate_email(self, client, sample_user):
        """Test qu'on ne peut pas enregistrer deux fois le même email."""
        response = client.post('/register', data={
            'email': 'user@test.com',  # Email déjà existant
            'nom': 'Duplicate',
            'prenom': 'User',
            'age': '25',
            'genre': 'F'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Devrait afficher une erreur
        assert b'existe' in response.data.lower() or b'error' in response.data.lower()


class TestPasswordReset:
    """Tests de réinitialisation de mot de passe."""
    
    def test_forgot_password_page_loads(self, client):
        """Test que la page de mot de passe oublié se charge."""
        response = client.get('/forgot_password')
        assert response.status_code == 200
    
    def test_request_password_reset(self, client, sample_user, app):
        """Test de demande de réinitialisation de mot de passe."""
        response = client.post('/forgot_password', data={
            'email': 'user@test.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Vérifier qu'un token a été créé
        with app.app_context():
            token = PasswordResetToken.query.filter_by(email='user@test.com').first()
            assert token is not None


class TestAccountValidation:
    """Tests de validation de compte."""
    
    def test_account_validation_token_creation(self, app, sample_user):
        """Test de création d'un token de validation."""
        with app.app_context():
            from models import db
            import uuid
            
            token = AccountValidationToken(
                email=sample_user.email,
                token=str(uuid.uuid4())
            )
            db.session.add(token)
            db.session.commit()
            
            assert token.id is not None
            assert token.email == sample_user.email
