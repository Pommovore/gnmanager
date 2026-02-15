"""
Exceptions personnalisées pour l'application GN Manager.

Ce module définit des exceptions spécifiques à l'application pour une
meilleure gestion des erreurs et un débogage plus clair. L'utilisation
d'exceptions spécifiques permet une gestion plus granulaire des erreurs
et des messages plus explicites.
"""


class AppError(Exception):
    """Exception de base pour toutes les erreurs de l'application."""
    pass


class DatabaseError(AppError):
    """
    Exception levée pour les erreurs d'opérations en base de données.
    
    Exemples :
    - Échec des opérations INSERT/UPDATE/DELETE
    - Violations de contraintes
    - Problèmes de connexion
    """
    pass


class PermissionError(AppError):
    """
    Exception levée pour les erreurs d'autorisation/permissions.
    
    Exemples :
    - Utilisateur tentant d'accéder à une ressource qui ne lui appartient pas
    - Non-admin essayant d'accéder à des fonctionnalités réservées aux administrateurs
    """
    pass


class ValidationError(AppError):
    """
    Exception levée pour les erreurs de validation des données.
    
    Exemples :
    - Format d'email invalide
    - Champs obligatoires manquants
    - Plages de dates invalides
    """
    pass


class ExternalServiceError(AppError):
    """
    Exception levée pour les erreurs de services externes.
    
    Exemples :
    - Échecs de l'API Google
    - Erreurs du service email
    - Échecs OAuth
    """
    pass
