"""
Tests for Discord service integration.

Tests cover:
- Successful webhook notifications
- Network failures and timeouts
- Invalid webhook URLs
- Empty/missing webhook URLs
- Edge cases with user data
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from services.discord_service import send_discord_notification
from exceptions import ExternalServiceError


class TestDiscordNotifications:
    """Test suite for Discord webhook notifications."""
    
    def test_send_notification_success(self):
        """Test successful Discord notification."""
        with patch('services.discord_service.requests.post') as mock_post:
            # Setup mock
            mock_response = Mock()
            mock_response.status_code = 204
            mock_post.return_value = mock_response
            
            # Execute
            send_discord_notification(
                webhook_url="https://discord.com/api/webhooks/test",
                event_name="Test Event",
                user_data={'nom': 'Doe', 'prenom': 'John', 'email': 'john@example.com'},
                registration_type="PJ"
            )
            
            # Verify
            assert mock_post.called
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://discord.com/api/webhooks/test"
            assert 'Content-Type' in call_args[1]['headers']
            assert call_args[1]['timeout'] == 5
    
    def test_send_notification_with_empty_webhook_url(self):
        """Test that no request is made when webhook URL is empty."""
        with patch('services.discord_service.requests.post') as mock_post:
            send_discord_notification(
                webhook_url="",
                event_name="Test Event",
                user_data={'nom': 'Doe', 'prenom': 'John', 'email': 'john@example.com'},
                registration_type="PJ"
            )
            
            # No request should be made
            assert not mock_post.called
    
    def test_send_notification_with_none_webhook_url(self):
        """Test that no request is made when webhook URL is None."""
        with patch('services.discord_service.requests.post') as mock_post:
            send_discord_notification(
                webhook_url=None,
                event_name="Test Event",
                user_data={'nom': 'Doe', 'prenom': 'John', 'email': 'john@example.com'},
                registration_type="PJ"
            )
            
            # No request should be made
            assert not mock_post.called
    
    def test_send_notification_network_error(self, app):
        """Test handling of network errors."""
        with patch('services.discord_service.requests.post') as mock_post:
            # Simulate network error
            mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
            
            with app.app_context():
                # Should not raise exception (logs error instead)
                send_discord_notification(
                    webhook_url="https://discord.com/api/webhooks/test",
                    event_name="Test Event",
                    user_data={'nom': 'Doe', 'prenom': 'John', 'email': 'john@example.com'},
                    registration_type="PJ"
                )
    
    def test_send_notification_timeout(self, app):
        """Test handling of request timeout."""
        with patch('services.discord_service.requests.post') as mock_post:
            # Simulate timeout
            mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
            
            with app.app_context():
                # Should not raise exception (logs error instead)
                send_discord_notification(
                    webhook_url="https://discord.com/api/webhooks/test",
                    event_name="Test Event",
                    user_data={'nom': 'Doe', 'prenom': 'John', 'email': 'john@example.com'},
                    registration_type="PJ"
                )
    
    def test_send_notification_http_error(self, app):
        """Test handling of HTTP errors (4xx, 5xx)."""
        with patch('services.discord_service.requests.post') as mock_post:
            # Simulate 404 error
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
            mock_post.return_value = mock_response
            
            with app.app_context():
                # Should not raise exception (logs error instead)
                send_discord_notification(
                    webhook_url="https://discord.com/api/webhooks/invalid",
                    event_name="Test Event",
                    user_data={'nom': 'Doe', 'prenom': 'John', 'email': 'john@example.com'},
                    registration_type="PJ"
                )
    
    def test_send_notification_with_incomplete_user_data(self):
        """Test notification with missing user data fields."""
        with patch('services.discord_service.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 204
            mock_post.return_value = mock_response
            
            # User data with missing fields
            send_discord_notification(
                webhook_url="https://discord.com/api/webhooks/test",
                event_name="Test Event",
                user_data={'email': 'john@example.com'},  # Missing nom and prenom
                registration_type="PJ"
            )
            
            # Should still work, using empty strings for missing fields
            assert mock_post.called
    
    def test_send_notification_payload_structure(self):
        """Test that the webhook payload has the correct structure."""
        with patch('services.discord_service.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 204
            mock_post.return_value = mock_response
            
            send_discord_notification(
                webhook_url="https://discord.com/api/webhooks/test",
                event_name="My Amazing Event",
                user_data={'nom': 'Smith', 'prenom': 'Jane', 'email': 'jane@example.com'},
                registration_type="PNJ"
            )
            
            # Extract the payload from the call
            import json
            call_kwargs = mock_post.call_args[1]
            payload = json.loads(call_kwargs['data'])
            
            # Verify structure
            assert 'embeds' in payload
            assert len(payload['embeds']) == 1
            
            embed = payload['embeds'][0]
            assert embed['title'] == "Nouvelle inscription !"
            assert "My Amazing Event" in embed['description']
            assert embed['color'] == 5763719
            assert len(embed['fields']) == 3
            
            # Verify fields
            fields = {field['name']: field['value'] for field in embed['fields']}
            assert 'Utilisateur' in fields
            assert 'Jane SMITH' in fields['Utilisateur']
            assert fields['Email'] == 'jane@example.com'
            assert fields['Type'] == 'PNJ'
            
            # Verify footer
            assert embed['footer']['text'] == "GNôle Notification System"
    
    def test_send_notification_all_registration_types(self):
        """Test notifications for different registration types."""
        with patch('services.discord_service.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 204
            mock_post.return_value = mock_response
            
            for reg_type in ["PJ", "PNJ", "Organisateur"]:
                send_discord_notification(
                    webhook_url="https://discord.com/api/webhooks/test",
                    event_name="Test Event",
                    user_data={'nom': 'Doe', 'prenom': 'John', 'email': 'john@example.com'},
                    registration_type=reg_type
                )
            
            # Should be called 3 times
            assert mock_post.call_count == 3
    
    def test_send_notification_special_characters_in_names(self):
        """Test notification with special characters in user names."""
        with patch('services.discord_service.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 204
            mock_post.return_value = mock_response
            
            send_discord_notification(
                webhook_url="https://discord.com/api/webhooks/test",
                event_name="L'Événement d'été 2026",
                user_data={
                    'nom': "O'Brien", 
                    'prenom': 'François', 
                    'email': 'françois@example.com'
                },
                registration_type="PJ"
            )
            
            assert mock_post.called
            # Verify JSON encoding handles special characters
            import json
            call_kwargs = mock_post.call_args[1]
            payload_str = call_kwargs['data']
            # Should not raise exception
            payload = json.loads(payload_str)
            assert payload is not None
