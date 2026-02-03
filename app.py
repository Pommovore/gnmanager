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

from flask import Flask, render_template, request, session
from models import db, User
from flask_login import LoginManager
from extensions import mail, migrate, csrf, limiter, oauth, cache
from werkzeug.middleware.proxy_fix import ProxyFix
import os
from logging_config import configure_logging



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
        
        # 1b. Si PATH_INFO commence par le préfixe (cas d'accès direct sans reverse proxy strippant le path),
        # on doit l'enlever pour que le routing Flask fonctionne.
        path_info = environ.get('PATH_INFO', '')
        if path_info.startswith(self.prefix):
            environ['PATH_INFO'] = path_info[len(self.prefix):]
        
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
    
    # DEBUG: Diagnostic CSRF/Session - PLACÉ AU DÉBUT pour s'exécuter avant CSRFProtect
    @app.before_request
    def log_request_info():
        # Ne logger que les requêtes intéressantes (pas les static)
        if not request.path.startswith('/static'):
            app.logger.debug(f"🔍 REQUEST: {request.method} {request.url}")
            app.logger.debug(f"   Headers: Host={request.headers.get('Host')}, X-Forwarded-Proto={request.headers.get('X-Forwarded-Proto')}, Origin={request.headers.get('Origin')}, Referer={request.headers.get('Referer')}")
            app.logger.debug(f"   Cookies: {request.cookies.keys()}")
            app.logger.debug(f"   Session: {'user_id' in session}, csrf_token in session: {'csrf_token' in session}")
            app.logger.debug(f"   Scheme: {request.scheme}, ScriptRoot: {request.script_root}, Path: {request.path}")

    # Gestion du préfixe d'URL (ex: /gnmanager)
    # Utilisation du middleware magique pour compatibilité Nginx force-redirect
    app_root = os.environ.get('APPLICATION_ROOT')
    
    # Configuration ProxyFix (Toujours nécessaire derrière un reverse proxy comme Nginx)
    # x_for=1 : Prend le 1er header X-Forwarded-For pour l'IP client
    # x_proto=1 : Prend le 1er header X-Forwarded-Proto pour savoir si HTTPS
    # x_host=1 : Prend le 1er header X-Forwarded-Host pour le domaine
    # x_prefix=1 : Prend le 1er header X-Forwarded-Prefix (si présent)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    if app_root:
        # On applique MagicPrefixMiddleware *après* ProxyFix (donc ProxyFix traite la requête externe d'abord)
        # Mais en python wsgi, on wrappe: Middleware(app). Donc app = ProxyFix(MagicPrefix(app)) si on veut que ProxyFix voie les headers bruts
        # Erratum: ProxyFix doit être le PLUS EXTERNE pour lire les headers Nginx.
        # Donc la requête entre dans ProxyFix -> nettoie environ -> passe à MagicPrefix -> passe à Flask
        app.wsgi_app = MagicPrefixMiddleware(app.wsgi_app, prefix=app_root)
        app.config['APPLICATION_ROOT'] = app_root
        print(f"✅ Application configurée avec MagicPrefixMiddleware: {app_root}")
    
    # Appliquer la configuration de test si fournie
    if test_config:
        app.config.from_mapping(test_config)
    
    # Détection du mode test via variable d'environnement (pour limiter/csrf)
    if os.environ.get('TESTING') == '1':
        app.config['TESTING'] = True
    
    # Configuration Cookies Sécurisés (Indispensable pour Chrome/Safari modernes en HTTPS)
    # On force la sécurité si on n'est PAS en debug/local simple
    is_production = os.environ.get('GN_ENVIRONMENT') in ['prod', 'production']
    if is_production or (app_root and 'https' in (os.environ.get('APP_PUBLIC_HOST', '') or '')):
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['REMEMBER_COOKIE_SECURE'] = True
        app.config['REMEMBER_COOKIE_HTTPONLY'] = True
        app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
    
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
    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gnmanager.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Optimisations SQLite pour la concurrence (WAL mode + timeout)
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'connect_args': {'timeout': 30},
        }
    
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
    
    # Configuration Cache
    # SimpleCache pour dev/test, Redis recommandé en production
    cache_type = os.environ.get('CACHE_TYPE', 'SimpleCache')
    app.config['CACHE_TYPE'] = cache_type
    app.config['CACHE_DEFAULT_TIMEOUT'] = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))  # 5 minutes par défaut
    
    if cache_type == 'RedisCache':
        app.config['CACHE_REDIS_URL'] = os.environ.get('CACHE_REDIS_URL', 'redis://localhost:6379/0')
    
    # Initialisation des extensions
    app.jinja_env.add_extension('jinja2.ext.do')
    db.init_app(app)

    # Activer le Write-Ahead Logging (WAL) pour meilleure concurrence lecture/écriture
    # DOIT être fait après init_app et dans un contexte d'application
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        from sqlalchemy import event
        with app.app_context():
            @event.listens_for(db.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
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
        app.logger.debug("✅ Google OAuth configuré")
    else:
        app.logger.warning("⚠️  Google OAuth non configuré (GOOGLE_CLIENT_ID/SECRET manquants)")
    
    # Configuration du gestionnaire de connexion
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'  # Mis à jour pour utiliser le nouveau blueprint
    login_manager.init_app(app)
    
    # Configure structured logging early
    configure_logging(app)
    
    # Initialize enhanced error handlers
    from error_handler import init_error_handlers
    init_error_handlers(app)
    
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
    from routes import auth_bp, admin_bp, event_bp, participant_bp, webhook_bp
    from routes.health_routes import health_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(participant_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(health_bp)
    
    app.logger.debug("✅ Tous les blueprints modulaires enregistrés (auth, admin, event, participant)")
    
    # Context processor pour rendre la version disponible dans tous les templates
    @app.context_processor
    def inject_version():
        version = "dev"
        try:
            # En production, on lit la version depuis le fichier généré au déploiement
            if os.path.exists('.deploy-version'):
                with open('.deploy-version', 'r') as f:
                    version = f.read().strip()
            else:
                # Fallback: essaye de lire version.py s'il existe
                from version import __version__
                version = __version__
        except Exception:
             pass
             
             
        return dict(
            app_version=version,
            gn_environment=os.environ.get('GN_ENVIRONMENT', 'prod')
        )
    
    @app.template_filter('from_json')
    def from_json_filter(s):
        import json
        try:
            return json.loads(s) if s else None
        except (ValueError, TypeError, json.JSONDecodeError):
            return None
    
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 errors - Page not found."""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        """Handle 500 errors - Internal server error."""
        db.session.rollback()  # Rollback any failed database transactions
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(e):
        """Handle 403 errors - Forbidden access."""
        return render_template('errors/403.html'), 403
        
    with app.app_context():
        db.create_all()
        
    return app

if __name__ == '__main__':
    app = create_app()
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(host=host, port=port, debug=True)
