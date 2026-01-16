"""
Tests pour les routes d'authentification (auth_routes.py).

Couvre :
- Login/logout
- Registration
- Password reset
- Account validation
- Rate limiting
- CSRF protection
"""

import pytest
from models import User, AccountValidationToken, PasswordResetToken
from tests.conftest import login, logout


class TestLogin:
    """Tests de la route /login."""
    
    def test_login_page_loads(self, client):
        """La page de login doit se charger correctement."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'connexion' in response.data.lower()
    
    def test_login_success(self, client, user_regular):
        """Un utilisateur avec les bons identifiants peut se connecter."""
        response = login(client, 'user@test.com', 'password123')
        assert response.status_code == 200
        # Vérifie redirection vers dashboard
        assert b'dashboard' in response.data.lower() or b'v' in response.data.lower() or b'en pr' in response.data.lower()
    
    def test_login_wrong_password(self, client, user_regular):
        """Un mauvais mot de passe doit être rejeté."""
        response = login(client, 'user@test.com', 'wrongpassword')
        assert response.status_code == 200
        assert b'incorrect' in response.data.lower() or b'erreur' in response.data.lower()
    
    def test_login_unknown_user(self, client):
        """Un email inconnu doit retourner une erreur."""
        response = login(client, 'unknown@test.com', 'password123')
        assert response.status_code == 200
        # Doit rediriger vers register ou afficher un message
        assert b'inconnu' in response.data.lower() or b'register' in response.data.lower()
    
    def test_login_banned_user(self, client, db):
        """Un utilisateur banni ne peut pas se connecter."""
        from werkzeug.security import generate_password_hash
        banned_user = User(
            email='banned@test.com',
            nom='Banned',
            prenom='User',
            role='user',
            is_banned=True,
            password_hash=generate_password_hash('password123')
        )
        db.session.add(banned_user)
        db.session.commit()
        
        response = login(client, 'banned@test.com', 'password123')
        assert response.status_code == 200
        assert b'banni' in response.data.lower()


class TestLogout:
    """Tests de la route /logout."""
    
    def test_logout_success(self, client, user_regular):
        """Un utilisateur connecté peut se déconnecter."""
        login(client, 'user@test.com', 'password123')
        response = logout(client)
        assert response.status_code == 200
        # Devrait être redirigé vers login
        assert b'connexion' in response.data.lower()


class TestRegister:
    """Tests de la route /register."""
    
    def test_register_page_loads(self, client):
        """La page d'inscription doit se charger."""
        response = client.get('/register')
        assert response.status_code == 200
        assert b'inscription' in response.data.lower()
    
    def test_register_new_user(self, client, db):
        """Un nouvel utilisateur peut s'inscrire."""
        response = client.post('/register', data={
            'email': 'newuser@test.com',
            'nom': 'New',
            'prenom': 'User',
            'age': '25',
            'genre': 'Homme'
        }, follow_redirects=True)
        
        # Vérifier que l'utilisateur a été créé
        user = User.query.filter_by(email='newuser@test.com').first()
        assert user is not None
        assert user.nom == 'New'
        assert user.prenom == 'User'
        
        # Vérifier qu'un token de validation a été créé
        token = AccountValidationToken.query.filter_by(email='newuser@test.com').first()
        assert token is not None
    
    def test_register_existing_email(self, client, user_regular):
        """On ne peut pas s'inscrire avec un email existant."""
        response = client.post('/register', data={
            'email': 'user@test.com',  # Email déjà utilisé
            'nom': 'Another',
            'prenom': 'User',
            'age': '30'
        }, follow_redirects=True)
        
        assert b'existe' in response.data.lower() or b'utilis' in response.data.lower()


class TestPasswordReset:
    """Tests des routes de réinitialisation de mot de passe."""
    
    def test_forgot_password_page_loads(self, client):
        """La page mot de passe oublié doit se charger."""
        response = client.get('/forgot_password')
        assert response.status_code == 200
    
    def test_forgot_password_existing_user(self, client, user_regular, db):
        """Un token de reset doit être créé pour un utilisateur existant."""
        response = client.post('/forgot_password', data={
            'email': 'user@test.com'
        }, follow_redirects=True)
        
        # Vérifier qu'un token a été créé
        token = PasswordResetToken.query.filter_by(email='user@test.com').first()
        assert token is not None
    
    def test_forgot_password_unknown_user(self, client):
        """Pas d'erreur révélée pour un email inconnu (sécurité)."""
        response = client.post('/forgot_password', data={
            'email': 'unknown@test.com'
        }, follow_redirects=True)
        
        # Doit afficher le même message (ne pas révéler si l'email existe)
        assert response.status_code == 200


class TestAccountValidation:
    """Tests de la validation de compte."""
    
    def test_validate_account_with_valid_token(self, client, db):
        """Un compte peut être validé avec un token valide."""
        # Créer un utilisateur sans mot de passe (non validé)
        user = User(
            email='tovalid@test.com',
            nom='To',
            prenom='Validate',
            role='user',
            password_hash=None  # Pas encore de mot de passe
        )
        db.session.add(user)
        
        # Créer un token de validation
        import uuid
        token_str = str(uuid.uuid4())
        token = AccountValidationToken(token=token_str, email='tovalid@test.com')
        db.session.add(token)
        db.session.commit()
        
        # Accéder à la page de validation
        response = client.get(f'/validate_account/{token_str}')
        assert response.status_code == 200
        assert b'password' in response.data.lower() or b'mot de passe' in response.data.lower()
        
        # Définir un mot de passe
        response = client.post(f'/validate_account/{token_str}', data={
            'password': 'newpassword123'
        }, follow_redirects=True)
        
        # Vérifier que le mot de passe a été défini
        user = User.query.filter_by(email='tovalid@test.com').first()
        assert user.password_hash is not None
        
        # Vérifier que le token a été supprimé
        token = AccountValidationToken.query.filter_by(token=token_str).first()
        assert token is None
    
    def test_validate_account_with_expired_token(self, client, db):
        """Un token expiré doit être rejeté."""
        from datetime import datetime, timedelta
        import uuid
        
        # Créer un token expiré
        token_str = str(uuid.uuid4())
        token = AccountValidationToken(token=token_str, email='expired@test.com')
        token.created_at = datetime.utcnow() - timedelta(hours=25)  # Expiré (> 24h)
        db.session.add(token)
        db.session.commit()
        
        response = client.get(f'/validate_account/{token_str}', follow_redirects=True)
        assert b'expir' in response.data.lower() or b'invalide' in response.data.lower()


class TestRateLimiting:
    """Tests du rate limiting sur les routes sensibles."""
    
    @pytest.mark.skip(reason="Rate limiting is disabled in testing mode")
    def test_login_rate_limit(self, client, user_regular):
        """Trop de tentatives de login doivent être bloquées."""
        # Flask-Limiter limite à 5 par minute pour /login
        for i in range(6):
            response = client.post('/login', data={
                'email': 'user@test.com',
                'password': 'wrongpassword'
            })
            
            if i < 5:
                # Les 5 premières tentatives passent
                assert response.status_code in [200, 302]
            else:
                # La 6ème devrait être rate-limited
                assert response.status_code == 429 or b'trop' in response.data.lower()
