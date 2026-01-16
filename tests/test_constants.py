"""
Tests pour le module constants.py.

Couvre :
- Validité des énumérations
- Fonctions helper
- Valeurs par défaut
"""

import pytest
from constants import (
    UserRole, RegistrationStatus, PAFStatus, EventStatus,
    ParticipantType, EventVisibility, Genre, ActivityLogType,
    DefaultValues, get_enum_values, get_enum_by_value
)


class TestUserRole:
    """Tests de l'énumération UserRole."""
    
    def test_user_role_values(self):
        """Test que toutes les valeurs de rôles sont définies."""
        assert UserRole.CREATEUR.value == 'createur'
        assert UserRole.SYSADMIN.value == 'sysadmin'
        assert UserRole.USER.value == 'user'
    
    def test_user_role_enum_members(self):
        """Test que tous les membres sont présents."""
        roles = list(UserRole)
        assert len(roles) == 3
        assert UserRole.CREATEUR in roles
        assert UserRole.SYSADMIN in roles
        assert UserRole.USER in roles


class TestRegistrationStatus:
    """Tests de l'énumération RegistrationStatus."""
    
    def test_registration_status_values(self):
        """Test des valeurs de statuts d'inscription."""
        assert RegistrationStatus.TO_VALIDATE.value == 'À valider'
        assert RegistrationStatus.PENDING.value == 'En attente'
        assert RegistrationStatus.VALIDATED.value == 'Validé'
        assert RegistrationStatus.REJECTED.value == 'Rejeté'
    
    def test_all_registration_statuses_defined(self):
        """Test que tous les statuts sont définis."""
        statuses = list(RegistrationStatus)
        assert len(statuses) == 4


class TestPAFStatus:
    """Tests de l'énumération PAFStatus."""
    
    def test_paf_status_values(self):
        """Test des valeurs de statuts de PAF."""
        assert PAFStatus.NOT_PAID.value == 'non versée'
        assert PAFStatus.PARTIAL.value == 'partielle'
        assert PAFStatus.PAID.value == 'versée'
        assert PAFStatus.DISPENSED.value == 'dispensé(e)'
        assert PAFStatus.ERROR.value == 'erreur'
    
    def test_all_paf_statuses_defined(self):
        """Test que tous les statuts PAF sont définis."""
        statuses = list(PAFStatus)
        assert len(statuses) == 5


class TestEventStatus:
    """Tests de l'énumération EventStatus."""
    
    def test_event_status_lifecycle(self):
        """Test des statuts principaux du cycle de vie d'un événement."""
        assert EventStatus.PREPARATION.value == 'En préparation'
        assert EventStatus.REGISTRATION_OPEN.value == 'Inscriptions ouvertes'
        assert EventStatus.REGISTRATION_CLOSED.value == 'Inscriptions fermées'
        assert EventStatus.CASTING_IN_PROGRESS.value == 'Casting en cours'
        assert EventStatus.CASTING_DONE.value == 'Casting terminé'
        assert EventStatus.COMPLETED.value == 'Terminé'
        assert EventStatus.CANCELLED.value == 'Annulé'
    
    def test_event_status_count(self):
        """Test que tous les statuts d'événement sont définis."""
        statuses = list(EventStatus)
        assert len(statuses) >= 12  # Au moins 12 statuts définis


class TestParticipantType:
    """Tests de l'énumération ParticipantType."""
    
    def test_participant_type_values(self):
        """Test des types de participants."""
        assert ParticipantType.ORGANISATEUR.value == 'organisateur'
        assert ParticipantType.PJ.value == 'PJ'
        assert ParticipantType.PNJ.value == 'PNJ'
    
    def test_all_participant_types_defined(self):
        """Test que tous les types sont définis."""
        types = list(ParticipantType)
        assert len(types) == 3


class TestEventVisibility:
    """Tests de l'énumération EventVisibility."""
    
    def test_event_visibility_values(self):
        """Test des valeurs de visibilité."""
        assert EventVisibility.PUBLIC.value == 'public'
        assert EventVisibility.PRIVATE.value == 'private'
    
    def test_all_visibility_options_defined(self):
        """Test que toutes les options de visibilité sont définies."""
        options = list(EventVisibility)
        assert len(options) == 2


class TestGenre:
    """Tests de l'énumération Genre."""
    
    def test_genre_values(self):
        """Test des valeurs de genres."""
        assert Genre.HOMME.value == 'Homme'
        assert Genre.FEMME.value == 'Femme'
        assert Genre.OTHER.value == 'X'
    
    def test_all_genres_defined(self):
        """Test que tous les genres sont définis."""
        genres = list(Genre)
        assert len(genres) == 3


