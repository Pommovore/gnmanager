"""
Gestionnaire d'erreurs amélioré pour GN Manager.

Fournit un logging structuré des erreurs et la capture du contexte.
"""
import logging
import traceback
from flask import request, jsonify
from werkzeug.exceptions import HTTPException


def init_error_handlers(app):
    """
    Initialise les gestionnaires d'erreurs améliorés pour l'application.
    Capture le contexte détaillé pour toutes les erreurs.
    """
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Gère les erreurs 404 (Page non trouvée)."""
        app.logger.warning(
            f'404 Not Found: {request.method} {request.url}',
            extra={
                'user_id': getattr(request, 'user_id', None),
                'ip_address': request.remote_addr,
                'user_agent': request.user_agent.string
            }
        )
        
        # Retourner du JSON pour les requêtes API, du HTML sinon
        if request.path.startswith('/api/') or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found'
            }), 404
        
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Gère les erreurs 403 (Accès interdit)."""
        app.logger.warning(
            f'403 Forbidden: {request.method} {request.url}',
            extra={
                'user_id': getattr(request, 'user_id', None),
                'ip_address': request.remote_addr
            }
        )
        
        if request.path.startswith('/api/') or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource'
            }), 403
        
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        """Gère les erreurs 500 (Erreur interne du serveur)."""
        # Journaliser les informations détaillées de l'erreur
        app.logger.error(
            f'500 Internal Server Error: {request.method} {request.url}',
            extra={
                'user_id': getattr(request, 'user_id', None),
                'ip_address': request.remote_addr,
                'exception': str(error),
                'traceback': traceback.format_exc()
            },
            exc_info=True
        )
        
        if request.path.startswith('/api/') or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500
        
        from flask import render_template
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Gère toutes les exceptions non interceptées."""
        # Laisser passer les erreurs HTTP
        if isinstance(error, HTTPException):
            return error
        
        # Journaliser l'erreur avec le contexte complet
        app.logger.critical(
            f'Unhandled exception: {type(error).__name__}: {str(error)}',
            extra={
                'user_id': getattr(request, 'user_id', None),
                'ip_address': request.remote_addr,
                'url': request.url,
                'method': request.method,
                'exception_type': type(error).__name__,
                'traceback': traceback.format_exc()
            },
            exc_info=True
        )
        
        # Retourner une erreur 500
        if request.path.startswith('/api/') or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500
        
        from flask import render_template
        return render_template('errors/500.html'), 500


def log_request_info():
    """Journalise les informations sur les requêtes entrantes (pour le debug)."""
    if not request.path.startswith('/static/'):
        app = current_app._get_current_object()
        app.logger.debug(
            f'{request.method} {request.path}',
            extra={
                'user_id': getattr(request, 'user_id', None),
                'ip_address': request.remote_addr,
                'user_agent': request.user_agent.string
            }
        )
