"""
Logging Configuration for GN Manager
Provides structured logging with rotation and environment-specific settings
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
import json


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'event_id'):
            log_data['event_id'] = record.event_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
            
        return json.dumps(log_data)


def configure_logging(app):
    """
    Configure application logging based on environment
    
    - Development: Console output with color
    - Production: JSON logs to file with rotation
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(app.root_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Determine log level from environment
    log_level_str = os.environ.get('LOGLEVEL', os.environ.get('LOG_LEVEL', 'INFO' if not app.debug else 'DEBUG'))
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler for all environments (Systemd/Docker friendly)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if app.debug:
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        )
    else:
        # JSON format for console in production (or simple if preferred)
        console_formatter = JsonFormatter()
        
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all environments (JSON format)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'app.log'),
        when='midnight',
        interval=1,
        backupCount=7,  # Keep 7 days of logs
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    
    if app.debug:
        # Use simple format in development file logs
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        )
    else:
        # Use JSON format in production
        file_formatter = JsonFormatter()
    
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Separate error log file (errors and above)
    error_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'error.log'),
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days of error logs
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Configure Flask app logger
    app.logger.setLevel(log_level)
    
    # Set SQLAlchemy logging level (reduce noise in production)
    if not app.debug:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    app.logger.debug(
        f'Logging configured: level={log_level_str}, debug={app.debug}, log_dir={log_dir}'
    )


def get_request_logger(request_id=None, user_id=None):
    """
    Get a logger with request context
    
    Usage:
        logger = get_request_logger(request_id='abc123', user_id=42)
        logger.info('User action completed')
    """
    logger = logging.getLogger('gnmanager')
    
    # Create adapter to add context to all log records
    extra = {}
    if request_id:
        extra['request_id'] = request_id
    if user_id:
        extra['user_id'] = user_id
    
    return logging.LoggerAdapter(logger, extra)
