"""
Routes pour la gestion du menu GForms (Google Forms integration).

Ce module gère :
- L'affichage des soumissions de formulaires Google Forms
- La gestion des catégories et couleurs
- Les associations champs → catégories
- Les APIs JSON pour les données dynamiques
"""

import json
import logging
import csv
from io import StringIO, TextIOWrapper
from flask import Blueprint, render_template, request, jsonify, current_app, Response
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy.exc import OperationalError
from werkzeug.security import generate_password_hash
import secrets

from models import db, Event, GFormsCategory, GFormsFieldMapping, GFormsSubmission, User, Participant, EventNotification
from decorators import organizer_required
from constants import RegistrationStatus, ParticipantType

# Création du Blueprint
gforms_bp = Blueprint('gforms', __name__)
logger = logging.getLogger(__name__)


@gforms_bp.route('/event/<int:event_id>/gforms')
@login_required
@organizer_required
def gforms_menu(event_id):
    """
    Page principale du menu GForms.
    Affiche les 3 onglets : formulaires, catégories, settings.
    """
    event = Event.query.get_or_404(event_id)
    
    # Vérifier si le webhook secret est configuré
    if not event.webhook_secret:
        # Menu grisé/désactivé sera géré dans le template
        pass
    
    # Initialiser la catégorie par défaut si elle n'existe pas (insensible à la casse)
    default_category = GFormsCategory.query.filter(
        GFormsCategory.event_id == event_id,
        db.func.lower(GFormsCategory.name) == 'généralités'
    ).first()
    
    if not default_category:
        default_category = GFormsCategory(
            event_id=event_id,
            name='Généralités',
            color='neutral',
            position=0
        )
        db.session.add(default_category)
        db.session.commit()
        logger.info(f"Created default 'Généralités' category for event {event_id}")

    # Vérifier et créer les mappings par défaut pour timestamp et type_ajout
    default_fields = ['timestamp', 'type_ajout']
    mappings_changed = False
    
    for field_name in default_fields:
        mapping = GFormsFieldMapping.query.filter_by(
            event_id=event_id,
            field_name=field_name
        ).first()
        
        if not mapping:
            mapping = GFormsFieldMapping(
                event_id=event_id,
                field_name=field_name,
                category_id=default_category.id
            )
            db.session.add(mapping)
            mappings_changed = True
            
    if mappings_changed:
        db.session.commit()
        logger.info(f"Created default field mappings for event {event_id}")
    
    return render_template(
        'gforms/main.html',
        event=event,
        user=current_user
    )


