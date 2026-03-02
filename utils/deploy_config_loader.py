"""
Utilitaire de chargement de la configuration des services externes.

Charge les paramètres depuis les variables d'environnement pour rendre
accessibles les URLs et tokens des services pdf2txt et character
dans app.config au runtime.

Variables d'environnement attendues :
- WEBHOOK_PDF2TXT_API_URL
- WEBHOOK_PDF2TXT_API_TOKEN
- WEBHOOK_CHARACTER_API_URL
- WEBHOOK_CHARACTER_API_TOKEN
"""

import os
import logging

logger = logging.getLogger(__name__)


def load_deploy_config(app):
    """
    Charge la configuration des services externes dans app.config
    depuis les variables d'environnement.
    """
    # Service pdf2txt
    pdf2txt_url = os.environ.get('WEBHOOK_PDF2TXT_API_URL', '')
    pdf2txt_token = os.environ.get('WEBHOOK_PDF2TXT_API_TOKEN', '')

    if pdf2txt_url and pdf2txt_token:
        app.config['PDF2TXT_API_URL'] = pdf2txt_url
        app.config['PDF2TXT_TOKEN'] = pdf2txt_token
        logger.info("✅ Configuration pdf2txt chargée depuis les variables d'environnement")
    else:
        logger.warning("⚠️  Variables WEBHOOK_PDF2TXT_API_URL / WEBHOOK_PDF2TXT_API_TOKEN "
                       "non définies. Le service pdf2txt ne sera pas disponible.")

    # Service character
    character_url = os.environ.get('WEBHOOK_CHARACTER_API_URL', '')
    character_token = os.environ.get('WEBHOOK_CHARACTER_API_TOKEN', '')

    if character_url and character_token:
        app.config['CHARACTER_API_URL'] = character_url
        app.config['CHARACTER_TOKEN'] = character_token
        logger.info("✅ Configuration character chargée depuis les variables d'environnement")
    else:
        logger.warning("⚠️  Variables WEBHOOK_CHARACTER_API_URL / WEBHOOK_CHARACTER_API_TOKEN "
                       "non définies. Le service character ne sera pas disponible.")
