"""
Constantes et énumérations pour GN Manager.

Ce module centralise toutes les valeurs constantes utilisées dans l'application
pour éliminer les "magic strings" et améliorer la maintenabilité.
"""

from enum import Enum


class UserRole(Enum):
    """
    Rôles utilisateur pour le système RBAC (Role-Based Access Control).
    
    - CREATEUR: Administrateur suprême, accès total
    - SYSADMIN: Administrateur système, ne peut pas modifier les créateurs
    - USER: Utilisateur standard
    """
    CREATEUR = 'createur'
    SYSADMIN = 'sysadmin'
    USER = 'user'


class RegistrationStatus(Enum):
    """
    Statuts d'inscription d'un participant à un événement.
    
    - TO_VALIDATE: Inscription en attente de validation par l'organisateur
    - PENDING: En attente (statut intermédiaire)
    - VALIDATED: Inscription validée par l'organisateur
    - REJECTED: Inscription rejetée
    """
    TO_VALIDATE = 'À valider'
    PENDING = 'En attente'
    VALIDATED = 'Validé'
    REJECTED = 'Rejeté'


class PAFStatus(Enum):
    """
    Statuts de PAF (Participation Aux Frais).
    
    - NOT_PAID: Aucun paiement reçu
    - PARTIAL: Paiement partiel
    - PAID: Paiement complet reçu
    - DISPENSED: Dispensé de paiement
    - ERROR: Erreur de paiement
    """
    NOT_PAID = 'non versée'
    PARTIAL = 'partielle'
    PAID = 'versée'
    DISPENSED = 'dispensé(e)'
    ERROR = 'erreur'


class EventStatus(Enum):
    """
    Statuts possibles pour un événement GN.
    
    Cycle de vie typique:
    1. En préparation
    2. Inscriptions ouvertes
    3. Inscriptions fermées
    4. Casting en cours
    5. Casting terminé
    6. Rôles en cours de préparation
    7. Rôles en cours d'envois
    8. Rôles envoyés, préparatifs de l'événement
    9. Événement en cours
    10. Terminé / Annulé / Reporté
    """
    PREPARATION = 'En préparation'
    REGISTRATION_OPEN = 'Inscriptions ouvertes'
    REGISTRATION_CLOSED = 'Inscriptions fermées'
    CASTING_IN_PROGRESS = 'Casting en cours'
    CASTING_DONE = 'Casting terminé'
    ROLES_PREPARATION = 'Rôles en cours de préparation'
    ROLES_SENDING = "Rôles en cours d'envois"
    ROLES_SENT = "Rôles envoyés, préparatifs de l'evènement"
    EVENT_IN_PROGRESS = 'Évènement en cours'
    COMPLETED = 'Terminé'
    CANCELLED = 'Annulé'
    POSTPONED = 'Reporté'


class ParticipantType(Enum):
    """
    Types de participation à un événement.
    
    - ORGANISATEUR: Organisateur de l'événement
    - PJ: Personnage Joueur
    - PNJ: Personnage Non Joueur
    """
    ORGANISATEUR = 'organisateur'
    PJ = 'PJ'
    PNJ = 'PNJ'


class EventVisibility(Enum):
    """
    Visibilité d'un événement.
    
    - PUBLIC: Visible par tous
    - PRIVATE: Visible uniquement par les participants et organisateurs
    """
    PUBLIC = 'public'
    PRIVATE = 'private'


class Genre(Enum):
    """
    Genres pour les utilisateurs et les rôles.
    
    - HOMME: Masculin
    - FEMME: Féminin
    - OTHER: Autre / Indéterminé
    """
    HOMME = 'Homme'
    FEMME = 'Femme'
    OTHER = 'X'


class ActivityLogType(Enum):
    """
    Types d'actions enregistrées dans le journal d'activité.
    
    - USER_REGISTRATION: Nouvelle inscription d'utilisateur
    - EVENT_CREATION: Création d'un événement
    - EVENT_PARTICIPATION: Demande de participation à un événement
    - STATUS_CHANGE: Modification de statut
    - USER_DELETION: Suppression d'utilisateur
    """
    USER_REGISTRATION = 'user_registration'
    EVENT_CREATION = 'event_creation'
    EVENT_PARTICIPATION = 'event_participation'
    STATUS_CHANGE = 'Modification statut'

    USER_DELETION = 'Suppression utilisateur'
    EVENT_UPDATE = 'Mise à jour événement'
    PARTICIPANT_UPDATE = 'Mise à jour participant'
    GROUPS_UPDATE = 'Mise à jour groupes'
    USER_UPDATE = 'Mise à jour utilisateur'
    EVENT_DELETION = 'Suppression événement'


# Constantes diverses
class DefaultValues:
    """Valeurs par défaut utilisées dans l'application."""
    
    DEFAULT_GROUP = 'Peu importe'
    DEFAULT_AVATAR_SIZE = (80, 80)
    PASSWORD_MIN_LENGTH = 6
    
    # Expiration des tokens
    PASSWORD_RESET_TOKEN_EXPIRY_HOURS = 1
    ACCOUNT_VALIDATION_TOKEN_EXPIRY_HOURS = 24
    
    # Pagination
    USERS_PER_PAGE = 20
    
    # Groupes par défaut pour les événements
    DEFAULT_GROUPS_CONFIG = {
        "PJ": ["Peu importe"],
        "PNJ": ["Peu importe"],
        "Organisateur": ["général", "coordinateur", "scénariste", "logisticien", "crafteur", "en charge des PNJ"]
    }


# Helper functions pour convertir entre Enum et string
def get_enum_values(enum_class):
    """Retourne la liste des valeurs d'un Enum."""
    return [e.value for e in enum_class]


def get_enum_by_value(enum_class, value):
    """Trouve un membre d'Enum par sa valeur."""
    for member in enum_class:
        if member.value == value:
            return member
    return None
