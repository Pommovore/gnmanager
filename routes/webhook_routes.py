import os
import json
import logging
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from models import db, FormResponse, Event, User, Participant, GFormsSubmission, GFormsCategory, GFormsFieldMapping, EventNotification
from extensions import csrf
from werkzeug.security import generate_password_hash
import secrets
from constants import RegistrationStatus, ParticipantType

# Création du Blueprint
webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

def verify_token():
    """
    Vérifie le token d'authentification dans le header Authorization.
    Retourne l'objet Event correspondant si valide, sinon None.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        # Compatibility/Legacy check using env var if header missing? No, enforce header.
        return None
    
    # Format attendu: "Bearer <token>"
    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return None
        
    # Vérification contre la base de données (Event.webhook_secret)
    event = Event.query.filter_by(webhook_secret=token).first()
    
    if event:
        return event
        
    # Fallback legacy (env var) si besoin, mais on passe au per-event.
    return None

@webhook_bp.route('/api/webhook/gform', methods=['POST'])
@csrf.exempt
def gform_webhook():
    """
    Endpoint pour recevoir les données de Google Forms via Apps Script.
    Attend un JSON:
    {
      "responseId": "...",
      "formId": "...", (optionnel)
      "email": "...", (optionnel)
      "timestamp": "...",
      "answers": { ... }
    }
    """
    # 1. Sécurité
    event = verify_token()
    if not event:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400
            
        response_id = data.get('responseId')
        if not response_id:
            return jsonify({"error": "Missing responseId"}), 400
            
        # 2. Upsert Logic (FormResponse - Legacy)
        form_response = FormResponse.query.filter_by(response_id=response_id).first()
        
        if form_response:
            # Update
            logger.info(f"Updating FormResponse {response_id}")
            form_response.answers = json.dumps(data.get('answers', {}))
            form_response.respondent_email = data.get('email')
            form_response.form_id = data.get('formId') # Update form_id just in case
            form_response.updated_at = datetime.utcnow()
            action = "updated"
        else:
            # Insert
            logger.info(f"Creating new FormResponse {response_id}")
            form_response = FormResponse(
                response_id=response_id,
                form_id=data.get('formId'),
                event_id=event.id,
                respondent_email=data.get('email'),
                answers=json.dumps(data.get('answers', {})),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(form_response)
            action = "created"
            
        db.session.flush() # Ensure ID is available
            
        # ---------------------------------------------------------
        # Nouvelle logique : Inscription/Mise à jour du Participant
        # ---------------------------------------------------------
        email = data.get('email')
        user = None
        participant = None
        type_ajout = "inconnu"
        
        if email:
            logger.info(f"Processing email: {email}") # DEBUG LOG
            # 1. Identifier ou Créer l'Utilisateur
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.info(f"Creating new User for email {email}")
                type_ajout = "créé"
                # Mot de passe aléatoire (l'utilisateur devra le reset)
                temp_password = secrets.token_urlsafe(12)
                user = User(
                    email=email,
                    nom="Utilisateur", # Placeholder
                    prenom="GForm",    # Placeholder
                    password_hash=generate_password_hash(temp_password),
                    role='user',
                    is_banned=False,
                    is_deleted=False
                )
                db.session.add(user)
                db.session.flush() # Pour avoir l'ID
            else:
                 logger.info(f"Found existing User ID: {user.id}") # DEBUG LOG
                 type_ajout = "ajouté" # Par défaut si user existe
            
            # 2. Identifier ou Créer le Participant
            participant = Participant.query.filter_by(user_id=user.id, event_id=event.id).first()
            if not participant:
                logger.info(f"Registering User {user.id} to Event {event.id}")
                participant = Participant(
                    user_id=user.id,
                    event_id=event.id,
                    type=ParticipantType.PJ.value, # Défaut
                    registration_status=RegistrationStatus.TO_VALIDATE.value, # "À valider"
                    role_communicated=False,
                    role_received=False
                )
                db.session.add(participant)
                db.session.flush()
            else:
                 logger.info(f"Found existing Participant ID: {participant.id}") # DEBUG LOG
                 type_ajout = "mis à jour" # Si participant existe déjà
            
            # 3. Traitement de l'identité (Nom/Prénom)
            answers = data.get('answers', {})
            nom_form = None
            prenom_form = None

            # Chercher dans les réponses
            if isinstance(answers, dict):
                for key, val in answers.items():
                    key_lower = key.lower().strip()
                    if key_lower in ['nom', 'nom de famille', 'family name', 'lastname', 'last name']:
                        nom_form = str(val).strip()
                    elif key_lower in ['prénom', 'prenom', 'first name', 'firstname']:
                        prenom_form = str(val).strip()
            
            # Heuristique si non trouvé
            if not nom_form or not prenom_form:
                email_part = email.split('@')[0]
                if '.' in email_part:
                    parts = email_part.split('.')
                    if not prenom_form: prenom_form = parts[0].capitalize()
                    if not nom_form: nom_form = " ".join(parts[1:]).capitalize()
                else:
                    if not prenom_form: prenom_form = email_part.capitalize()
                    if not nom_form: nom_form = "Utilisateur"

            # Mise à jour de l'utilisateur
            if prenom_form: user.prenom = prenom_form
            if nom_form: user.nom = nom_form
            
            # 4. Création d'une Notification (uniquement pour les nouveaux ou ajouts)
            if type_ajout in ["créé", "ajouté"]:
                notif = EventNotification(
                    event_id=event.id,
                    user_id=user.id,
                    action_type="participant_join_request", # Utilisation d'un type existant pour compatibilité
                    description=f"Nouvelle inscription via Google Form: {user.prenom} {user.nom} ({email})",
                    created_at=datetime.utcnow(),
                    is_read=False
                )
                db.session.add(notif)

        # ---------------------------------------------------------
        # Nouvelle logique : GFormsSubmission & Field Mappings
        # ---------------------------------------------------------
        
        # 1. Créer/Mettre à jour GFormsSubmission
        if email:
            # Use email + event_id to find existing submission to allow merging
            g_submission = GFormsSubmission.query.filter_by(event_id=event.id, email=email).first()
            new_answers = data.get('answers', {})
            
            if not g_submission:
                 g_submission = GFormsSubmission(
                    event_id=event.id,
                    user_id=user.id if user else None,
                    email=email,
                    timestamp=datetime.utcnow(),
                    type_ajout=type_ajout,
                    form_response_id=form_response.id,
                    raw_data=json.dumps(new_answers)
                )
                 db.session.add(g_submission)
            else:
                # Merge logic: replace only if new data is not empty
                try:
                    current_data = json.loads(g_submission.raw_data) if g_submission.raw_data else {}
                except:
                    current_data = {}
                
                if isinstance(new_answers, dict):
                    for key, val in new_answers.items():
                        # check for "empty" values: None, empty string, empty list, empty dict
                        if val is not None and val != "" and val != [] and val != {}:
                            current_data[key] = val
                            
                g_submission.raw_data = json.dumps(current_data)
                g_submission.type_ajout = type_ajout
                g_submission.timestamp = datetime.utcnow()
                g_submission.form_response_id = form_response.id # Link to latest response
                if not g_submission.user_id and user:
                    g_submission.user_id = user.id
        
        # 2. Auto-detect fields and create mappings
        answers = data.get('answers', {})
        if isinstance(answers, dict):
            # Get default category (case-insensitive)
            default_cat = GFormsCategory.query.filter(
                GFormsCategory.event_id == event.id,
                db.func.lower(GFormsCategory.name) == 'généralités'
            ).first()
            if not default_cat:
                # Default creation should use nice capitalization
                default_cat = GFormsCategory(event_id=event.id, name='Généralités', color='neutral', position=0)
                db.session.add(default_cat)
                db.session.flush()
            
            existing_mappings = {m.field_name for m in GFormsFieldMapping.query.filter_by(event_id=event.id).all()}
            
            for field_name in answers.keys():
                if field_name not in existing_mappings:
                    new_mapping = GFormsFieldMapping(
                        event_id=event.id,
                        field_name=field_name,
                        category_id=default_cat.id
                    )
                    db.session.add(new_mapping)
                    existing_mappings.add(field_name) # Avoid duplicates in same transaction

        db.session.commit()
        logger.info("Transaction committed successfully")

        # ---------------------------------------------------------
        # Notification Discord
        # ---------------------------------------------------------
        if event.discord_webhook_url and email: # Only if email/user logic ran
             try:
                from services.discord_service import send_discord_notification
                
                # Préparer les champs pour Discord
                discord_fields = []
                # Limiter le nombre de champs pour éviter les limites Discord
                if isinstance(answers, dict):
                    for i, (q, a) in enumerate(answers.items()):
                        if i >= 20: break
                        val_str = str(a) if a is not None else ""
                        if len(val_str) > 1024:
                            val_str = val_str[:1021] + "..."
                        
                        discord_fields.append({
                            "name": q[:256],
                            "value": val_str,
                            "inline": False 
                        })
                
                user_data = {
                    'nom': user.nom if user else "Inconnu",
                    'prenom': user.prenom if user else "Inconnu",
                    'email': email
                }
                
                send_discord_notification(
                    webhook_url=event.discord_webhook_url,
                    event_name=event.name,
                    user_data=user_data,
                    registration_type="Inscription via Google Form",
                    extra_fields=discord_fields
                )
             except Exception as e_discord:
                 logger.error(f"Failed to send Discord notification: {e_discord}")

        return jsonify({
            "status": "success", 
            "action": action, 
            "id": form_response.id,
            "user_processed": bool(email)
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

