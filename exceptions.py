"""
Custom exceptions for GN Manager application.

This module defines application-specific exceptions for better error handling
and debugging. Using specific exceptions allows for more granular error handling
and clearer error messages.
"""


class AppError(Exception):
    """Base exception for all application errors."""
    pass


class DatabaseError(AppError):
    """
    Exception raised for database operation errors.
    
    Examples:
    - Failed INSERT/UPDATE/DELETE operations
    - Constraint violations
    - Connection issues
    """
    pass


class PermissionError(AppError):
    """
    Exception raised for authorization/permission errors.
    
    Examples:
    - User attempting to access resource they don't own
    - Non-admin trying to access admin-only features
    """
    pass


class ValidationError(AppError):
    """
    Exception raised for input validation errors.
    
    Examples:
    - Invalid email format
    - Missing required fields
    - Invalid date ranges
    """
    pass


class ExternalServiceError(AppError):
    """
    Exception raised for external service errors.
    
    Examples:
    - Google API failures
    - Email service errors
    - OAuth failures
    """
    pass
