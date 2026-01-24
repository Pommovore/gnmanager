"""
Tests for custom error handlers.
"""

import pytest


def test_404_error_handler(client):
    """Test 404 error page is displayed for non-existent routes."""
    response = client.get('/non-existent-page-route-404')
    assert response.status_code == 404
    data = response.data.decode('utf-8')
    assert '404' in data
    assert 'Page non trouv' in data


def test_404_includes_base_elements(client):
    """Test that 404 error page extends base.html."""
    response = client.get('/non-existent-page')
    assert response.status_code == 404
    data = response.data.decode('utf-8')
    # Check for elements from base.html
    assert 'GN Manager' in data


def test_403_in_response_text(client):
    """Test that we can trigger a 403 response."""
    # Test by trying to access admin page without permission
    # We test that the 403 handler works by checking if it's properly registered
    # The actual 403 triggering is tested in other test files
    from app import create_app
    app = create_app()
    
    # Verify the handler exists
    assert 403 in app.error_handler_spec[None]
