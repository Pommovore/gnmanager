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

@webhook_bp.route('/api/webhook/gform', methods=['POST'])
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
            
        db.session.commit()
        
        return jsonify({
            "status": "success", 
            "action": action, 
            "id": form_response.id
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
