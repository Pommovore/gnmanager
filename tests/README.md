# GNôle Tests

This directory contains the pytest test suite for GNôle.

## Structure

- `conftest.py` - Pytest fixtures and test configuration
- `test_models.py` - Unit tests for SQLAlchemy models
- `test_auth.py` - Authentication and email utility tests
- `test_auth_routes.py` - Authentication route tests (login, register, validation)
- `test_admin_routes.py` - Admin panel and user management tests
- `test_routes.py` - General route integration tests
- `test_event_routes.py` - Event CRUD and configuration tests
- `test_event_casting.py` - Casting system tests (assign, proposals, scores)
- `test_event_errors.py` - Event-related error handling tests
- `test_event_real.py` - Real-world scenario tests
- `test_participant_routes.py` - Participant management route tests
- `test_participant_bulk_update.py` - Bulk participant update tests
- `test_permissions.py` - RBAC and permission tests
- `test_decorators.py` - Custom decorator tests
- `test_constants.py` - Enums and constants tests
- `test_gforms.py` - Google Forms integration tests
- `test_webhook_routes.py` - Webhook endpoint tests
- `test_health_routes.py` - Health check endpoint tests
- `test_error_handlers.py` - Error handler tests
- `test_discord_service.py` - Discord notification service tests
- `test_file_validation.py` - File upload and validation tests
- `test_new_features.py` - Tests for newly added features
- `test_regenerate_secret.py` - Webhook secret regeneration tests

## Running Tests

### Run all tests
```bash
uv run pytest
```

### Run with verbose output
```bash
uv run pytest -v
```

### Run specific test file
```bash
uv run pytest tests/test_models.py
```

### Run specific test class or function
```bash
uv run pytest tests/test_models.py::TestUserModel::test_create_user
```

### Run with coverage report
```bash
uv run pytest --cov=. --cov-report=html
```

The coverage report will be generated in `htmlcov/index.html`.

## Test Markers

Tests can be marked with custom markers:

```bash
# Run only unit tests
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"
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