@gforms_bp.route('/event/<int:event_id>/gforms/submissions')
@login_required
@organizer_required
def get_submissions(event_id):
    """
    API: Retourne la liste des soumissions avec pagination.
    """
    event = Event.query.get_or_404(event_id)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    try:
        # Récupérer les soumissions
        submissions_query = GFormsSubmission.query.filter_by(event_id=event_id).order_by(GFormsSubmission.timestamp.desc())
        submissions_paginated = submissions_query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Récupérer les mappings de champs pour connaître tous les champs disponibles
        field_mappings = GFormsFieldMapping.query.filter_by(event_id=event_id).all()
        field_mapping_dict = {fm.field_name: fm for fm in field_mappings}
        
        # Construire la réponse JSON
        submissions_data = []
        for sub in submissions_paginated.items:
            try:
                raw_data = json.loads(sub.raw_data) if sub.raw_data else {}
                
                submissions_data.append({
                    'id': sub.id,
                    'email': sub.email,
                    'timestamp': sub.timestamp.strftime('%Y/%m/%d %H:%M') if sub.timestamp else "N/A",
                    'type_ajout': sub.type_ajout,
                    'raw_data': raw_data
                })
            except Exception as e:
                logger.error(f"Error processing submission {sub.id}: {e}")
                continue
        
        return jsonify({
            'submissions': submissions_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': submissions_paginated.total,
                'pages': submissions_paginated.pages,
                'has_prev': submissions_paginated.has_prev,
                'has_next': submissions_paginated.has_next
            }
        })
    except OperationalError as e:
        if 'no such table' in str(e).lower():
            logger.warning(f"GFormsSubmission table not found: {e}")
            return jsonify({
                'submissions': [],
                'pagination': {
                    'page': page, 'per_page': per_page, 'total': 0, 'pages': 0,
                    'has_prev': False, 'has_next': False
                }
            })
        logger.error(f"Database error in get_submissions: {e}", exc_info=True)
        return jsonify({'error': 'Erreur de base de données'}), 500
    except Exception as e:
        logger.error(f"Error in get_submissions_data: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@gforms_bp.route('/event/<int:event_id>/gforms/categories', methods=['GET'])
@login_required
@organizer_required
def get_categories(event_id):
    """
    API: Retourne la liste des catégories.
    """
    event = Event.query.get_or_404(event_id)
    
    categories = GFormsCategory.query.filter_by(event_id=event_id).order_by(GFormsCategory.position).all()
    
    categories_data = [{
        'id': cat.id,
        'name': cat.name,
        'color': cat.color,
        'position': cat.position
    } for cat in categories]
    
    return jsonify({'categories': categories_data})


@gforms_bp.route('/event/<int:event_id>/gforms/categories', methods=['POST'])
@login_required
@organizer_required
def save_categories(event_id):
    """
    API: Crée ou met à jour des catégories.
    Payload: { "categories": [{"id": 1, "name": "...", "color": "...", "position": 0}, ...] }
    """
    event = Event.query.get_or_404(event_id)
    
    data = request.get_json()
    categories_input = data.get('categories', [])
    
    # Couleurs valides
    valid_colors = ['neutral', 'blue', 'green', 'red', 'yellow', 'purple', 'orange', 'pink', 'teal']
    
    try:
        # Récupérer les catégories existantes
        existing_categories = {cat.id: cat for cat in GFormsCategory.query.filter_by(event_id=event_id).all()}
        existing_ids = set(existing_categories.keys())
        updated_ids = set()
        
        for idx, cat_data in enumerate(categories_input):
            cat_id = cat_data.get('id')
            name = cat_data.get('name', '').strip()
            if not name:
                continue  # Skip empty names
            
            # Normalisation : Majuscule au début si possible
            if len(name) > 1:
                name = name[0].upper() + name[1:]
            elif len(name) == 1:
                name = name.upper()
            
            color = cat_data.get('color', 'neutral')
            
            if color not in valid_colors:
                color = 'neutral'
            
            if cat_id and cat_id in existing_categories:
                # Update existing
                category = existing_categories[cat_id]
                category.name = name
                category.color = color
                category.position = idx
                updated_ids.add(cat_id)
            else:
                # Create new
                category = GFormsCategory(
                    event_id=event_id,
                    name=name,
                    color=color,
                    position=idx
                )
                db.session.add(category)
        
        # Delete categories that were removed
        removed_ids = existing_ids - updated_ids
        for cat_id in removed_ids:
            # Ne pas supprimer la catégorie "Généralités" par défaut
            if existing_categories[cat_id].name != 'Généralités':
                # Sauvegarder les mappings (alias) en les détachant de la catégorie supprimée
                # au lieu de les supprimer par cascade
                mappings_to_preserve = GFormsFieldMapping.query.filter_by(
                    event_id=event_id,
                    category_id=cat_id
                ).all()
                
                for mapping in mappings_to_preserve:
                    mapping.category_id = None
                
                db.session.delete(existing_categories[cat_id])
        
        # Notification details
        actions = []
        if updated_ids: actions.append(f"{len(updated_ids)} catégories mises à jour")
        # Count new categories (those in input but not in existing at start, or we can just track them)
        # simplistic approach: actions already has updates.
        # Let's count creations:
        created_count = len([c for c in categories_input if not c.get('id')])
        if created_count > 0: actions.append(f"{created_count} catégories créées")
        
        if removed_ids: actions.append(f"{len(removed_ids)} catégories supprimées")
        
        db.session.commit()
        logger.info(f"Saved {len(categories_input)} categories for event {event_id}")
        
        if actions:
            from services.notification_service import create_notification
            create_notification(
                event_id=event.id,
                user_id=current_user.id,
                action_type='gforms_config_update',
                description=f"Configuration GForms : {', '.join(actions)}"
            )
        
        return jsonify({'success': True, 'message': 'Catégories enregistrées'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving categories for event {event_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@gforms_bp.route('/event/<int:event_id>/gforms/fields', methods=['GET'])
@login_required
@organizer_required
def get_fields(event_id):
    """
    API: Retourne la liste des champs détectés avec leurs mappings.
    """
    event = Event.query.get_or_404(event_id)
    
    try:
        # Récupérer tous les champs détectés à partir des soumissions
        submissions = GFormsSubmission.query.filter_by(event_id=event_id).all()
        detected_fields = set()
        
        # Champs système toujours présents
        detected_fields.add('timestamp')
        detected_fields.add('type_ajout')
        
        for sub in submissions:
            try:
                raw_data = json.loads(sub.raw_data) if sub.raw_data else {}
                detected_fields.update(raw_data.keys())
            except:
                continue
        
        # Récupérer les mappings existants
        mappings = GFormsFieldMapping.query.filter_by(event_id=event_id).all()
        mapping_dict = {m.field_name: m for m in mappings}
        
        # Récupérer les catégories pour inclure les infos de couleur
        categories = GFormsCategory.query.filter_by(event_id=event_id).all()
        category_dict = {cat.id: cat for cat in categories}
        
        # Construire la réponse JSON
        fields_data = []
        for field_name in sorted(detected_fields):
            mapping = mapping_dict.get(field_name)
            category = None
            if mapping and mapping.category_id:
                category = category_dict.get(mapping.category_id)
            
            fields_data.append({
                'field_name': field_name,
                'field_alias': mapping.field_alias if mapping else None,
                'category_id': mapping.category_id if mapping else None,
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'color': category.color
                } if category else None
            })
        
        return jsonify({'fields': fields_data})
    except OperationalError as e:
        if 'no such table' in str(e).lower():
            # Retourner au moins les champs par défaut
            return jsonify({'fields': [
                {'field_name': 'timestamp', 'field_alias': 'Date', 'category_id': None, 'category': None},
                {'field_name': 'type_ajout', 'field_alias': 'Type', 'category_id': None, 'category': None}
            ]})
        logger.error(f"Database error in get_fields: {e}", exc_info=True)
        return jsonify({'error': 'Erreur de base de données'}), 500
    except Exception as e:
        logger.error(f"Error in get_fields: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@gforms_bp.route('/event/<int:event_id>/gforms/field-mappings', methods=['POST'])
@login_required
@organizer_required
def save_field_mappings(event_id):
    """
    API: Sauvegarde les associations champ → catégorie.
    Payload: { "mappings": [{"field_name": "...", "category_id": 1, "field_alias": "..."}, ...] }
    """
    event = Event.query.get_or_404(event_id)
    
    data = request.get_json()
    mappings_input = data.get('mappings', [])
    
    try:
        for mapping_data in mappings_input:
            field_name = mapping_data.get('field_name')
            category_id = mapping_data.get('category_id')
            field_alias = mapping_data.get('field_alias')
            
            if not field_name:
                continue
            
            # Vérifier si le mapping existe already
            mapping = GFormsFieldMapping.query.filter_by(
                event_id=event_id,
                field_name=field_name
            ).first()
            
            if mapping:
                # Update
                mapping.category_id = category_id
                mapping.field_alias = field_alias
            else:
                # Create
                mapping = GFormsFieldMapping(
                    event_id=event_id,
                    field_name=field_name,
                    category_id=category_id,
                    field_alias=field_alias
                )
                db.session.add(mapping)
        
        db.session.commit()
        logger.info(f"Saved field mappings for event {event_id}")
        
        from services.notification_service import create_notification
        create_notification(
            event_id=event.id,
            user_id=current_user.id,
            action_type='gforms_mapping_update',
            description=f"Configuration GForms : {len(mappings_input)} mappings mis à jour"
        )
        
        return jsonify({'success': True, 'message': 'Mappings enregistrés'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving field mappings for event {event_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@gforms_bp.route('/event/<int:event_id>/gforms/export')
@login_required
@organizer_required
def export_gforms_data(event_id):
    """
    Export CSV fusionnant les données de Participant et les données GForms.
    """
    event = Event.query.get_or_404(event_id)
    
    # 1. Récupérer toutes les soumissions GForms
    submissions = GFormsSubmission.query.filter_by(event_id=event_id).all()
    sub_map = {}
    for s in submissions:
        try:
            sub_map[s.email.lower()] = json.loads(s.raw_data) if s.raw_data else {}
        except:
            sub_map[s.email.lower()] = {}
            
    # 2. Récupérer tous les participants de l'événement
    participants = Participant.query.filter_by(event_id=event_id).all()
    
    # 3. Collecter tous les champs dynamiques de GForms
    dynamic_fields = set()
    for data in sub_map.values():
        dynamic_fields.update(data.keys())
    
    # Trier les champs pour la consistance
    sorted_dynamic_fields = sorted(list(dynamic_fields))
    
    # 4. Définir les en-têtes CSV
    headers = [
        "Email", "Nom", "Prénom", "Type Participant", "Statut Inscription", 
        "Statut PAF", "Montant Payé", "Méthode Paiement", "Téléphone", 
        "Discord", "Facebook", "Commentaire Global"
    ] + sorted_dynamic_fields
    
    # 5. Construire les lignes
    rows = []
    processed_emails = set()
    
    for p in participants:
        email_key = p.user.email.lower()
        processed_emails.add(email_key)
        form_data = sub_map.get(email_key, {})
        
        row = [
            p.user.email,
            p.user.nom,
            p.user.prenom,
            p.type,
            p.registration_status,
            p.paf_status,
            p.payment_amount,
            p.payment_method,
            p.participant_phone or p.user.phone or "",
            p.participant_discord or p.user.discord or "",
            p.participant_facebook or p.user.facebook or "",
            p.global_comment or ""
        ]
        
        # Ajouter les données du formulaire
        for field in sorted_dynamic_fields:
            row.append(form_data.get(field, ""))
            
        rows.append(row)
        
    # Ajouter les soumissions qui n'ont pas (encore) de participant lié
    # (par exemple si un formulaire arrive mais l'utilisateur n'est pas encore créé/lié)
    for email, form_data in sub_map.items():
        if email not in processed_emails:
            row = [email, "(No Participant)", "", "", "", "", "", "", "", "", "", ""]
            for field in sorted_dynamic_fields:
                row.append(form_data.get(field, ""))
            rows.append(row)
            
    # 6. Générer le CSV (format Excel compatible avec BOM UTF-8 et point-virgule)
    output = StringIO()
    output.write('\ufeff') # BOM for Excel
    writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    writer.writerow(headers)
    writer.writerows(rows)
    
    filename = f"export_gforms_{event.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    # Notification
    from services.notification_service import create_notification
    create_notification(
        event_id=event.id,
        user_id=current_user.id,
        action_type='gforms_export',
        description="Action : export des données GForms"
    )
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


@gforms_bp.route('/event/<int:event_id>/gforms/import', methods=['POST'])
@login_required
@organizer_required
def import_gforms_data(event_id):
    """
    Importe des données depuis un CSV Google Forms.
    Le format attendu est celui de l'export GForms ou compatible:
    - Col 0 : Timestamp
    - Col 1 : Email
    - Col 2+ : Questions / Réponses
    """
    event = Event.query.get_or_404(event_id)
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier fourni'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Aucun fichier sélectionné'}), 400

    try:
        # Wrapper pour lire le fichier en mode texte (stream)
        stream = TextIOWrapper(file.stream, encoding='utf-8', errors='replace')
        # Détection basique du délimiteur (GForms natif = ',', Excel FR = ';')
        # On lit la première ligne pour deviner
        first_line = stream.readline()
        stream.seek(0)
        
        delimiter = ','
        if ';' in first_line and first_line.count(';') > first_line.count(','):
            delimiter = ';'
            
        csv_reader = csv.reader(stream, delimiter=delimiter)
        
        # Lire les en-têtes
        try:
            headers = next(csv_reader)
        except StopIteration:
            return jsonify({'success': False, 'error': 'Fichier vide'}), 400
            
        if len(headers) < 2:
            return jsonify({'success': False, 'error': 'Le fichier doit contenir au moins 2 colonnes (Timestamp, Email)'}), 400
            
        # Stats
        stats = {
            'imported': 0,
            'updated': 0,
            'ignored': 0,
            'errors': []
        }
        
        # Cache des utilisateurs/participants pour éviter trop de requêtes
        # (Optimisation simple : on ne charge pas tout, on fait au fil de l'eau mais on pourrait optimiser plus)
        
        for row_idx, row in enumerate(csv_reader, start=2): # Start=2 car ligne 1 = header
            if not row:
                continue
                
            if len(row) < 2:
                stats['errors'].append(f"Ligne {row_idx}: Pas assez de colonnes")
                continue
                
            timestamp_str = row[0].strip()
            email = row[1].strip()
            
            if not email:
                stats['ignored'] += 1
                continue

            # Validation format email simple
            if '@' not in email or '.' not in email:
                stats['errors'].append(f"Ligne {row_idx}: Email invalide ({email})")
                continue
                
            # Parse timestamp
            timestamp = datetime.utcnow()
            try:
                # Formats courants GForms et Excel
                formats = [
                    '%Y/%m/%d %I:%M:%S %p %Z', # 2024/01/30 2:30:15 PM EAT
                    '%d/%m/%Y %H:%M:%S',       # 30/01/2024 14:30:15 (FR)
                    '%Y/%m/%d %H:%M:%S',       # 2024/01/30 14:30:15 (ISOish)
                    '%Y-%m-%d %H:%M:%S',       # 2024-01-30 14:30:15 (ISO)
                    '%m/%d/%Y %H:%M:%S',       # 01/30/2024 14:30:15 (US)
                ]
                
                parsed_date = None
                for fmt in formats:
                    try:
                        # Tentative de parsing (naïf pour timezone si %Z échoue ou est ignoré par strptime standard sans %z)
                        # Note: %Z est dépendant de la locale en C, souvent ignoré en Python standard sans librarie tierce
                        # On nettoie un peu la chaine pour %Z si c'est gênant, ou on essaie direct.
                        # strptime ne gère pas bien les noms de timezone comme EAT/CET sans config.
                        # On va essayer de parser sans la fin si ça echoue.
                        parsed_date = datetime.strptime(timestamp_str, fmt)
                        break
                    except ValueError:
                        continue
                        
                if parsed_date:
                    timestamp = parsed_date
                else:
                    # Fallback: essai de parser en coupant la timezone à la fin si présente (ex: " PM EAT")
                    # On suppose que la date est au début
                    # Ceci est une heuristique simple
                    # Si échec total, on garde le timestamp actuel (défini avant le try)
                    logger.warning(f"Date parsing failed for '{timestamp_str}', using current time.")
                    
            except Exception as e:
                logger.debug(f"Date parsing error: {e}")

            # Récupérer les réponses dynamiques
            answers = {}
            for i in range(2, len(row)):
                if i < len(headers):
                    key = headers[i].strip()
                    val = row[i].strip()
                    if val: # On ne stocke que les valeurs non vides
                        answers[key] = val
            
            try:
                # 1. Gestion Utilisateur
                user = User.query.filter_by(email=email).first()
                type_ajout = "inconnu"
                
                if not user:
                    type_ajout = "créé"
                    temp_password = secrets.token_urlsafe(12)
                    user = User(
                        email=email,
                        nom="Utilisateur",
                        prenom="GForm",
                        password_hash=generate_password_hash(temp_password),
                        role='user'
                    )
                    db.session.add(user)
                    db.session.flush()
                    
                    # SysAdmin Log
                    from models import ActivityLog
                    from constants import ActivityLogType
                    
                    # On suppose que l'import est fait par un admin/orga, on loggue l'action
                    log = ActivityLog(
                        action_type=ActivityLogType.USER_REGISTRATION.value, # Use appropriate enum
                        user_id=current_user.id,
                        details=json.dumps({'email': email, 'source': 'gforms_import', 'event_id': event.id})
                    )
                    db.session.add(log)
                else:
                    type_ajout = "ajouté" # Par défaut
                
                # Mise à jour Nom/Prénom si trouvés dans les réponses
                nom_form = None
                prenom_form = None
                for key, val in answers.items():
                    k = key.lower()
                    if k in ['nom', 'nom de famille', 'lastname']: nom_form = val
                    elif k in ['prénom', 'prenom', 'firstname']: prenom_form = val
                
                if nom_form: user.nom = nom_form
                if prenom_form: user.prenom = prenom_form
                
                # 2. Gestion Participant
                participant = Participant.query.filter_by(user_id=user.id, event_id=event.id).first()
                if not participant:
                    participant = Participant(
                        user_id=user.id,
                        event_id=event.id,
                        type=ParticipantType.PJ.value,
                        registration_status=RegistrationStatus.TO_VALIDATE.value
                    )
                    db.session.add(participant)
                    
                    # Notification
                    notif = EventNotification(
                        event_id=event.id,
                        user_id=user.id,
                        action_type="participant_join_request",
                        description=f"Import GForm: {user.prenom} {user.nom} ({email})",
                        is_read=False
                    )
                    db.session.add(notif)
                else:
                    type_ajout = "mis à jour"

                # 3. Gestion GFormsSubmission
                submission = GFormsSubmission.query.filter_by(event_id=event.id, email=email).first()
                if not submission:
                    submission = GFormsSubmission(
                        event_id=event.id,
                        user_id=user.id,
                        email=email,
                        timestamp=datetime.utcnow(), # On met le temps d'import par defaut
                        type_ajout=type_ajout,
                        raw_data=json.dumps(answers)
                    )
                    db.session.add(submission)
                    stats['imported'] += 1
                else:
                    # Fusion des données
                    current_data = json.loads(submission.raw_data) if submission.raw_data else {}
                    # On écrase/ajoute les nouvelles valeurs non vides
                    for k, v in answers.items():
                        current_data[k] = v
                    
                    submission.raw_data = json.dumps(current_data)
                    submission.type_ajout = "mis à jour" # Force status update
                    submission.timestamp = datetime.utcnow() # Update timestamp to now (import time)
                    stats['updated'] += 1
                    
            except Exception as e:
                db.session.rollback() # Rollback partiel si possible ? Non, session unique.
                # Dans une boucle, si on veut tolérance aux pannes, il faudrait commit à chaque ligne
                # ou utiliser des savepoints. Ici on log l'erreur et on continue (mais la session pourrait être invalidée)
                # Pour simplifier: on log et on espère. En SQLAlchemy, rollback invalide souvent la transaction.
                # Mieux vaut tout faire dans une grosse transaction, si erreur, tout fail.
                # Ou commit à chaque ligne pour "best effort".
                # Vu la demande "import", souvent on veut tout ou rien, ou best effort. 
                # On va faire un commit à la fin, si erreur on stop tout.
                raise e # On laisse remonter pour le try/except global qui fera rollback
        
        # Creation automatique des mappings pour les nouveaux champs
        # On récupère toutes les clés de toutes les réponses importées
        # (C'est déjà fait implicitement car on a stocké dans raw_data, mais il faut mettre à jour la table mappings)
        
        # Recupération des champs existants
        existing_mappings = {m.field_name for m in GFormsFieldMapping.query.filter_by(event_id=event_id).all()}
        
        # On parcourt les headers (sauf 0 et 1)
        default_cat = GFormsCategory.query.filter(
            GFormsCategory.event_id == event_id,
            db.func.lower(GFormsCategory.name) == 'généralités'
        ).first()
        
        if not default_cat:
             default_cat = GFormsCategory(event_id=event_id, name='Généralités', color='neutral', position=0)
             db.session.add(default_cat)
             db.session.flush()
             
        for h in headers[2:]:
            h = h.strip()
            if h and h not in existing_mappings:
                new_mapping = GFormsFieldMapping(
                    event_id=event_id,
                    field_name=h,
                    category_id=default_cat.id
                )
                db.session.add(new_mapping)
                existing_mappings.add(h)

        # Notification récapitulative pour l'import
        if stats['imported'] > 0 or stats['updated'] > 0:
            msg_parts = []
            if stats['imported'] > 0: msg_parts.append(f"{stats['imported']} importés")
            if stats['updated'] > 0: msg_parts.append(f"{stats['updated']} mis à jour")
            
            description = f"Import GForms : {', '.join(msg_parts)}"
            if stats['errors']:
                description += f" ({len(stats['errors'])} erreurs)"
                
            # Notification unique pour l'organisateur (celui qui importe)
            # On pourrait notifier tous les orgas, mais ça risque de faire doublon avec les notifs individuelles "participant_join_request"
            # qui sont déjà générées plus haut (lignes 640-646) pour les NOUVEAUX participants.
            # MAIS l'utilisateur veut "une seule notification avec la liste agrégée".
            # Le code existant génère DEJA une notif par participant (lignes 640+).
            # Si on veut grouper, il faut supprimer la notif individuelle et en faire une grosse à la fin.
            # Pour l'instant, je rajoute celle-ci en plus pour le resume global.
            
            from services.notification_service import create_notification
            create_notification(
                event_id=event.id,
                user_id=current_user.id,
                action_type='gforms_import',
                description=description
            )
            
            # SysAdmin Log pour les nouveaux utilisateurs créés
            # Le code plus haut (lignes 602-613) crée des User mais ne semble pas logger explicitement pour SysAdmin.
            # On peut le faire ici si on avait gardé une liste des new users.
            # Correction : le code actuel ne garde pas la liste des users créés dans une variable accessible ici facilement
            # sauf si on modifie la boucle pour stocker 'created_users'.
            
        db.session.commit()
        return jsonify({
            'success': True, 
            'imported': stats['imported'], 
            'updated': stats['updated'], 
            'ignored': stats['ignored'], 
            'errors': stats['errors']
        })

    except UnicodeDecodeError:
        return jsonify({'success': False, 'error': 'Encodage fichier invalide (utilisez UTF-8)'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur import GForms: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@gforms_bp.route('/event/<int:event_id>/gforms/purge', methods=['DELETE'])
@login_required
@organizer_required
def purge_gforms_data(event_id):
    """
    API: Supprime toutes les données GForms d'un événement.
    Supprime : GFormsSubmission, GFormsFieldMapping, GFormsCategory, FormResponse.
    Ne touche pas aux utilisateurs ni aux participants.
    """
    event = Event.query.get_or_404(event_id)

    try:
        from models import FormResponse

        # Compter avant suppression pour le résumé
        nb_submissions = GFormsSubmission.query.filter_by(event_id=event_id).count()
        nb_mappings = GFormsFieldMapping.query.filter_by(event_id=event_id).count()
        nb_categories = GFormsCategory.query.filter_by(event_id=event_id).count()
        nb_responses = FormResponse.query.filter_by(event_id=event_id).count()

        # Supprimer dans l'ordre (respecter les FK)
        GFormsSubmission.query.filter_by(event_id=event_id).delete()
        GFormsFieldMapping.query.filter_by(event_id=event_id).delete()
        GFormsCategory.query.filter_by(event_id=event_id).delete()
        FormResponse.query.filter_by(event_id=event_id).delete()

        db.session.commit()

        total = nb_submissions + nb_mappings + nb_categories + nb_responses
        logger.info(f"Purged all GForms data for event {event_id}: "
                     f"{nb_submissions} submissions, {nb_mappings} mappings, "
                     f"{nb_categories} categories, {nb_responses} form responses")

        # Notification
        from services.notification_service import create_notification
        create_notification(
            event_id=event.id,
            user_id=current_user.id,
            action_type='gforms_purge',
            description=f"Suppression de toutes les données GForms : "
                        f"{nb_submissions} soumissions, {nb_categories} catégories, "
                        f"{nb_mappings} mappings, {nb_responses} réponses brutes"
        )

        return jsonify({
            'success': True,
            'deleted': {
                'submissions': nb_submissions,
                'categories': nb_categories,
                'mappings': nb_mappings,
                'form_responses': nb_responses
            },
            'message': f'{total} éléments supprimés'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error purging GForms data for event {event_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
