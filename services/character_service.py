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
    Construit l'URL de base pour les webhooks à partir des variables d'environnement.
    Utilise APP_PUBLIC_HOST et APPLICATION_ROOT (déjà présents dans le .env).
    Retourne par ex: https://minimoi.mynetgear.com/gnole_dev
    """
    import os
    public_host = os.environ.get('APP_PUBLIC_HOST', '')
    app_root = current_app.config.get('APPLICATION_ROOT', '/')

    if not public_host:
        # Fallback: utiliser le SERVER_NAME ou localhost
        server = current_app.config.get('SERVER_NAME', 'localhost:5000')
        scheme = 'https' if current_app.config.get('PREFERRED_URL_SCHEME') == 'https' else 'http'
        return f"{scheme}://{server}"

    # Construire l'URL à partir de APP_PUBLIC_HOST + APPLICATION_ROOT
    prefix = app_root.rstrip('/')
    scheme = 'https' if 'https' in public_host else 'http'
    host = public_host.replace('https://', '').replace('http://', '')
    return f"{scheme}://{host}{prefix}"


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

    # Construction d'un id_texte unique et explicite :
    # nom_sanitisé + ID rôle + ID événement + APPLICATION_ROOT (sans slashes)
    id_texte_base = _sanitize_id_texte(role.name)
    app_root = current_app.config.get('APPLICATION_ROOT', '/').replace('/', '')
    id_texte = f"{id_texte_base}_{role.id}_{role.event_id}_{app_root}" if app_root else f"{id_texte_base}_{role.id}_{role.event_id}"
    base_url = _build_webhook_base_url()
    webhook_url = f"{base_url}/webhook/pdf2txt"

    request_headers = {'token': token}
    request_data = {
        'id_texte': id_texte,
        'webhook_url': webhook_url,
        'ia_validate': 'true',
        'pdf_url': role.pdf_url
    }

    # Masquer le token dans les logs
    safe_headers = {k: (v[:8] + '***' if k.lower() == 'token' else v) for k, v in request_headers.items()}

    logger.info(f"📄 ═══ APPEL PDF2TXT ═══")
    logger.info(f"   URL API:      {api_url}")
    logger.info(f"   Rôle:         '{role.name}' (id_texte={id_texte})")
    logger.info(f"   PDF URL:      {role.pdf_url}")
    logger.info(f"   Webhook URL:  {webhook_url}")
    logger.info(f"   Headers:      {safe_headers}")
    logger.info(f"   Data:         {request_data}")

    try:
        response = requests.post(
            api_url,
            headers=request_headers,
            data=request_data,
            timeout=30
        )

        logger.info(f"   ─── RÉPONSE PDF2TXT ───")
        logger.info(f"   Status:       {response.status_code}")
        logger.info(f"   Headers:      {dict(response.headers)}")
        logger.info(f"   Body:         {response.text[:500]}")

        if response.status_code in (200, 201, 202):
            logger.info(f"✅ Requête pdf2txt envoyée avec succès pour '{role.name}'")
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

    request_headers = {
        'token': token,
        'Content-Type': 'application/json',
        'webhook': webhook_url
    }
    request_body = {
        'text': text_url,
        'request_id': request_id
    }

    # Masquer le token et le webhook dans les logs
    safe_headers = {k: (v[:8] + '***' if k.lower() in ('token', 'webhook') else v)
                    for k, v in request_headers.items()}

    logger.info(f"🧠 ═══ APPEL CHARACTER ═══")
    logger.info(f"   URL API:      {api_url}")
    logger.info(f"   Request ID:   {request_id}")
    logger.info(f"   Text URL:     {text_url}")
    logger.info(f"   Webhook URL:  {webhook_url}")
    logger.info(f"   Headers:      {safe_headers}")
    logger.info(f"   Body JSON:    {json.dumps(request_body)}")

    try:
        response = requests.post(
            api_url,
            headers=request_headers,
            json=request_body,
            timeout=30
        )

        logger.info(f"   ─── RÉPONSE CHARACTER ───")
        logger.info(f"   Status:       {response.status_code}")
        logger.info(f"   Headers:      {dict(response.headers)}")
        logger.info(f"   Body:         {response.text[:500]}")

        if response.status_code in (200, 201, 202):
            logger.info(f"✅ Requête character envoyée avec succès pour '{request_id}'")
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
