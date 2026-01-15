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
from routes import main
from extensions import mail, migrate, csrf, limiter
import os


def create_app():
    """
    Crée et configure l'application Flask.
    
    Cette fonction implémente le pattern Application Factory de Flask.
    Elle initialise tous les composants nécessaires:
    - Configuration de l'application
    - Base de données
    - Système d'authentification
    - Service d'email
    - Protection CSRF
    - Rate limiting
    - Routes
    
    Returns:
        Flask: Application Flask configurée et prête à l'emploi
        
    Raises:
        ValueError: Si SECRET_KEY n'est pas définie en production
        
    Note:
        La clé secrète DOIT être définie via la variable d'environnement
        SECRET_KEY en production pour des raisons de sécurité.
    """
    app = Flask(__name__)
    
    # Configuration de sécurité - CRITIQUE: SECRET_KEY obligatoire en production!
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        # En mode développement, utiliser une clé par défaut
        # En production, lever une exception
        if not app.debug and os.environ.get('FLASK_ENV') != 'development':
            raise ValueError(
                "SECURITY ERROR: SECRET_KEY environment variable must be set in production! "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
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
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None  # Les tokens ne expirent pas (session-based)
    
    # Initialisation des extensions
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    
    # Configuration du gestionnaire de connexion
    login_manager = LoginManager()
    login_manager.login_view = 'main.login'
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
        
    app.register_blueprint(main)
    
    with app.app_context():
        db.create_all()
        
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
