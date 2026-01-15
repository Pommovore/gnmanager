"""
Module d'authentification et utilitaires email pour GN Manager.

Ce module fournit:
- Génération de mots de passe aléatoires
- Envoi d'emails via SMTP (Brevo)
"""

import os
import random
import string
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration du logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def generate_password():
    """
    Génère un mot de passe de 9 caractères.
    
    Format: 4 lettres (majuscules/minuscules) suivies de 5 chiffres
    Exemple: AbCd12345
    
    Returns:
        str: Le mot de passe généré
    """
    letters = ''.join(random.choices(string.ascii_letters, k=4))
    digits = ''.join(random.choices(string.digits, k=5))
    return letters + digits


def send_email(to, subject, body):
    """
    Envoie un email via SMTP (Brevo).
    
    Args:
        to (str): Adresse email du destinataire
        subject (str): Sujet de l'email
        body (str): Corps de l'email au format HTML
        
    Returns:
        bool: True si l'envoi a réussi, False sinon
        
    Note:
        Nécessite les variables d'environnement suivantes:
        - MAIL_SERVER: Serveur SMTP
        - MAIL_PORT: Port SMTP (défaut: 587)
        - MAIL_USERNAME: Identifiant SMTP
        - MAIL_PASSWORD: Mot de passe SMTP
        - MAIL_DEFAULT_SENDER: Expéditeur par défaut (optionnel)
    """
    smtp_server = os.environ.get('MAIL_SERVER')
    smtp_port = int(os.environ.get('MAIL_PORT', 587))
    smtp_user = os.environ.get('MAIL_USERNAME')
    smtp_password = os.environ.get('MAIL_PASSWORD')
    smtp_sender = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@gnmanager.fr')
    
    # Vérification de la configuration SMTP
    if not smtp_user or not smtp_password:
        logger.error(f"[EMAIL ERROR] Configuration SMTP incomplète. Impossible d'envoyer à {to}")
        logger.info(f"[EMAIL FALLBACK]\nTo: {to}\nSubject: {subject}\nBody:\n{body}\n")
        return False

    # Construction du message MIME
    message = MIMEMultipart()
    message["From"] = f"GN Manager <{smtp_sender}>"
    message["To"] = to
    message["Subject"] = subject
    message.attach(MIMEText(body, "html", "utf-8"))

    try:
        # Connexion et envoi via SMTP avec TLS
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_sender, to, message.as_string().encode('utf-8'))
            
        logger.info(f"[EMAIL] Email envoyé avec succès à {to}")
        return True
        
    except Exception as e:
        logger.error(f"[EMAIL ERROR] Échec d'envoi à {to}: {e}")
        logger.info(f"[EMAIL FALLBACK]\nTo: {to}\nSubject: {subject}\nBody:\n{body}\n")
        return False