class TestActivityLogType:
    """Tests de l'énumération ActivityLogType."""
    
    def test_activity_log_types(self):
        """Test des types de logs d'activité."""
        assert ActivityLogType.USER_REGISTRATION.value == 'user_registration'
        assert ActivityLogType.EVENT_CREATION.value == 'event_creation'
        assert ActivityLogType.EVENT_PARTICIPATION.value == 'event_participation'
        assert ActivityLogType.STATUS_CHANGE.value == 'Modification statut'
        assert ActivityLogType.USER_DELETION.value == 'Suppression utilisateur'
    
    def test_all_log_types_defined(self):
        """Test que tous les types de logs sont définis."""
        types = list(ActivityLogType)
        assert len(types) == 5


class TestDefaultValues:
    """Tests de la classe DefaultValues."""
    
    def test_default_group(self):
        """Test de la valeur du groupe par défaut."""
        assert DefaultValues.DEFAULT_GROUP == 'Peu importe'
    
    def test_default_avatar_size(self):
        """Test de la taille par défaut de l'avatar."""
        assert DefaultValues.DEFAULT_AVATAR_SIZE == (80, 80)
        assert isinstance(DefaultValues.DEFAULT_AVATAR_SIZE, tuple)
        assert len(DefaultValues.DEFAULT_AVATAR_SIZE) == 2
    
    def test_password_min_length(self):
        """Test de la longueur minimale de mot de passe."""
        assert DefaultValues.PASSWORD_MIN_LENGTH == 6
        assert isinstance(DefaultValues.PASSWORD_MIN_LENGTH, int)
    
    def test_token_expiry_values(self):
        """Test des durées d'expiration des tokens."""
        assert DefaultValues.PASSWORD_RESET_TOKEN_EXPIRY_HOURS == 1
        assert DefaultValues.ACCOUNT_VALIDATION_TOKEN_EXPIRY_HOURS == 24
    
    def test_pagination_values(self):
        """Test des valeurs de pagination."""
        assert DefaultValues.USERS_PER_PAGE == 20
        assert isinstance(DefaultValues.USERS_PER_PAGE, int)
    
    def test_default_groups_config(self):
        """Test de la configuration par défaut des groupes."""
        config = DefaultValues.DEFAULT_GROUPS_CONFIG
        assert isinstance(config, dict)
        assert 'PJ' in config
        assert 'PNJ' in config
        assert 'Organisateur' in config
        assert 'Peu importe' in config['PJ']
        assert 'général' in config['Organisateur']


class TestHelperFunctions:
    """Tests des fonctions helper."""
    
    def test_get_enum_values(self):
        """Test de get_enum_values."""
        values = get_enum_values(UserRole)
        assert 'createur' in values
        assert 'sysadmin' in values
        assert 'user' in values
        assert len(values) == 3
    
    def test_get_enum_values_participant_type(self):
        """Test de get_enum_values pour ParticipantType."""
        values = get_enum_values(ParticipantType)
        assert 'organisateur' in values
        assert 'PJ' in values
        assert 'PNJ' in values
    
    def test_get_enum_by_value_found(self):
        """Test de get_enum_by_value quand la valeur existe."""
        result = get_enum_by_value(UserRole, 'createur')
        assert result == UserRole.CREATEUR
        
        result = get_enum_by_value(PAFStatus, 'versée')
        assert result == PAFStatus.PAID
    
    def test_get_enum_by_value_not_found(self):
        """Test de get_enum_by_value quand la valeur n'existe pas."""
        result = get_enum_by_value(UserRole, 'invalid_role')
        assert result is None
        
        result = get_enum_by_value(EventStatus, 'nonexistent')
        assert result is None
    
    def test_get_enum_by_value_with_all_enums(self):
        """Test de get_enum_by_value avec plusieurs énumérations."""
        # UserRole
        assert get_enum_by_value(UserRole, 'sysadmin') == UserRole.SYSADMIN
        
        # RegistrationStatus
        assert get_enum_by_value(RegistrationStatus, 'Validé') == RegistrationStatus.VALIDATED
        
        # ParticipantType
        assert get_enum_by_value(ParticipantType, 'PJ') == ParticipantType.PJ
        
        # Genre
        assert get_enum_by_value(Genre, 'Homme') == Genre.HOMME


class TestEnumConsistency:
    """Tests de cohérence entre les énumérations."""
    
    def test_no_duplicate_values_in_user_role(self):
        """Test qu'il n'y a pas de valeurs dupliquées dans UserRole."""
        values = [role.value for role in UserRole]
        assert len(values) == len(set(values))
    
    def test_no_duplicate_values_in_registration_status(self):
        """Test qu'il n'y a pas de valeurs dupliquées dans RegistrationStatus."""
        values = [status.value for status in RegistrationStatus]
        assert len(values) == len(set(values))
    
    def test_all_enums_have_string_values(self):
        """Test que toutes les énumérations ont des valeurs de type string."""
        for role in UserRole:
            assert isinstance(role.value, str)
        
        for status in EventStatus:
            assert isinstance(status.value, str)
        
        for ptype in ParticipantType:
            assert isinstance(ptype.value, str)
