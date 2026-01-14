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
from extensions import mail
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
    - Routes
    
    Returns:
        Flask: Application Flask configurée et prête à l'emploi
        
    Note:
        La clé secrète doit être définie via la variable d'environnement
        SECRET_KEY en production pour des raisons de sécurité.
    """
    app = Flask(__name__)
    
    # Configuration de sécurité - IMPORTANT: Définir SECRET_KEY en production!
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    if app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production' and not app.debug:
        app.logger.warning('ATTENTION: Utilisation de la clé secrète par défaut en production!')
    
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
    
    # Initialisation des extensions
    db.init_app(app)
    mail.init_app(app)
    
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
