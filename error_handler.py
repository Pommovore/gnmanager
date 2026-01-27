"""
Enhanced Error Handler for GN Manager
Provides structured error logging and context capture
"""
import logging
import traceback
from flask import request, jsonify
from werkzeug.exceptions import HTTPException


def init_error_handlers(app):
    """
    Initialize enhanced error handlers for the application
    Captures detailed context for all errors
    """
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors"""
        app.logger.warning(
            f'404 Not Found: {request.method} {request.url}',
            extra={
                'user_id': getattr(request, 'user_id', None),
                'ip_address': request.remote_addr,
                'user_agent': request.user_agent.string
            }
        )
        
        # Return JSON for API requests, HTML otherwise
        if request.path.startswith('/api/') or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found'
            }), 404
        
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors"""
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
        """Handle 500 Internal Server errors"""
        # Log detailed error information
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
        """Handle all unhandled exceptions"""
        # Pass through HTTP errors
        if isinstance(error, HTTPException):
            return error
        
        # Log the error with full context
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
        
        # Return 500 error
        if request.path.startswith('/api/') or request.accept_mimetypes.accept_json:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500
        
        from flask import render_template
        return render_template('errors/500.html'), 500


def log_request_info():
    """Log information about incoming requests (for debugging)"""
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
