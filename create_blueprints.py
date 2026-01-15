#!/usr/bin/env python3
"""
Script pour extraire et créer les blueprints depuis routes.py.

Ce script lit routes.py et extrait les différentes routes dans des blueprints séparés.
"""

import re
import os

# Définir les routes pour chaque blueprint
BLUEPRINT_ROUTES = {
    'auth_routes.py': [
        ('/', 'index'),
        ('/login', 'login'),
        ('/register', 'register'),
        ('/validate_account/<token>', 'validate_account'),
        ('/forgot_password', 'forgot_password'),
        ('/reset_password/<token>', 'reset_password'),
        ('/logout', 'logout'),
    ],
    'admin_routes.py': [
        ('/dashboard', 'dashboard'),
        ('/profile', 'update_profile'),
        ('/admin/user/add', 'admin_add_user'),
        ('/admin/user/<int:user_id>/update_full', 'admin_update_full_user'),
        ('/admin/user/<int:user_id>/delete', 'admin_delete_user'),
        ('/admin/logs', 'admin_logs'),
        ('/admin/logs/mark-viewed', 'mark_logs_viewed'),
    ],
    'event_routes.py': [
        ('/event/create', 'create_event'),
        ('/event/<int:event_id>/update_general', 'update_event_general'),
        ('/event/<int:event_id>/update_status', 'update_event_status'),
        ('/event/<int:event_id>', 'event_detail'),
        ('/event/<int:event_id>/update_groups', 'update_event_groups'),
        ('/event/<int:event_id>/join', 'join_event'),
    ],
    'participant_routes.py': [
        ('/event/<int:event_id>/participants', 'manage_participants'),
        ('/event/<int:event_id>/participants/bulk_update', 'bulk_update_participants'),
        ('/event/<int:event_id>/participant/<int:p_id>/update', 'update_participant'),
        ('/event/<int:event_id>/participant/<int:p_id>/change-status', 'change_participant_status'),
        ('/event/<int:event_id>/casting', 'casting_interface'),
        ('/api/casting/assign', 'api_assign_role'),
        ('/api/casting/unassign', 'api_unassign_role'),
    ],
}

def create_blueprint_header(blueprint_name):
    """Crée l'en-tête d'un fichier blueprint."""
    bp_var = blueprint_name.replace('_routes.py', '_bp')
    
    headers = {
        'auth_routes.py': '''"""
Routes d'authentification pour GN Manager.

Ce module gère:
- Connexion / Déconnexion
- Inscription et validation de compte
- Réinitialisation de mot de passe
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, AccountValidationToken, PasswordResetToken, ActivityLog
from auth import generate_password, send_email
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from extensions import limiter
from constants import ActivityLogType, DefaultValues
import uuid
import json
import os

auth_bp = Blueprint('auth', __name__)
''',
        'admin_routes.py': '''"""
Routes d'administration pour GN Manager.

Ce module gère:
- Dashboard utilisateur
- Gestion des utilisateurs (CRUD)
- Journal d'activité (logs)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Event, Participant, ActivityLog
from auth import generate_password, send_email
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import datetime
from decorators import admin_required
from constants import UserRole, ActivityLogType, DefaultValues
from sqlalchemy.orm import joinedload
import json
import os

admin_bp = Blueprint('admin', __name__)
''',
        'event_routes.py': '''"""
Routes de gestion des événements pour GN Manager.

Ce module gère:
- Création et édition d'événements
- Affichage des détails
- Configuration des groupes
- Inscription aux événements
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Event, Participant, ActivityLog
from datetime import datetime
from decorators import organizer_required
from constants import EventStatus, ParticipantType, RegistrationStatus, ActivityLogType
import json

event_bp = Blueprint('event', __name__)
''',
        'participant_routes.py': '''"""
Routes de gestion des participants pour GN Manager.

Ce module gère:
- Liste et gestion des participants
- Interface de casting (drag & drop)
- Attribution des rôles
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Event, Participant, Role, ActivityLog
from decorators import organizer_required
from constants import RegistrationStatus, PAFStatus, ActivityLogType
from sqlalchemy.orm import joinedload
import json

participant_bp = Blueprint('participant', __name__)
''',
    }
    
    return headers.get(blueprint_name, f'# {blueprint_name}\n')

def main():
    """Fonction principale."""
    print("📦 Création des blueprints...")
    print("=" * 60)
    
    # Créer le fichier __init__.py
    init_content = '''"""
Package de routes pour GN Manager.

Organisation modulaire des routes par fonctionnalité.
"""

from .auth_routes import auth_bp
from .admin_routes import admin_bp
from .event_routes import event_bp
from .participant_routes import participant_bp

__all__ = ['auth_bp', 'admin_bp', 'event_bp', 'participant_bp']
'''
    
    os.makedirs('routes', exist_ok=True)
    
    with open('routes/__init__.py', 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    print("✅ Créé routes/__init__.py")
    
    # Créer les fichiers blueprint avec headers
    for filename in BLUEPRINT_ROUTES.keys():
        header = create_blueprint_header(filename)
        
        with open(f'routes/{filename}', 'w', encoding='utf-8') as f:
            f.write(header)
            f.write('\n\n# Routes seront extraites depuis routes.py\n')
            f.write('# TODO: Extraire les fonctions de route correspondantes\n')
        
        routes_count = len(BLUEPRINT_ROUTES[filename])
        print(f"✅ Créé routes/{filename} ({routes_count} routes)")
    
    print("=" * 60)
    print(f"✅ {len(BLUEPRINT_ROUTES)} blueprints créés")
    print("")
    print("⚠️  ATTENTION: Les fonctions de routes doivent être copiées manuellement")
    print("   depuis routes.py vers les blueprints correspondants.")
    print("")
    print("📝 Prochaines étapes:")
    print("   1. Copier les fonctions de route dans les blueprints appropriés")
    print("   2. Remplacer 'main' par le nom du blueprint (auth_bp, admin_bp, etc.)")
    print("   3. Adapter les url_for('main.X') en url_for('blueprint.X')")  
    print("   4. Mettre à jour app.py pour utiliser les nouveaux blueprints")

if __name__ == '__main__':
    main()
