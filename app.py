"""
Module de configuration et initialisation de l'application Flask GN Manager.

Ce module implémente le pattern Factory pour créer l'application Flask.
Il configure:
- La base de données SQLAlchemy (SQLite)
- L'authentification Flask-Login
- La configuration email (SMTP)
- Les blueprints de routes

Usage:
    from app import create_app
    app = create_app()
    app.run()
"""

from flask import Flask
from models import db, User
from flask_login import LoginManager
from extensions import mail, migrate, csrf, limiter, oauth
from werkzeug.middleware.proxy_fix import ProxyFix
import os



class MagicPrefixMiddleware(object):
    """
    Middleware "Magique" pour gérer le double-préfixe avec Nginx.
    
    Problème : 
    - Nginx a 'proxy_redirect / /gnmanager/;' qui ajoute /gnmanager aux redirections.
    - Flask a besoin de SCRIPT_NAME='/gnmanager' pour générer des liens HTML corrects.
    - MAIS si Flask a SCRIPT_NAME, il génère aussi des redirections avec /gnmanager.
    - Résultat : Nginx ajoute un 2ème préfixe -> /gnmanager/gnmanager/login.
    
    Solution :
    1. On force SCRIPT_NAME pour que le HTML soit bon.
    2. On INTERCEPTE la réponse. Si c'est une redirection (Header Location) qui contient le préfixe,
       on l'ENLÈVE avant de l'envoyer à Nginx.
    3. Nginx reçoit une Location sans préfixe, applique sa règle, et remet LE préfixe.
    """
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix.rstrip('/')

    def __call__(self, environ, start_response):
        # 1. Forcer SCRIPT_NAME pour la génération d'URL (HTML)
        environ['SCRIPT_NAME'] = self.prefix
        
        def custom_start_response(status, headers, exc_info=None):
            # 2. Intercepter les headers pour nettoyer les redirections
            if status.startswith('3'): # Redirection (301, 302, etc.)
                new_headers = []
                for name, value in headers:
                    if name.lower() == 'location':
                        # Si la location commence par le préfixe
                        # Cas 1: Exact match (/gnmanager -> /)
                        if value == self.prefix:
                            value = '/'
                        # Cas 2: Sous-chemin (/gnmanager/login -> /login)
                        elif value.startswith(self.prefix + '/'):
                            value = value[len(self.prefix):]
                        
                        # Note: Si c'est une URL absolue (http://...), on ne touche à rien
                        # et c'est très bien comme ça.
                    new_headers.append((name, value))
                return start_response(status, new_headers, exc_info)
            return start_response(status, headers, exc_info)


        return self.app(environ, custom_start_response)


def create_app(test_config=None):
    """
    Crée et configure l'application Flask.
    
    Cette fonction implémente le pattern Application Factory de Flask.
    Elle initialise tous les composants nécessaires:
    ...
    """
    app = Flask(__name__)
    
    # Gestion du préfixe d'URL (ex: /gnmanager)
    # Utilisation du middleware magique pour compatibilité Nginx force-redirect
    app_root = os.environ.get('APPLICATION_ROOT')
    if app_root:
        app.wsgi_app = MagicPrefixMiddleware(app.wsgi_app, prefix=app_root)
        app.config['APPLICATION_ROOT'] = app_root
        print(f"✅ Application configurée avec MagicPrefixMiddleware: {app_root}")
    else:
        # Fallback local
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Appliquer la configuration de test si fournie
    if test_config:
        app.config.from_mapping(test_config)
    
    # Détection du mode test via variable d'environnement (pour limiter/csrf)
    if os.environ.get('TESTING') == '1':
        app.config['TESTING'] = True
    
    # Configuration de sécurité - CRITIQUE: SECRET_KEY obligatoire en production!
    secret_key = app.config.get('SECRET_KEY') or os.environ.get('SECRET_KEY')
    
    if not secret_key and not app.config.get('TESTING'):
        # Détecter si on est en mode développement
        is_development = (
            app.debug or 
            os.environ.get('FLASK_ENV') == 'development' or
            os.environ.get('FLASK_DEBUG') == '1' or
            os.path.exists('gnmanager.db')
        )
        
        if not is_development:
            # En production réelle, refuser de démarrer sans SECRET_KEY
            raise ValueError(
                "SECURITY ERROR: SECRET_KEY environment variable must be set in production! "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        
        # En développement, utiliser une clé par défaut avec avertissement
        secret_key = 'dev-secret-key-change-in-production'
        app.logger.warning('⚠️  Using default SECRET_KEY in development mode. DO NOT use in production!')
    
    app.config['SECRET_KEY'] = secret_key
    
    # Configuration de la base de données
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gnmanager.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Email Configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'] or 'noreply@gnmanager.fr')
    
    # Configuration WTF/CSRF
    app.config['WTF_CSRF_ENABLED'] = not app.config.get('TESTING', False)
    app.config['WTF_CSRF_TIME_LIMIT'] = None  # Les tokens ne expirent pas (session-based)
    
    # Configuration Rate Limiting
    app.config['RATELIMIT_ENABLED'] = not app.config.get('TESTING', False)
    
    # Initialisation des extensions
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    oauth.init_app(app)
    
    # Configuration OAuth Google
    if os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET'):
        oauth.register(
            name='google',
            client_id=os.environ.get('GOOGLE_CLIENT_ID'),
            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
            access_token_url='https://accounts.google.com/o/oauth2/token',
            access_token_params=None,
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            authorize_params=None,
            api_base_url='https://www.googleapis.com/oauth2/v1/',
            client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive.file'},
            jwks_uri='https://www.googleapis.com/oauth2/v3/certs'
        )
        app.logger.info("✅ Google OAuth configuré")
    else:
        app.logger.warning("⚠️  Google OAuth non configuré (GOOGLE_CLIENT_ID/SECRET manquants)")
    
    # Configuration du gestionnaire de connexion
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'  # Mis à jour pour utiliser le nouveau blueprint
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        """
        Charge un utilisateur depuis la base de données pour Flask-Login.
        
        Args:
            user_id: ID de l'utilisateur à charger (string)
            
        Returns:
            User: Instance de l'utilisateur ou None si invalide
        """
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError):
            return None
    
    # Enregistrement des blueprints modulaires
    # Note: Architecture modulaire complète - tous les blueprints sont maintenant séparés
    from routes import auth_bp, admin_bp, event_bp, participant_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(participant_bp)
    
    app.logger.info("✅ Tous les blueprints modulaires enregistrés (auth, admin, event, participant)")
        
    with app.app_context():
        db.create_all()
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
