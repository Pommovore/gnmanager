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
    assert 'Accueil' in data


def test_403_access_forbidden(app, client):
    """Test 403 error page is displayed when access is forbidden."""
    # Create a route that aborts with 403
    @app.route('/trigger-403')
    def trigger_403():
        abort(403)
        
    response = client.get('/trigger-403')
    assert response.status_code == 403
    data = response.data.decode('utf-8')
    assert '403' in data
    assert 'Accès interdit' in data or 'non autorisé' in data
    assert 'GN Manager' in data


def test_500_internal_server_error(app, client):
    """Test 500 error page is displayed when an exception occurs."""
    # Create a route that raises an exception
    @app.route('/trigger-500')
    def trigger_500():
        raise Exception("Simulated server error")
        
    # In testing mode, Flask usually propagates exceptions. 
    # We might need to handle this to see the 500 page or just verify status if propagation is off.
    # However, testing the actual 500 template rendering often requires PROPAGATE_EXCEPTIONS=False 
    # or using app.test_client() in a specific way.
    # For now, we'll try catching the exception or configuring the app temporarily if needed.
    
    # Configure app to NOT propagate exceptions for this test, so the error handler catches it
    app.config['PROPAGATE_EXCEPTIONS'] = False
    
    response = client.get('/trigger-500')
    assert response.status_code == 500
    data = response.data.decode('utf-8')
    assert '500' in data
    assert 'Erreur serveur' in data or 'interne' in data
    
    # Restore config
    app.config['PROPAGATE_EXCEPTIONS'] = True
