"""
Tests pour les routes de webhook (webhook_routes.py).

Couvre :
- Endpoint Google Forms webhook
- Authentification par token
- Création et mise à jour de FormResponse
- Gestion des erreurs
"""

import pytest
import json
from models import FormResponse, Event
from datetime import datetime, timedelta


class TestWebhookAuthentication:
    """Tests d'authentification du webhook."""
    
    def test_webhook_without_authorization_header(self, client):
        """Test webhook sans header Authorization."""
        response = client.post('/api/webhook/gform',
            json={'responseId': '123', 'answers': {}}
        )
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Unauthorized'
    
    def test_webhook_with_invalid_token_format(self, client):
        """Test webhook avec format de token invalide."""
        response = client.post('/api/webhook/gform',
            headers={'Authorization': 'InvalidFormat'},
            json={'responseId': '123', 'answers': {}}
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Unauthorized'
    
    def test_webhook_with_invalid_token(self, client):
        """Test webhook avec token invalide."""
        response = client.post('/api/webhook/gform',
            headers={'Authorization': 'Bearer invalid_token_12345'},
            json={'responseId': '123', 'answers': {}}
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Unauthorized'
    
    def test_webhook_with_valid_token(self, client, event_sample, db):
        """Test webhook avec token valide."""
        # Set webhook secret on event
        event_sample.webhook_secret = 'valid_secret_token_123'
        db.session.commit()
        
        response = client.post('/api/webhook/gform',
            headers={'Authorization': 'Bearer valid_secret_token_123'},
            json={
                'responseId': 'resp_123',
                'formId': 'form_456',
                'email': 'test@example.com',
                'timestamp': datetime.utcnow().isoformat(),
                'answers': {'question1': 'answer1'}
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['action'] == 'created'


class TestWebhookPayload:
    """Tests de validation du payload du webhook."""
    

    def test_webhook_without_response_id(self, client, event_sample, db):
        """Test webhook sans responseId."""
        event_sample.webhook_secret = 'token123'
        db.session.commit()
        
        response = client.post('/api/webhook/gform',
            headers={'Authorization': 'Bearer token123'},
            json={'formId': 'form_id', 'answers': {}}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'responseId' in data['error']


class TestFormResponseCreation:
    """Tests de création de FormResponse."""
    
    def test_create_new_form_response(self, client, event_sample, db):
        """Test de création d'une nouvelle réponse."""
        event_sample.webhook_secret = 'token_create'
        db.session.commit()
        
        payload = {
            'responseId': 'new_resp_001',
            'formId': 'form_001',
            'email': 'user@example.com',
            'timestamp': datetime.utcnow().isoformat(),
            'answers': {
                'Nom': 'Dupont',
                'Prénom': 'Jean',
                'Age': '25'
            }
        }
        
        response = client.post('/api/webhook/gform',
            headers={'Authorization': 'Bearer token_create'},
            json=payload
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['action'] == 'created'
        assert 'id' in data
        
        # Verify in database
        form_response = FormResponse.query.filter_by(response_id='new_resp_001').first()
        assert form_response is not None
        assert form_response.form_id == 'form_001'
        assert form_response.respondent_email == 'user@example.com'
        assert form_response.event_id == event_sample.id
        
        answers = json.loads(form_response.answers)
        assert answers['Nom'] == 'Dupont'
        assert answers['Prénom'] == 'Jean'
    
    def test_create_form_response_minimal_data(self, client, event_sample, db):
        """Test création avec données minimales (juste responseId)."""
        event_sample.webhook_secret = 'token_minimal'
        db.session.commit()
        
        response = client.post('/api/webhook/gform',
            headers={'Authorization': 'Bearer token_minimal'},
            json={
                'responseId': 'minimal_resp_001',
                'answers': {}
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['action'] == 'created'
        
        form_response = FormResponse.query.filter_by(response_id='minimal_resp_001').first()
        assert form_response is not None
        assert form_response.respondent_email is None
        assert form_response.form_id is None


class TestFormResponseUpdate:
    """Tests de mise à jour de FormResponse."""
    
    def test_update_existing_form_response(self, client, event_sample, db):
        """Test de mise à jour d'une réponse existante."""
        event_sample.webhook_secret = 'token_update'
        db.session.commit()
        
        # Create initial response
        initial_response = FormResponse(
            response_id='update_resp_001',
            form_id='form_001',
            event_id=event_sample.id,
            respondent_email='old@example.com',
            answers=json.dumps({'question1': 'old_answer'}),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(initial_response)
        db.session.commit()
        
        initial_id = initial_response.id
        
        # Send update via webhook
        update_payload = {
            'responseId': 'update_resp_001',
            'formId': 'form_002',  # Changed
            'email': 'new@example.com',  # Changed
            'answers': {'question1': 'new_answer', 'question2': 'another_answer'}
        }
        
        response = client.post('/api/webhook/gform',
            headers={'Authorization': 'Bearer token_update'},
            json=update_payload
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['action'] == 'updated'
        assert data['id'] == initial_id  # Same ID
        
        # Verify update in database
        db.session.refresh(initial_response)
        assert initial_response.form_id == 'form_002'
        assert initial_response.respondent_email == 'new@example.com'
        
        updated_answers = json.loads(initial_response.answers)
        assert updated_answers['question1'] == 'new_answer'
        assert updated_answers['question2'] == 'another_answer'
    
    def test_idempotent_webhook_calls(self, client, event_sample, db):
        """Test que plusieurs appels avec le même responseId sont idempotents."""
        event_sample.webhook_secret = 'token_idempotent'
        db.session.commit()
        
        payload = {
            'responseId': 'idempotent_001',
            'formId': 'form_001',
            'answers': {'q': 'a'}
        }
        
        # First call - create
        response1 = client.post('/api/webhook/gform',
            headers={'Authorization': 'Bearer token_idempotent'},
            json=payload
        )
        assert response1.status_code == 200
        data1 = response1.get_json()
        assert data1['action'] == 'created'
        
        # Second call - update (same data)
        response2 = client.post('/api/webhook/gform',
            headers={'Authorization': 'Bearer token_idempotent'},
            json=payload
        )
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['action'] == 'updated'
        assert data2['id'] == data1['id']
        
        # Verify only one record exists
        count = FormResponse.query.filter_by(response_id='idempotent_001').count()
        assert count == 1


class TestWebhookErrorHandling:
    """Tests de gestion des erreurs du webhook."""
    
    def test_webhook_with_database_error(self, client, event_sample, db, monkeypatch):
        """Test comportement avec erreur de base de données."""
        event_sample.webhook_secret = 'token_error'
        db.session.commit()
        
        # Mock db.session.commit to raise an exception
        def mock_commit():
            raise Exception("Database connection lost")
        
        monkeypatch.setattr(db.session, 'commit', mock_commit)
        
        response = client.post('/api/webhook/gform',
            headers={'Authorization': 'Bearer token_error'},
            json={
                'responseId': 'error_resp_001',
                'answers': {'q': 'a'}
            }
        )
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'Database connection lost' in data['error']
    
    def test_webhook_with_invalid_json_in_answers(self, client, event_sample, db):
        """Test avec des données valides (answers peut être n'importe quoi)."""
        event_sample.webhook_secret = 'token_json'
        db.session.commit()
        
        # Complex nested structure should work
        response = client.post('/api/webhook/gform',
            headers={'Authorization': 'Bearer token_json'},
            json={
                'responseId': 'complex_001',
                'answers': {
                    'nested': {
                        'data': [1, 2, 3],
                        'more': {'deep': 'value'}
                    }
                }
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
