import os
import json
import logging
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from models import db, FormResponse

# Création du Blueprint
webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

from models import db, FormResponse, Event

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

from extensions import csrf

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
            
        # 2. Upsert Logic
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
            
        # ---------------------------------------------------------
        # Nouvelle logique : Inscription/Mise à jour du Participant
        # ---------------------------------------------------------
        from models import User, Participant
        from constants import RegistrationStatus, ParticipantType
        from werkzeug.security import generate_password_hash
        import secrets

        email = data.get('email')
        if email:
            logger.info(f"Processing email: {email}") # DEBUG LOG
            # 1. Identifier ou Créer l'Utilisateur
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.info(f"Creating new User for email {email}")
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
            
            # 3. Traitement des réponses pour global_comment
            answers = data.get('answers', {})
            logger.info(f"Processing {len(answers) if answers else 0} answers") # DEBUG LOG

            formatted_answers = []
            
            # On essaie d'être malin : si c'est un dict, on formate Key: Value
            # Si c'est une liste (cas rare via webhook GForm?), on join
            if isinstance(answers, dict):
                for key, value in answers.items():
                    # Nettoyage basique
                    val_str = str(value) if value is not None else ""
                    formatted_answers.append(f"{key}: {val_str}")
            else:
                formatted_answers.append(str(answers))
            
            new_comment_content = "\n".join(formatted_answers)
            timestamp_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
            header = f"\n\n--- Import GForm ({timestamp_str}) ---\n"
            
            logger.info(f"Updating global_comment for Participant {participant.id}") # DEBUG LOG

            if participant.global_comment:
                participant.global_comment += header + new_comment_content
            else:
                participant.global_comment = header.strip() + "\n" + new_comment_content
        else:
            logger.warning("No email found in webhook payload - skipping User/Participant processing") # DEBUG LOG
        
        db.session.commit()
        logger.info("Transaction committed successfully") # DEBUG LOG
        
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
