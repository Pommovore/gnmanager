"""
Extensions Flask pour GN Manager.

Ce module centralise les instances des extensions Flask :
- mail : Flask-Mail pour l'envoi d'emails
- migrate : Flask-Migrate pour les migrations de base de données
- csrf : Flask-WTF pour la protection CSRF
- limiter : Flask-Limiter pour le rate limiting
- cache : Flask-Caching pour la mise en cache
"""

from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth
from flask_caching import Cache

mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()
oauth = OAuth()
cache = Cache()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://"
)
