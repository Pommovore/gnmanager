# GNôle Tests

This directory contains the pytest test suite for GNôle.

## Structure

- `conftest.py` - Pytest fixtures and test configuration
- `test_models.py` - Unit tests for SQLAlchemy models
- `test_auth.py` - Authentication and registration tests
- `test_routes.py` - Integration tests for Flask routes
- `test_permissions.py` - RBAC and permission tests

## Running Tests

### Run all tests
```bash
pytest
```

### Run with verbose output
```bash
pytest -v
```

### Run specific test file
```bash
pytest tests/test_models.py
```

### Run specific test class or function
```bash
pytest tests/test_models.py::TestUserModel::test_create_user
```

### Run with coverage report
```bash
pytest --cov=. --cov-report=html
```

The coverage report will be generated in `htmlcov/index.html`.

## Test Markers

Tests can be marked with custom markers:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Fixtures

Key fixtures available in `conftest.py`:

- `app` - Flask application instance
- `client` - Test client
- `sample_user` - Regular user
- `sample_admin` - Admin user
- `sample_creator` - Creator account
- `sample_event` - Test event
- `sample_participant` - Test participant
- `auth_client` - Authenticated test client
- `admin_client` - Admin authenticated client

## Writing New Tests

Example test structure:

```python
class TestMyFeature:
    """Tests for my feature."""
    
    def test_something(self, client, sample_user):
        """Test that something works."""
        response = client.get('/some_route')
        assert response.status_code == 200
```
