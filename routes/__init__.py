"""
Package de routes pour GN Manager.

Organisation modulaire des routes par fonctionnalité.
"""

from .auth_routes import auth_bp
from .admin_routes import admin_bp
from .event_routes import event_bp
from .participant_routes import participant_bp

__all__ = ['auth_bp', 'admin_bp', 'event_bp', 'participant_bp']
