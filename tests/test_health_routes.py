"""
Tests pour les routes de santé (health_routes.py).

Couvre :
- Health check endpoint
- Readiness check endpoint  
- Metrics endpoint
- Vérification de la connectivité DB
"""

import pytest
from datetime import datetime


class TestHealthEndpoint:
    """Tests du endpoint /health."""
    
    def test_health_check_returns_200(self, client):
        """Test que health check retourne 200."""
        response = client.get('/health')
        assert response.status_code == 200
    
    def test_health_check_json_format(self, client):
        """Test que health check retourne le bon format JSON."""
        response = client.get('/health')
        data = response.get_json()
        
        assert 'status' in data
        assert 'timestamp' in data
        assert data['status'] == 'healthy'
    
    def test_health_check_timestamp_format(self, client):
        """Test que le timestamp est au bon format ISO."""
        response = client.get('/health')
        data = response.get_json()
        
        timestamp = data['timestamp']
        assert timestamp.endswith('Z')
        # Should be parseable as ISO format
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))


class TestReadyEndpoint:
    """Tests du endpoint /health/ready."""
    
    def test_ready_check_returns_200(self, client, db):
        """Test que ready check retourne 200 quand DB est connectée."""
        response = client.get('/health/ready')
        assert response.status_code == 200
    
    def test_ready_check_json_format(self, client, db):
        """Test que ready check retourne le bon format JSON."""
        response = client.get('/health/ready')
        data = response.get_json()
        
        assert 'status' in data
        assert 'checks' in data
        assert 'database' in data['checks']
        assert 'timestamp' in data
    
    def test_ready_check_database_connected(self, client, db):
        """Test que ready check indique DB connectée."""
        response = client.get('/health/ready')
        data = response.get_json()
        
        assert data['status'] == 'ready'
        assert data['checks']['database'] == 'connected'
    
    def test_ready_check_with_db_error(self, client, db, monkeypatch):
        """Test ready check avec erreur DB."""
        # Mock db.session.execute to raise an exception
        def mock_execute(*args, **kwargs):
            raise Exception("Database connection failed")
        
        monkeypatch.setattr(db.session, 'execute', mock_execute)
        
        response = client.get('/health/ready')
        assert response.status_code == 503
        
        data = response.get_json()
        assert data['status'] == 'not_ready'
        assert 'error:' in data['checks']['database']  # Contains error message


class TestMetricsEndpoint:
    """Tests du endpoint /health/metrics."""
    
    def test_metrics_returns_200(self, client):
        """Test que metrics retourne 200."""
        response = client.get('/health/metrics')
        assert response.status_code == 200
    
    def test_metrics_json_structure(self, client):
        """Test la structure JSON des metrics."""
        response = client.get('/health/metrics')
        data = response.get_json()
        
        assert 'timestamp' in data
        assert 'uptime_seconds' in data
        assert 'python_version' in data
        assert 'flask_debug' in data
        assert 'database' in data
        assert 'logs' in data
    
    def test_metrics_uptime(self, client):
        """Test que uptime est un nombre positif."""
        response = client.get('/health/metrics')
        data = response.get_json()
        
        assert isinstance(data['uptime_seconds'], (int, float))
        assert data['uptime_seconds'] >= 0
    
    def test_metrics_python_version(self, client):
        """Test que python_version est au bon format."""
        response = client.get('/health/metrics')
        data = response.get_json()
        
        version = data['python_version']
        assert isinstance(version, str)
        # Format: "3.12.12" or similar
        parts = version.split('.')
        assert len(parts) >= 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()
    
    def test_metrics_database_info(self, client):
        """Test les informations de base de données."""
        response = client.get('/health/metrics')
        data = response.get_json()
        
        db_info = data['database']
        assert 'size_bytes' in db_info
        assert 'size_mb' in db_info
        assert isinstance(db_info['size_bytes'], (int, float))
        assert isinstance(db_info['size_mb'], (int, float))
        assert db_info['size_bytes'] >= 0
        assert db_info['size_mb'] >= 0
    
    def test_metrics_logs_info(self, client):
        """Test les informations de logs."""
        response = client.get('/health/metrics')
        data = response.get_json()
        
        logs_info = data['logs']
        assert 'directory' in logs_info
        assert 'file_count' in logs_info
        assert isinstance(logs_info['file_count'], int)
        assert logs_info['file_count'] >= 0
    
    def test_metrics_flask_debug_flag(self, client, app):
        """Test que le flag flask_debug reflète la config."""
        response = client.get('/health/metrics')
        data = response.get_json()
        
        # In testing, debug should match app.debug
        assert data['flask_debug'] == app.debug


class TestHealthEndpointsAccessibility:
    """Tests d'accessibilité des endpoints de santé."""
    
    def test_health_endpoints_dont_require_auth(self, client):
        """Test que les endpoints de santé ne nécessitent pas d'authentification."""
        # /health
        response = client.get('/health')
        assert response.status_code == 200
        
        # /health/ready
        response = client.get('/health/ready')
        assert response.status_code in [200, 503]  # 503 si DB error
        
        # /health/metrics
        response = client.get('/health/metrics')
        assert response.status_code == 200
    
    def test_health_endpoints_content_type(self, client):
        """Test que les endpoints retournent du JSON."""
        endpoints = ['/health', '/health/ready', '/health/metrics']
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert 'application/json' in response.content_type


class TestHealthTimestamps:
    """Tests des timestamps dans les réponses health."""
    
    def test_all_endpoints_have_timestamps(self, client, db):
        """Test que tous les endpoints health ont un timestamp."""
        endpoints = ['/health', '/health/ready', '/health/metrics']
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            if response.status_code == 200:
                data = response.get_json()
                assert 'timestamp' in data
                assert isinstance(data['timestamp'], str)
    
    def test_timestamps_are_recent(self, client):
        """Test que les timestamps sont récents (< 5 secondes)."""
        response = client.get('/health')
        data = response.get_json()
        
        timestamp_str = data['timestamp'].replace('Z', '+00:00')
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now(timestamp.tzinfo)
        
        # Should be within last 5 seconds
        time_diff = (now - timestamp).total_seconds()
        assert abs(time_diff) < 5
