#!/usr/bin/env python3
import argparse
import json
import sys
import logging
from datetime import datetime
import os

os.environ.setdefault('FLASK_ENV', 'development')

# Configuration du logger pour ce module
logger = logging.getLogger('manage_db')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


# Imports déplacés à l'intérieur des fonctions pour éviter les imports circulaires


class DateTimeEncoder(json.JSONEncoder):
    """Client JSONEncoder pour gérer les objets datetime."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def serialize_model(instance):
    """Convertit une instance SQLAlchemy en dictionnaire."""
    data = {}
    for column in instance.__table__.columns:
        value = getattr(instance, column.name)
        data[column.name] = value
    return data

def export_data(args):
    """Exporte les données vers un fichier JSON.
    
    Exporte TOUTES les tables de la base de données:
    - Users, Events, Participants, Roles
    - PasswordResetToken, AccountValidationToken
    - ActivityLog
    - CastingProposal, CastingAssignment
    """
    file_path = args.file
    logger.info(f"Exportation des données vers {file_path}...")
    
    data = {
        'timestamp': datetime.now().isoformat(),
        'users': [],
        'events': [],
        'roles': [],
        'participants': [],
        'password_reset_tokens': [],
        'account_validation_tokens': [],
        'activity_logs': [],
        'casting_proposals': [],
        'casting_assignments': []
    }
    
    from app import create_app
    from models import (User, Event, Participant, Role, 
                        PasswordResetToken, AccountValidationToken,
                        ActivityLog, CastingProposal, CastingAssignment)
    
    app = create_app()
    with app.app_context():
        # Users
        users = User.query.all()
        data['users'] = [serialize_model(u) for u in users]
        logger.info(f"  - {len(users)} utilisateurs exportés")
        
        # Events
        events = Event.query.all()
        data['events'] = [serialize_model(e) for e in events]
        logger.info(f"  - {len(events)} événements exportés")
        
        # Roles
        roles = Role.query.all()
        data['roles'] = [serialize_model(r) for r in roles]
        logger.info(f"  - {len(roles)} rôles exportés")

        # Participants
        participants = Participant.query.all()
        data['participants'] = [serialize_model(p) for p in participants]
        logger.info(f"  - {len(participants)} participations exportées")
        
        # PasswordResetToken
        tokens = PasswordResetToken.query.all()
        data['password_reset_tokens'] = [serialize_model(t) for t in tokens]
        logger.info(f"  - {len(tokens)} tokens de réinitialisation exportés")
        
        # AccountValidationToken
        validation_tokens = AccountValidationToken.query.all()
        data['account_validation_tokens'] = [serialize_model(t) for t in validation_tokens]
        logger.info(f"  - {len(validation_tokens)} tokens de validation exportés")
        
        # ActivityLog
        logs = ActivityLog.query.all()
        data['activity_logs'] = [serialize_model(l) for l in logs]
        logger.info(f"  - {len(logs)} logs d'activité exportés")
        
        # CastingProposal
        proposals = CastingProposal.query.all()
        data['casting_proposals'] = [serialize_model(p) for p in proposals]
        logger.info(f"  - {len(proposals)} propositions de casting exportées")
        
        # CastingAssignment
        assignments = CastingAssignment.query.all()
        data['casting_assignments'] = [serialize_model(a) for a in assignments]
        logger.info(f"  - {len(assignments)} attributions de casting exportées")
        
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, cls=DateTimeEncoder, indent=2, ensure_ascii=False)
        
    logger.info("Export terminé avec succès.")

def import_data(args):
    """Importe les données depuis un fichier JSON.
    
    Importe TOUTES les tables de la base de données:
    - Users, Events, Participants, Roles
    - PasswordResetToken, AccountValidationToken
    - ActivityLog
    - CastingProposal, CastingAssignment
    """
    file_path = args.file
    clean = args.clean
    
    logger.info(f"Importation des données depuis {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Erreur: Le fichier {file_path} n'existe pas.")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Erreur: Le fichier {file_path} n'est pas un JSON valide.")
        sys.exit(1)
        
    from app import create_app
    from models import (db, User, Event, Participant, Role,
                        PasswordResetToken, AccountValidationToken,
                        ActivityLog, CastingProposal, CastingAssignment)
    
    app = create_app()
    with app.app_context():
        if clean:
            logger.info("Nettoyage de la base de données...")
            try:
                # Ordre de suppression pour respecter les FK
                db.session.query(CastingAssignment).delete()
                db.session.query(CastingProposal).delete()
                db.session.query(ActivityLog).delete()
                db.session.query(AccountValidationToken).delete()
                db.session.query(PasswordResetToken).delete()
                db.session.query(Participant).delete()
                db.session.query(Role).delete()
                db.session.query(Event).delete()
                db.session.query(User).delete()
                db.session.commit()
                logger.info("Données existantes supprimées.")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erreur lors du nettoyage: {e}")
                sys.exit(1)

        # Import Users
        logger.info("Importation des utilisateurs...")
        for user_data in data.get('users', []):
            if not User.query.get(user_data['id']):
                user = User()
                for key, value in user_data.items():
                    setattr(user, key, value)
                db.session.add(user)
        db.session.commit()
        logger.info("  - Utilisateurs importés.")

        # Import Events
        logger.info("Importation des événements...")
        for event_data in data.get('events', []):
            if not Event.query.get(event_data['id']):
                event = Event()
                for key, value in event_data.items():
                    if key in ['date_start', 'date_end'] and value:
                        value = datetime.fromisoformat(value)
                    setattr(event, key, value)
                db.session.add(event)
        db.session.commit()
        logger.info("  - Événements importés.")
        
        # Import Roles (AVANT Participants car Participant peut référencer Role)
        logger.info("Importation des rôles...")
        for role_data in data.get('roles', []):
            if not Role.query.get(role_data['id']):
                role = Role()
                for key, value in role_data.items():
                    # Ignorer assigned_participant_id pour l'instant (sera mis à jour après)
                    if key == 'assigned_participant_id':
                        continue
                    setattr(role, key, value)
                db.session.add(role)
        db.session.commit()
        logger.info("  - Rôles importés.")

        # Import Participants
        logger.info("Importation des participants...")
        for part_data in data.get('participants', []):
            if 'id' in part_data and not Participant.query.get(part_data['id']):
                part = Participant()
                for key, value in part_data.items():
                    setattr(part, key, value)
                db.session.add(part)
        db.session.commit()
        logger.info("  - Participations importées.")
        
        # Mettre à jour assigned_participant_id sur les rôles
        logger.info("Mise à jour des assignations de rôles...")
        for role_data in data.get('roles', []):
            if role_data.get('assigned_participant_id'):
                role = Role.query.get(role_data['id'])
                if role:
                    role.assigned_participant_id = role_data['assigned_participant_id']
        db.session.commit()
        
        # Import PasswordResetToken
        logger.info("Importation des tokens de réinitialisation...")
        for token_data in data.get('password_reset_tokens', []):
            if not PasswordResetToken.query.get(token_data['id']):
                token = PasswordResetToken()
                for key, value in token_data.items():
                    if key == 'created_at' and value:
                        value = datetime.fromisoformat(value)
                    setattr(token, key, value)
                db.session.add(token)
        db.session.commit()
        logger.info("  - Tokens de réinitialisation importés.")
        
        # Import AccountValidationToken
        logger.info("Importation des tokens de validation...")
        for token_data in data.get('account_validation_tokens', []):
            if not AccountValidationToken.query.get(token_data['id']):
                token = AccountValidationToken()
                for key, value in token_data.items():
                    if key == 'created_at' and value:
                        value = datetime.fromisoformat(value)
                    setattr(token, key, value)
                db.session.add(token)
        db.session.commit()
        logger.info("  - Tokens de validation importés.")
        
        # Import ActivityLog
        logger.info("Importation des logs d'activité...")
        for log_data in data.get('activity_logs', []):
            if not ActivityLog.query.get(log_data['id']):
                log = ActivityLog()
                for key, value in log_data.items():
                    if key == 'created_at' and value:
                        value = datetime.fromisoformat(value)
                    setattr(log, key, value)
                db.session.add(log)
        db.session.commit()
        logger.info("  - Logs d'activité importés.")
        
        # Import CastingProposal
        logger.info("Importation des propositions de casting...")
        for proposal_data in data.get('casting_proposals', []):
            if not CastingProposal.query.get(proposal_data['id']):
                proposal = CastingProposal()
                for key, value in proposal_data.items():
                    if key == 'created_at' and value:
                        value = datetime.fromisoformat(value)
                    setattr(proposal, key, value)
                db.session.add(proposal)
        db.session.commit()
        logger.info("  - Propositions de casting importées.")
        
        # Import CastingAssignment
        logger.info("Importation des attributions de casting...")
        for assign_data in data.get('casting_assignments', []):
            if not CastingAssignment.query.get(assign_data['id']):
                assignment = CastingAssignment()
                for key, value in assign_data.items():
                    setattr(assignment, key, value)
                db.session.add(assignment)
        db.session.commit()
        logger.info("  - Attributions de casting importées.")
        
    logger.info("Import terminé avec succès.")

def export_data_csv(args):
    """Exporte les données vers des fichiers CSV dans un répertoire.
    
    Exporte TOUTES les tables de la base de données:
    - Users, Events, Participants, Roles
    - PasswordResetToken, AccountValidationToken
    - ActivityLog
    - CastingProposal, CastingAssignment
    """
    dir_path = args.file
    logger.info(f"Exportation des données vers {dir_path}/ (CSV)...")
    
    # Créer le répertoire s'il n'existe pas
    import os
    os.makedirs(dir_path, exist_ok=True)
    
    from app import create_app
    from models import (User, Event, Participant, Role, 
                        PasswordResetToken, AccountValidationToken,
                        ActivityLog, CastingProposal, CastingAssignment)
    import csv
    
    app = create_app()
    with app.app_context():
        # Export Users
        users = User.query.all()
        users_file = os.path.join(dir_path, 'db_test_users.csv')
        with open(users_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'email', 'password_hash', 'nom', 'prenom', 'age', 'genre', 
                           'avatar_url', 'role', 'is_banned', 'is_deleted'])
            for u in users:
                writer.writerow([
                    u.id, u.email, u.password_hash, u.nom, u.prenom, u.age,
                    u.genre or '', u.avatar_url or '', u.role, u.is_banned, u.is_deleted
                ])
        logger.info(f"  - {len(users)} utilisateurs exportés vers {users_file}")
        
        # Export Events
        events = Event.query.all()
        events_file = os.path.join(dir_path, 'db_test_events.csv')
        with open(events_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'description', 'date_start', 'date_end', 'location',
                           'background_image', 'visibility', 'organizer_structure', 'org_link_url',
                           'org_link_title', 'google_form_url', 'google_form_active', 'discord_webhook_url',
                           'external_link', 'statut', 'groups_config', 'max_pjs', 'max_pnjs', 'max_organizers',
                           'is_casting_validated'])
            for e in events:
                writer.writerow([
                    e.id, e.name, e.description or '',
                    e.date_start.isoformat() if e.date_start else '',
                    e.date_end.isoformat() if e.date_end else '',
                    e.location or '', e.background_image or '', e.visibility or 'public',
                    e.organizer_structure or '', e.org_link_url or '', e.org_link_title or '',
                    e.google_form_url or '', e.google_form_active or False, e.discord_webhook_url or '',
                    e.external_link or '', e.statut, e.groups_config or '{}',
                    e.max_pjs or 50, e.max_pnjs or 10, e.max_organizers or 5,
                    e.is_casting_validated or False
                ])
        logger.info(f"  - {len(events)} événements exportés vers {events_file}")
        
        # Export Roles
        roles = Role.query.all()
        roles_file = os.path.join(dir_path, 'db_test_roles.csv')
        with open(roles_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'event_id', 'name', 'type', 'genre', 'group', 'assigned_participant_id',
                           'comment', 'google_doc_url', 'pdf_url'])
            for r in roles:
                writer.writerow([
                    r.id, r.event_id, r.name, r.type or '', r.genre or '', r.group or '',
                    r.assigned_participant_id or '', r.comment or '',
                    r.google_doc_url or '', r.pdf_url or ''
                ])
        logger.info(f"  - {len(roles)} rôles exportés vers {roles_file}")
        
        # Export Participants
        participants = Participant.query.all()
        participants_file = os.path.join(dir_path, 'db_test_participants.csv')
        with open(participants_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'event_id', 'user_id', 'type', 'group', 'role_id',
                           'role_communicated', 'role_received', 'registration_status', 'paf_status',
                           'payment_method', 'payment_amount', 'payment_comment', 'comment', 'custom_image'])
            for p in participants:
                writer.writerow([
                    p.id, p.event_id, p.user_id, p.type or '', p.group or '', p.role_id or '',
                    p.role_communicated, p.role_received, p.registration_status, p.paf_status or 'non versée',
                    p.payment_method or '', p.payment_amount or 0.0, p.payment_comment or '',
                    p.comment or '', p.custom_image or ''
                ])
        logger.info(f"  - {len(participants)} participations exportées vers {participants_file}")
        
        # Export PasswordResetToken
        tokens = PasswordResetToken.query.all()
        tokens_file = os.path.join(dir_path, 'db_test_password_reset_tokens.csv')
        with open(tokens_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'token', 'email', 'created_at'])
            for t in tokens:
                writer.writerow([
                    t.id, t.token, t.email,
                    t.created_at.isoformat() if t.created_at else ''
                ])
        logger.info(f"  - {len(tokens)} tokens de réinitialisation exportés vers {tokens_file}")
        
        # Export AccountValidationToken
        validation_tokens = AccountValidationToken.query.all()
        val_tokens_file = os.path.join(dir_path, 'db_test_account_validation_tokens.csv')
        with open(val_tokens_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'token', 'email', 'temp_data', 'created_at'])
            for t in validation_tokens:
                writer.writerow([
                    t.id, t.token, t.email, t.temp_data or '',
                    t.created_at.isoformat() if t.created_at else ''
                ])
        logger.info(f"  - {len(validation_tokens)} tokens de validation exportés vers {val_tokens_file}")
        
        # Export ActivityLog
        logs = ActivityLog.query.all()
        logs_file = os.path.join(dir_path, 'db_test_activity_logs.csv')
        with open(logs_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'action_type', 'user_id', 'event_id', 'details', 'is_viewed', 'created_at'])
            for l in logs:
                writer.writerow([
                    l.id, l.action_type, l.user_id or '', l.event_id or '',
                    l.details or '', l.is_viewed,
                    l.created_at.isoformat() if l.created_at else ''
                ])
        logger.info(f"  - {len(logs)} logs d'activité exportés vers {logs_file}")
        
        # Export CastingProposal
        proposals = CastingProposal.query.all()
        proposals_file = os.path.join(dir_path, 'db_test_casting_proposals.csv')
        with open(proposals_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'event_id', 'name', 'position', 'created_at'])
            for p in proposals:
                writer.writerow([
                    p.id, p.event_id, p.name, p.position,
                    p.created_at.isoformat() if p.created_at else ''
                ])
        logger.info(f"  - {len(proposals)} propositions de casting exportées vers {proposals_file}")
        
        # Export CastingAssignment
        assignments = CastingAssignment.query.all()
        assignments_file = os.path.join(dir_path, 'db_test_casting_assignments.csv')
        with open(assignments_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'proposal_id', 'role_id', 'participant_id', 'event_id', 'score'])
            for a in assignments:
                writer.writerow([
                    a.id, a.proposal_id, a.role_id, a.participant_id or '', a.event_id, a.score or ''
                ])
        logger.info(f"  - {len(assignments)} attributions de casting exportées vers {assignments_file}")
    
    logger.info("Export CSV terminé avec succès.")

def import_data_csv(args):
    """Importe les données depuis des fichiers CSV dans un répertoire.
    
    Importe TOUTES les tables de la base de données:
    - Users, Events, Participants, Roles
    - PasswordResetToken, AccountValidationToken
    - ActivityLog
    - CastingProposal, CastingAssignment
    """
    dir_path = args.file
    clean = args.clean
    
    logger.info(f"Importation des données depuis {dir_path}/ (CSV)...")
    
    import os
    import csv
    
    # Vérifier que le répertoire existe
    if not os.path.isdir(dir_path):
        logger.error(f"Erreur: Le répertoire {dir_path} n'existe pas.")
        sys.exit(1)
    
    from app import create_app
    from models import (db, User, Event, Participant, Role,
                        PasswordResetToken, AccountValidationToken,
                        ActivityLog, CastingProposal, CastingAssignment)
    
    app = create_app()
    with app.app_context():
        if clean:
            logger.info("Nettoyage de la base de données...")
            try:
                # Ordre de suppression pour respecter les FK
                db.session.query(CastingAssignment).delete()
                db.session.query(CastingProposal).delete()
                db.session.query(ActivityLog).delete()
                db.session.query(AccountValidationToken).delete()
                db.session.query(PasswordResetToken).delete()
                db.session.query(Participant).delete()
                db.session.query(Role).delete()
                db.session.query(Event).delete()
                db.session.query(User).delete()
                db.session.commit()
                logger.info("Données existantes supprimées.")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erreur lors du nettoyage: {e}")
                sys.exit(1)
        
        # Import Users
        users_file = os.path.join(dir_path, 'db_test_users.csv')
        if os.path.exists(users_file):
            logger.info("Importation des utilisateurs...")
            with open(users_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not User.query.get(int(row['id'])):
                        user = User()
                        user.id = int(row['id'])
                        user.email = row['email']
                        user.password_hash = row['password_hash']
                        user.nom = row['nom']
                        user.prenom = row['prenom']
                        user.age = int(row['age']) if row['age'] else None
                        user.genre = row['genre'] if row['genre'] else None
                        user.avatar_url = row['avatar_url'] if row['avatar_url'] else None
                        user.role = row['role']
                        user.is_banned = row['is_banned'].lower() in ['true', '1', 'yes']
                        user.is_deleted = row['is_deleted'].lower() in ['true', '1', 'yes']
                        db.session.add(user)
            db.session.commit()
            logger.info("  - Utilisateurs importés.")
        
        # Import Events
        events_file = os.path.join(dir_path, 'db_test_events.csv')
        if os.path.exists(events_file):
            logger.info("Importation des événements...")
            with open(events_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not Event.query.get(int(row['id'])):
                        event = Event()
                        event.id = int(row['id'])
                        event.name = row['name']
                        event.description = row['description'] if row['description'] else None
                        event.date_start = datetime.fromisoformat(row['date_start']) if row['date_start'] else None
                        event.date_end = datetime.fromisoformat(row['date_end']) if row['date_end'] else None
                        event.location = row['location'] if row['location'] else None
                        event.background_image = row['background_image'] if row['background_image'] else None
                        event.visibility = row['visibility'] if row['visibility'] else 'public'
                        event.organizer_structure = row['organizer_structure'] if row['organizer_structure'] else None
                        event.org_link_url = row['org_link_url'] if row['org_link_url'] else None
                        event.org_link_title = row['org_link_title'] if row['org_link_title'] else None
                        event.google_form_url = row['google_form_url'] if row['google_form_url'] else None
                        event.google_form_active = row['google_form_active'].lower() in ['true', '1', 'yes'] if row.get('google_form_active') else False
                        event.discord_webhook_url = row.get('discord_webhook_url') if row.get('discord_webhook_url') else None
                        event.external_link = row['external_link'] if row['external_link'] else None
                        event.statut = row['statut']
                        event.groups_config = row['groups_config'] if row['groups_config'] else '{}'
                        event.max_pjs = int(row['max_pjs']) if row.get('max_pjs') else 50
                        event.max_pnjs = int(row['max_pnjs']) if row.get('max_pnjs') else 10
                        event.max_organizers = int(row['max_organizers']) if row.get('max_organizers') else 5
                        event.is_casting_validated = row.get('is_casting_validated', '').lower() in ['true', '1', 'yes'] if row.get('is_casting_validated') else False
                        db.session.add(event)
            db.session.commit()
            logger.info("  - Événements importés.")
        
        # Import Roles (AVANT Participants car il y a des références croisées)
        # On importe d'abord sans assigned_participant_id
        roles_file = os.path.join(dir_path, 'db_test_roles.csv')
        roles_data_for_update = []  # Pour stocker les assigned_participant_id
        if os.path.exists(roles_file):
            logger.info("Importation des rôles...")
            with open(roles_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not Role.query.get(int(row['id'])):
                        role = Role()
                        role.id = int(row['id'])
                        role.event_id = int(row['event_id'])
                        role.name = row['name']
                        role.type = row.get('type') if row.get('type') else None
                        role.genre = row['genre'] if row['genre'] else None
                        role.group = row['group'] if row['group'] else None
                        # On stocke l'assigned_participant_id pour plus tard
                        if row['assigned_participant_id']:
                            roles_data_for_update.append({
                                'id': int(row['id']),
                                'assigned_participant_id': int(row['assigned_participant_id'])
                            })
                        role.comment = row['comment'] if row['comment'] else None
                        role.google_doc_url = row['google_doc_url'] if row['google_doc_url'] else None
                        role.pdf_url = row['pdf_url'] if row['pdf_url'] else None
                        db.session.add(role)
            db.session.commit()
            logger.info("  - Rôles importés.")
        
        # Import Participants
        participants_file = os.path.join(dir_path, 'db_test_participants.csv')
        if os.path.exists(participants_file):
            logger.info("Importation des participants...")
            with open(participants_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not Participant.query.get(int(row['id'])):
                        part = Participant()
                        part.id = int(row['id'])
                        part.event_id = int(row['event_id'])
                        part.user_id = int(row['user_id'])
                        part.type = row['type'] if row['type'] else None
                        part.group = row['group'] if row['group'] else None
                        part.role_id = int(row['role_id']) if row['role_id'] else None
                        part.role_communicated = row['role_communicated'].lower() in ['true', '1', 'yes']
                        part.role_received = row['role_received'].lower() in ['true', '1', 'yes']
                        part.registration_status = row['registration_status']
                        part.paf_status = row['paf_status'] if row['paf_status'] else 'non versée'
                        part.payment_method = row['payment_method'] if row['payment_method'] else None
                        part.payment_amount = float(row['payment_amount']) if row['payment_amount'] else 0.0
                        part.payment_comment = row['payment_comment'] if row['payment_comment'] else None
                        part.comment = row['comment'] if row['comment'] else None
                        part.custom_image = row['custom_image'] if row['custom_image'] else None
                        db.session.add(part)
            db.session.commit()
            logger.info("  - Participations importées.")
        
        # Mise à jour des assigned_participant_id sur les rôles
        if roles_data_for_update:
            logger.info("Mise à jour des assignations de rôles...")
            for role_data in roles_data_for_update:
                role = Role.query.get(role_data['id'])
                if role:
                    role.assigned_participant_id = role_data['assigned_participant_id']
            db.session.commit()
        
        # Import PasswordResetToken
        tokens_file = os.path.join(dir_path, 'db_test_password_reset_tokens.csv')
        if os.path.exists(tokens_file):
            logger.info("Importation des tokens de réinitialisation...")
            with open(tokens_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not PasswordResetToken.query.get(int(row['id'])):
                        token = PasswordResetToken()
                        token.id = int(row['id'])
                        token.token = row['token']
                        token.email = row['email']
                        token.created_at = datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                        db.session.add(token)
            db.session.commit()
            logger.info("  - Tokens de réinitialisation importés.")
        
        # Import AccountValidationToken
        val_tokens_file = os.path.join(dir_path, 'db_test_account_validation_tokens.csv')
        if os.path.exists(val_tokens_file):
            logger.info("Importation des tokens de validation...")
            with open(val_tokens_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not AccountValidationToken.query.get(int(row['id'])):
                        token = AccountValidationToken()
                        token.id = int(row['id'])
                        token.token = row['token']
                        token.email = row['email']
                        token.temp_data = row['temp_data'] if row['temp_data'] else None
                        token.created_at = datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                        db.session.add(token)
            db.session.commit()
            logger.info("  - Tokens de validation importés.")
        
        # Import ActivityLog
        logs_file = os.path.join(dir_path, 'db_test_activity_logs.csv')
        if os.path.exists(logs_file):
            logger.info("Importation des logs d'activité...")
            with open(logs_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not ActivityLog.query.get(int(row['id'])):
                        log = ActivityLog()
                        log.id = int(row['id'])
                        log.action_type = row['action_type']
                        log.user_id = int(row['user_id']) if row['user_id'] else None
                        log.event_id = int(row['event_id']) if row['event_id'] else None
                        log.details = row['details'] if row['details'] else None
                        log.is_viewed = row['is_viewed'].lower() in ['true', '1', 'yes']
                        log.created_at = datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                        db.session.add(log)
            db.session.commit()
            logger.info("  - Logs d'activité importés.")
        
        # Import CastingProposal
        proposals_file = os.path.join(dir_path, 'db_test_casting_proposals.csv')
        if os.path.exists(proposals_file):
            logger.info("Importation des propositions de casting...")
            with open(proposals_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not CastingProposal.query.get(int(row['id'])):
                        proposal = CastingProposal()
                        proposal.id = int(row['id'])
                        proposal.event_id = int(row['event_id'])
                        proposal.name = row['name']
                        proposal.position = int(row['position']) if row['position'] else 0
                        proposal.created_at = datetime.fromisoformat(row['created_at']) if row['created_at'] else None
                        db.session.add(proposal)
            db.session.commit()
            logger.info("  - Propositions de casting importées.")
        
        # Import CastingAssignment
        assignments_file = os.path.join(dir_path, 'db_test_casting_assignments.csv')
        if os.path.exists(assignments_file):
            logger.info("Importation des attributions de casting...")
            with open(assignments_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not CastingAssignment.query.get(int(row['id'])):
                        assignment = CastingAssignment()
                        assignment.id = int(row['id'])
                        assignment.proposal_id = int(row['proposal_id'])
                        assignment.role_id = int(row['role_id'])
                        assignment.participant_id = int(row['participant_id']) if row['participant_id'] else None
                        assignment.event_id = int(row['event_id'])
                        assignment.score = int(row['score']) if row.get('score') else None
                        db.session.add(assignment)
            db.session.commit()
            logger.info("  - Attributions de casting importées.")
    
    logger.info("Import CSV terminé avec succès.")

def main():
    parser = argparse.ArgumentParser(description="Outil de gestion de base de données import/export JSON et CSV.")
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    subparsers.required = True
    
    # Export Parser
    export_parser = subparsers.add_parser('export', help='Exporter la base de données')
    export_parser.add_argument('-f', '--file', required=True, help='Chemin du fichier/répertoire de sortie (.json pour JSON, répertoire pour CSV)')
    export_parser.set_defaults(func=None)  # Will be determined based on file extension
    
    # Import Parser
    import_parser = subparsers.add_parser('import', help='Importer la base de données')
    import_parser.add_argument('-f', '--file', required=True, help='Chemin du fichier/répertoire source (.json pour JSON, répertoire pour CSV)')
    import_parser.add_argument('--clean', action='store_true', help='Vider la base avant l\'importation')
    import_parser.set_defaults(func=None)  # Will be determined based on file extension
    
    args = parser.parse_args()
    
    # Déterminer le format basé sur le chemin fourni
    import os
    if args.command == 'export':
        if args.file.endswith('.json'):
            args.func = export_data
        elif os.path.isdir(args.file) or not os.path.splitext(args.file)[1]:  # Répertoire ou pas d'extension
            args.func = export_data_csv
        else:
            logger.error("Format non reconnu. Utilisez .json pour JSON ou un répertoire pour CSV.")
            sys.exit(1)
    elif args.command == 'import':
        if args.file.endswith('.json'):
            args.func = import_data
        elif os.path.isdir(args.file):  # Répertoire CSV
            args.func = import_data_csv
        else:
            logger.error("Format non reconnu. Utilisez .json pour JSON ou un répertoire contenant les fichiers CSV.")
            sys.exit(1)
    
    if hasattr(args, 'func') and args.func:
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
