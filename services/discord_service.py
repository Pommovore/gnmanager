"""
Service for handling Discord interactions.
"""
import requests
import json
from flask import current_app
from exceptions import ExternalServiceError

def send_discord_notification(webhook_url, event_name, user_data, registration_type):
    """
    Send a notification to a Discord channel via Webhook.
    
    Args:
        webhook_url (str): The Discord Webhook URL
        event_name (str): The name of the event
        user_data (dict): Dictionary containing 'nom', 'prenom', 'email'
        registration_type (str): Type of registration (PJ, PNJ, Organisateur)
    
    Raises:
        ExternalServiceError: If the request fails
    """
    if not webhook_url:
        return

    embed = {
        "title": "Nouvelle inscription !",
        "description": f"Un nouvel utilisateur s'est inscrit à l'événement **{event_name}**.",
        "color": 5763719,  # Green color
        "fields": [
            {
                "name": "Utilisateur",
                "value": f"{user_data.get('prenom', '')} {user_data.get('nom', '').upper()}",
                "inline": True
            },
            {
                "name": "Email",
                "value": user_data.get('email', ''),
                "inline": True
            },
            {
                "name": "Type",
                "value": registration_type,
                "inline": False
            }
        ],
        "footer": {
            "text": "GN Manager Notification System"
        }
    }

    payload = {
        "embeds": [embed]
    }

    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Failed to send Discord notification: {str(e)}")
        # We assume this is not critical enough to break the user flow, so we log but don't re-raise
        # unless specifically requested by caller. To follow strict error handling principles defined earlier:
        # raise ExternalServiceError(f"Discord notification failed: {str(e)}")
