"""
Health Check Routes for GN Manager
Provides endpoints for monitoring application health and availability
"""
from flask import Blueprint, jsonify, current_app
from models import db
from datetime import datetime
import os
import sys

health_bp = Blueprint('health', __name__)

# Stocker l'heure de démarrage de l'application
_start_time = datetime.utcnow()


@health_bp.route('/health', methods=['GET'])
def health():
    """
    Basic health check endpoint (liveness probe)
    Returns 200 if the application is running
    
    Example:
        GET /health -> {"status": "healthy", "timestamp": "2026-01-28T00:00:00Z"}
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


@health_bp.route('/health/ready', methods=['GET'])
def readiness():
    """
    Readiness check endpoint
    Returns 200 if app is ready to serve traffic (DB connection OK)
    
    Example:
        GET /health/ready -> {"status": "ready", "database": "connected", ...}
    """
    checks = {
        'status': 'ready',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'checks': {}
    }
    
    # Vérifier la connexion à la base de données
    try:
        db.session.execute(db.text('SELECT 1'))
        checks['checks']['database'] = 'connected'
    except Exception as e:
        checks['checks']['database'] = f'error: {str(e)}'
        checks['status'] = 'not_ready'
        return jsonify(checks), 503
    
    return jsonify(checks), 200


@health_bp.route('/health/metrics', methods=['GET'])
def metrics():
    """
    Basic metrics endpoint
    Returns application metrics and statistics
    
    Example:
        GET /health/metrics -> {"uptime_seconds": 3600, "python_version": "3.12", ...}
    """
    uptime = (datetime.utcnow() - _start_time).total_seconds()
    
    # Récupérer la taille du fichier de la base de données (pour SQLite)
    db_size = 0
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
    
    # Compter les fichiers de logs
    log_dir = os.path.join(current_app.root_path, 'logs')
    log_files_count = 0
    if os.path.exists(log_dir):
        log_files_count = len([f for f in os.listdir(log_dir) if f.endswith('.log')])
    
    return jsonify({
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'uptime_seconds': round(uptime, 2),
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'flask_debug': current_app.debug,
        'database': {
            'size_bytes': db_size,
            'size_mb': round(db_size / (1024 * 1024), 2)
        },
        'logs': {
            'directory': log_dir,
            'file_count': log_files_count
        }
    }), 200
