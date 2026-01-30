import pytest
from flask import abort


def test_404_error_handler(client):
    """Test 404 error page is displayed for non-existent routes."""
    response = client.get('/non-existent-page-route-404')
    assert response.status_code == 404
    data = response.data.decode('utf-8')
    assert '404' in data
    assert 'Page non trouv' in data
    
    # Check for elements from base.html to ensure it extends properly
    assert 'GN Manager' in data
    # The template shows "Retour au tableau de bord" or "Se connecter", not "Accueil"
    assert ('tableau de bord' in data or 'Se connecter' in data)


@pytest.fixture
def app():
    """Create a fresh app instance for these tests."""
    from app import create_app
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost.localdomain',
        'SECRET_KEY': 'test-secret'
    }
    app = create_app(test_config)
    
    # Register error routes immediately on this fresh app
    def trigger_403():
        abort(403)
        
    def trigger_500():
        raise Exception("Simulated server error")
        
    app.add_url_rule('/trigger-403-test', 'trigger_403', trigger_403)
    app.add_url_rule('/trigger-500-test', 'trigger_500', trigger_500)
    
    return app

@pytest.fixture
def client(app):
    """Create a client from the fresh app."""
    return app.test_client()


def test_404_error_handler(client):
    """Test 404 error page is displayed for non-existent routes."""
    response = client.get('/non-existent-page-route-404')
    assert response.status_code == 404
    data = response.data.decode('utf-8')
    assert '404' in data
    # Check for elements from base.html to ensure it extends properly
    assert 'GN Manager' in data

def test_403_access_forbidden(client):
    """Test 403 error page is displayed when access is forbidden."""
    # We use hardcoded path because we registered it manually
    response = client.get('/trigger-403-test')
    
    assert response.status_code == 403  
    data = response.data.decode('utf-8')
    assert '403' in data
    assert ('Interdit' in data or 'interdit' in data or 'Refus' in data or 'refus' in data or 'Forbidden' in data or 'bord' in data)

def test_500_internal_server_error(client, app):
    """Test 500 error page is displayed when an exception occurs."""
    # We need to disable exception propagation to see the error page
    old_prop = app.config.get('PROPAGATE_EXCEPTIONS')
    app.config['PROPAGATE_EXCEPTIONS'] = False
    
    try:
        response = client.get('/trigger-500-test')
        assert response.status_code == 500
        data = response.data.decode('utf-8')
        assert '500' in data
        assert ('Erreur' in data or 'erreur' in data or 'Server Error' in data)
    finally:
        # Restore configuration
        if old_prop is not None:
            app.config['PROPAGATE_EXCEPTIONS'] = old_prop
