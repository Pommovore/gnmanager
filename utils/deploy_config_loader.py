"""
Utilitaire de chargement de la configuration de déploiement.

Charge les paramètres depuis deploy_config_<mode>.yaml pour rendre
accessibles les URLs et tokens des services externes (pdf2txt, character)
dans app.config au runtime.
"""

import os
import logging
import yaml

logger = logging.getLogger(__name__)


def load_deploy_config(app):
    """
    Charge la configuration de déploiement dans app.config.

    Cherche le fichier de config selon GN_ENVIRONMENT (dev, test, prod).
    Fallback sur config/deploy_config.yaml si le fichier spécifique n'existe pas.
    Injecte les clés PDF2TXT_* et CHARACTER_* dans app.config.
    """
    env = os.environ.get('GN_ENVIRONMENT', 'dev')
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Chercher le fichier de config spécifique au mode
    config_path = os.path.join(base_dir, 'config', f'deploy_config_{env}.yaml')
    if not os.path.exists(config_path):
        # Fallback sur le fichier générique
        config_path = os.path.join(base_dir, 'config', 'deploy_config.yaml')

    if not os.path.exists(config_path):
        logger.warning("⚠️  Aucun fichier deploy_config trouvé. "
                       "Les services pdf2txt et character ne seront pas configurés.")
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement de {config_path}: {e}")
        return

    # Injection des paramètres pdf2txt
    pdf2txt = config.get('pdf2txt', {})
    if pdf2txt:
        app.config['PDF2TXT_API_URL'] = pdf2txt.get('api_url', '')
        app.config['PDF2TXT_TOKEN'] = pdf2txt.get('token', '')
        logger.info(f"✅ Configuration pdf2txt chargée depuis {config_path}")

    # Injection des paramètres character
    character = config.get('character', {})
    if character:
        app.config['CHARACTER_API_URL'] = character.get('api_url', '')
        app.config['CHARACTER_TOKEN'] = character.get('token', '')
        logger.info(f"✅ Configuration character chargée depuis {config_path}")

    # Injection du deploy (pour construire les webhook URLs)
    deploy = config.get('deploy', {})
    if deploy:
        machine_name = deploy.get('machine_name', '')
        app_prefix = deploy.get('app_prefix', '/')
        app.config['DEPLOY_MACHINE_NAME'] = machine_name
        app.config['DEPLOY_APP_PREFIX'] = app_prefix
        logger.info(f"✅ Configuration deploy chargée: {machine_name}{app_prefix}")
