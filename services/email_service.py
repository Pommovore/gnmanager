import os
import logging
from flask import url_for, current_app
from models import db, AccountValidationToken
from auth import send_email
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

def send_new_account_invitation(user, event):
    """
    Envoie un email d'invitation à un nouvel utilisateur créé automatiquement.
    Génère un token de validation de compte et l'envoie par email.
    
    Args:
        user (User): L'utilisateur nouvellement créé
        event (Event): L'événement concerné
        
    Returns:
        bool: True si l'email a été envoyé, False sinon
    """
    try:
        # Vérifier si un token existe déjà (éviter doublons si appelé plusieurs fois)
        # Mais ici on suppose un new user. 
        # On nettoie les vieux tokens si besoin ? Non, on crée un nouveau.
        
        token_str = str(uuid.uuid4())
        token = AccountValidationToken(token=token_str, email=user.email)
        db.session.add(token)
        # Note: Le commit doit être fait par l'appelant pour garantir l'atomicité de la transaction globale
        # Sauf si on veut que le token soit persisté indépendamment. 
        # Ici, l'appelant (webhook/import) gère la transaction user creation.
        # Si on commit ici, on risque de casser la transaction de l'appelant ou de committer un user partiel.
        # PROBLÈME : Si on ne commit pas, le token n'est pas en base, donc si l'utilisateur clique tout de suite...
        # MAIS send_email est lent.
        # SOLUTION : On flush pour avoir l'ID si besoin (pas besoin ici).
        # On laissera l'appelant committer le tout.
        
        # Générer l'URL de validation
        if os.environ.get('APP_PUBLIC_HOST'):
            valid_endpoint = url_for('auth.validate_account', token=token_str)
            validation_url = f"http://{os.environ['APP_PUBLIC_HOST']}{valid_endpoint}"
        else:
            validation_url = url_for('auth.validate_account', token=token_str, _external=True)
            
        event_name = event.name if event else "GN Manager"
        
        email_body = f"""
        <h3>Bienvenue sur GN Manager !</h3>
        <p>Votre compte a été créé automatiquement suite à votre inscription à l'événement <strong>{event_name}</strong>.</p>
        <p>Pour finaliser votre inscription et accéder aux informations de l'événement (fiches de rôle, casting, etc.), 
        veuillez activer votre compte et définir votre mot de passe en cliquant sur le lien ci-dessous :</p>
        <p><a href="{validation_url}" style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">Activer mon compte</a></p>
        <p><small>Si le bouton ne fonctionne pas, copiez ce lien : {validation_url}</small></p>
        """
        
        logger.info(f"Sending auto-invite email to {user.email} for event {event.id}")
        return send_email(user.email, f"Invitation : {event_name}", email_body)
        
    except Exception as e:
        logger.error(f"Error sending invitation email to {user.email}: {e}")
        return False
