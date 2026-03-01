"""
Service d'analyse des traits de caractère.

Orchestre les deux appels API asynchrones :
1. PDF → Texte (service pdf2txt)
2. Texte → Traits de caractère (service character)

Les résultats sont reçus via des webhooks dédiés.
"""

import re
import json
import logging
import requests
from flask import current_app, url_for

logger = logging.getLogger(__name__)


def _sanitize_id_texte(name):
    """
    Transforme le nom du personnage en identifiant alphanumérique.
    Supprime tous les caractères non alphanumériques et les espaces.
    """
    return re.sub(r'[^a-zA-Z0-9]', '', name)


def _build_webhook_base_url():
    """
    Construit l'URL de base pour les webhooks à partir de la config deploy.
    Retourne par ex: https://minimoi.mynetgear.com/gnole_dev
    """
    machine_name = current_app.config.get('DEPLOY_MACHINE_NAME', '')
    app_prefix = current_app.config.get('DEPLOY_APP_PREFIX', '/')

    if not machine_name:
        # Fallback: utiliser le SERVER_NAME ou localhost
        server = current_app.config.get('SERVER_NAME', 'localhost:5000')
        scheme = 'https' if current_app.config.get('PREFERRED_URL_SCHEME') == 'https' else 'http'
        return f"{scheme}://{server}"

    # Construire l'URL à partir de la config deploy
    prefix = app_prefix.rstrip('/')
    return f"https://{machine_name}{prefix}"


def request_pdf_extraction(role):
    """
    Envoie une requête au service pdf2txt pour extraire le texte du PDF.

    Args:
        role: Instance du modèle Role avec pdf_url renseigné

    Returns:
        tuple: (success: bool, message: str)
    """
    api_url = current_app.config.get('PDF2TXT_API_URL')
    token = current_app.config.get('PDF2TXT_TOKEN')

    if not api_url or not token:
        logger.error("❌ Configuration pdf2txt manquante (api_url ou token)")
        return False, "Configuration pdf2txt manquante"

    if not role.pdf_url:
        return False, "Aucun PDF associé à ce rôle"

    id_texte = _sanitize_id_texte(role.name)
    base_url = _build_webhook_base_url()
    webhook_url = f"{base_url}/webhook/pdf2txt"

    logger.info(f"📄 Envoi de la requête pdf2txt pour le rôle '{role.name}' "
                f"(id_texte={id_texte}, pdf_url={role.pdf_url})")
    logger.info(f"   Webhook URL: {webhook_url}")

    try:
        response = requests.post(
            api_url,
            headers={'token': token},
            data={
                'id_texte': id_texte,
                'webhook_url': webhook_url,
                'ia_validate': 'true',
                'pdf_url': role.pdf_url
            },
            timeout=30
        )

        if response.status_code in (200, 201, 202):
            logger.info(f"✅ Requête pdf2txt envoyée avec succès pour '{role.name}' "
                        f"(status={response.status_code})")
            return True, "Extraction PDF lancée"
        else:
            error_msg = f"Erreur pdf2txt: HTTP {response.status_code} - {response.text[:200]}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg

    except requests.Timeout:
        logger.error(f"❌ Timeout lors de l'appel pdf2txt pour '{role.name}'")
        return False, "Timeout lors de l'appel au service pdf2txt"
    except requests.RequestException as e:
        logger.error(f"❌ Erreur réseau pdf2txt pour '{role.name}': {e}")
        return False, f"Erreur réseau: {str(e)}"


def request_character_analysis(text_url, request_id):
    """
    Envoie une requête au service character pour analyser les traits.

    Args:
        text_url: URL du texte extrait (retournée par pdf2txt)
        request_id: Identifiant de la requête (id_texte du PDF)

    Returns:
        tuple: (success: bool, message: str)
    """
    api_url = current_app.config.get('CHARACTER_API_URL')
    token = current_app.config.get('CHARACTER_TOKEN')

    if not api_url or not token:
        logger.error("❌ Configuration character manquante (api_url ou token)")
        return False, "Configuration character manquante"

    base_url = _build_webhook_base_url()
    webhook_url = f"{base_url}/webhook/character"

    logger.info(f"🧠 Envoi de la requête character pour request_id='{request_id}' "
                f"(text_url={text_url})")
    logger.info(f"   Webhook URL: {webhook_url}")

    try:
        response = requests.post(
            api_url,
            headers={
                'token': token,
                'Content-Type': 'application/json',
                'webhook': webhook_url
            },
            json={
                'text': text_url,
                'request_id': request_id
            },
            timeout=30
        )

        if response.status_code in (200, 201, 202):
            logger.info(f"✅ Requête character envoyée avec succès pour '{request_id}' "
                        f"(status={response.status_code})")
            return True, "Analyse des traits lancée"
        else:
            error_msg = f"Erreur character: HTTP {response.status_code} - {response.text[:200]}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg

    except requests.Timeout:
        logger.error(f"❌ Timeout lors de l'appel character pour '{request_id}'")
        return False, "Timeout lors de l'appel au service character"
    except requests.RequestException as e:
        logger.error(f"❌ Erreur réseau character pour '{request_id}': {e}")
        return False, f"Erreur réseau: {str(e)}"
