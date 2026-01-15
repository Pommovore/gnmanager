"""
Point d'entrée principal de l'application GN Manager.

Ce module:
- Charge les variables d'environnement depuis le fichier .env
- Initialise l'application Flask
- Lance le serveur de développement
"""

import os
import logging
from dotenv import load_dotenv
from app import create_app

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    Fonction principale de démarrage de l'application.
    
    Charge la configuration depuis:
    1. Le fichier .env (si présent)
    2. Les variables d'environnement système
    
    Puis démarre le serveur Flask sur l'hôte et le port configurés.
    """
    # Charger les variables d'environnement depuis .env
    # (complète les variables système sans les écraser)
    load_dotenv()
    
    # Créer l'application Flask
    app = create_app()
    
    # Récupérer la configuration réseau
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    # Démarrer le serveur
    logger.info(f"Lancement de l'application sur {host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
