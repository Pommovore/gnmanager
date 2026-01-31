"""
Modèles de données SQLAlchemy pour GN Manager.

Ce module définit tous les modèles de la base de données:
- User: Utilisateurs et authentification
- Event: Événements GN
- Role: Rôles disponibles pour un événement
- Participant: Inscription d'un utilisateur à un événement
- PasswordResetToken: Tokens de réinitialisation de mot de passe
- AccountValidationToken: Tokens de validation de compte
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import validates
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    Modèle utilisateur pour l'authentification et le profil.
    
    Attributes:
        id: Identifiant unique
        email: Adresse email (unique, utilisée pour la connexion)
        password_hash: Hash bcrypt du mot de passe
        nom: Nom de famille
        prenom: Prénom
        age: Âge de l'utilisateur
        genre: Genre (Homme/Femme/Autre)
        avatar_url: URL de l'image de profil
        role: Rôle RBAC (createur/sysadmin/user)
        is_banned: Indicateur de bannissement
        is_deleted: Soft delete (suppression logique)
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    nom = db.Column(db.String(80))
    prenom = db.Column(db.String(80))
    age = db.Column(db.Integer)
    genre = db.Column(db.String(20))
    avatar_url = db.Column(db.String(200))
    
    # Nouveaux champs de contact
    phone = db.Column(db.String(20))
    discord = db.Column(db.String(100))
    facebook = db.Column(db.String(200))
    
    # Champs RBAC (Role-Based Access Control)
    role = db.Column(db.String(20), default='user')  # createur, sysadmin, user
    is_banned = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)  # Suppression logique

    @property
    def is_admin(self):
        """Vérifie si l'utilisateur a des privilèges administrateur."""
        return self.role in ['createur', 'sysadmin']
    
    @is_admin.setter
    def is_admin(self, value):
        """Définit le rôle administrateur (compatibilité descendante)."""
        if value:
            self.role = 'sysadmin'
        else:
            self.role = 'user'
    
    def __repr__(self):
        return f'<User {self.email}>'


class Event(db.Model):
    """
    Modèle représentant un événement GN.
    
    Attributes:
        id: Identifiant unique
        name: Nom de l'événement
        description: Description détaillée
        date_start: Date de début
        date_end: Date de fin
        location: Lieu de l'événement
        background_image: URL de l'image de fond
        visibility: Visibilité (public/private)
        organizer_structure: Structure organisatrice
        org_link_url: URL du site de l'association
        org_link_title: Titre du lien de l'association
        google_form_url: URL du Google Form d'inscription
        external_link: Lien externe (legacy)
        statut: Statut manuel de l'événement
        groups_config: Configuration JSON des groupes (PJ/PNJ/Organisateur)
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date_start = db.Column(db.DateTime, nullable=False)
    date_end = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    # background_image = db.Column(db.String(200))  # Deprecated
    background_image_light = db.Column(db.String(200))
    background_image_dark = db.Column(db.String(200))
    visibility = db.Column(db.String(20), default='public')  # public, private
    organizing_association = db.Column(db.String(150), default='une entité mystérieuse et inquiétante')
    organizer_structure = db.Column(db.String(100))
    org_link_url = db.Column(db.String(255))
    org_link_title = db.Column(db.String(100))
    google_form_url = db.Column(db.String(255))
    google_form_active = db.Column(db.Boolean, default=False)
    display_organizers = db.Column(db.Boolean, default=True)
    # Secret unique pour le webhook Google Forms de cet événement
    webhook_secret = db.Column(db.String(32), unique=True, nullable=True)
    # Discord Webhook URL for notifications
    discord_webhook_url = db.Column(db.String(255), nullable=True)
    external_link = db.Column(db.String(255))
    statut = db.Column(db.String(50), default='En préparation')
    # Statuts possibles: "En préparation", "Inscriptions ouvertes", "Inscriptions fermées",
    # "Casting en cours", "Casting terminé", "Rôles en cours de préparation",
    # "Rôles en cours d'envois", "Rôles envoyés, préparatifs de l'evènement",
    # "Évènement en cours", "Terminé", "Annulé", "Reporté"
    # "Évènement en cours", "Terminé", "Annulé", "Reporté"
    groups_config = db.Column(db.Text, default='{"PJ": ["Peu importe"], "PNJ": ["Peu importe"], "Organisateur": ["Peu importe"]}')
    
    # Configuration PAF (JSON)
    # Format: [{"name": "PJ Standard", "amount": 50}, {"name": "PJ Réduit", "amount": 30}]
    paf_config = db.Column(db.Text, default='[]')
    
    # Moyens de paiement autorisés (JSON)
    # Format: ["Helloasso", "PayPal", "Espèces"]
    payment_methods = db.Column(db.Text, default='["Helloasso"]')
    
    # Nombre maximum de participants
    max_pjs = db.Column(db.Integer, default=50)
    max_pnjs = db.Column(db.Integer, default=10)
    max_organizers = db.Column(db.Integer, default=5)
    
    # Casting validation status
    is_casting_validated = db.Column(db.Boolean, default=False)

    
    # Relations
    links = db.relationship('EventLink', backref='event', cascade='all, delete-orphan')
    
    @property
    def links_sorted(self):
        """Retourne les liens triés par position."""
        return sorted(self.links, key=lambda x: x.position)
        
    def __repr__(self):
        return f'<Event {self.name}>'


class EventLink(db.Model):
    """
    Lien externe associé à un événement.
    
    Attributes:
        id: Identifiant unique
        event_id: ID de l'événement associé
        title: Titre du lien (ex: "Site officiel", "Règles", "Billeterie")
        url: URL de destination
        position: Position d'affichage pour le tri
    """
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    position = db.Column(db.Integer, default=0)
    
    # Relation définie dans Event via backref 'links'
    
    def __repr__(self):
        return f'<EventLink {self.title} - Event {self.event_id}>'


class Role(db.Model):
    """
    Modèle représentant un rôle jouable dans un événement.
    
    Attributes:
        id: Identifiant unique
        event_id: ID de l'événement associé
        name: Nom du rôle
        type: Type de rôle (Organisateur/PJ/PNJ)
        genre: Genre du rôle (Homme/Femme/Autre)
        group: Groupe auquel appartient le rôle
        assigned_participant_id: ID du participant assigné à ce rôle
        comment: Commentaires sur le rôle
        google_doc_url: URL du Google Doc décrivant le rôle
        pdf_url: URL du PDF du rôle
    """
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20))  # Organisateur, PJ, PNJ
    genre = db.Column(db.String(20))
    group = db.Column(db.String(50))
    assigned_participant_id = db.Column(db.Integer, db.ForeignKey('participant.id', use_alter=True, name='fk_role_assigned_participant'), nullable=True)
    comment = db.Column(db.Text)
    google_doc_url = db.Column(db.String(255))
    pdf_url = db.Column(db.String(255))
    
    @validates('type')
    def validate_type(self, key, value):
        """Assure que le type est normalisé (Organisateur, PJ, PNJ)."""
        if value:
            v_lower = value.lower()
            if v_lower == 'organisateur':
                return 'Organisateur'
            if v_lower == 'pj':
                return 'PJ'
            if v_lower == 'pnj':
                return 'PNJ'
        return value

    # Relation pour obtenir facilement le participant assigné
    assigned_participant = db.relationship('Participant', foreign_keys=[assigned_participant_id], backref='assigned_role_ref')
    
    def __repr__(self):
        return f'<Role {self.name} - Event {self.event_id}>'


class Participant(db.Model):
    """
    Modèle représentant l'inscription d'un utilisateur à un événement.
    
    Attributes:
        id: Identifiant unique
        event_id: ID de l'événement
        user_id: ID de l'utilisateur
        type: Type de participation (Organisateur/PJ/PNJ)
        group: Groupe du participant
        role_id: ID du rôle assigné
        role_communicated: Si le rôle a été communiqué
        role_received: Si le participant a confirmé la réception
        registration_status: Statut d'inscription (À valider/En attente/Validé/Rejeté)
        paf_status: Statut PAF - Participation Aux Frais (non versée/partielle/versée/erreur)
        payment_method: Méthode de paiement
        payment_amount: Montant payé
        global_comment: Commentaire général (ex: régime alimentaire, notes internes)
        comment: Commentaire (obsolète/interne)
        custom_image: Image personnalisée du participant
    """
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50))  # Organisateur, PJ, PNJ
    group = db.Column(db.String(50))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id', use_alter=True, name='fk_participant_role'), nullable=True)
    role_communicated = db.Column(db.Boolean, default=False)
    role_received = db.Column(db.Boolean, default=False)
    
    # Statut d'inscription: "À valider", "En attente", "Validé", "Rejeté"
    registration_status = db.Column(db.String(50), default='À valider')
    
    # Statut PAF (Participation Aux Frais)
    # Statut PAF (Participation Aux Frais)
    paf_status = db.Column(db.String(20), default='non versée')  # non versée, partielle, versée, erreur
    paf_type = db.Column(db.String(50))  # Ex: "PJ Standard", "Tarif Réduit"
    
    payment_method = db.Column(db.String(50))
    payment_amount = db.Column(db.Float, default=0.0)
    global_comment = db.Column(db.Text)
    comment = db.Column(db.Text)
    custom_image = db.Column(db.String(200))
    info_payement = db.Column(db.Text)
    
    # Coordonnées spécifiques à l'événement (copiées depuis User lors de l'inscription)
    participant_phone = db.Column(db.String(20))
    participant_discord = db.Column(db.String(100))
    participant_facebook = db.Column(db.String(200))
    
    # Flags de consentement pour partager les coordonnées avec les organisateurs
    share_phone = db.Column(db.Boolean, default=True)
    share_discord = db.Column(db.Boolean, default=True)
    share_facebook = db.Column(db.Boolean, default=True)
    
    @property
    def is_organizer(self):
        """Vérifie si le participant est un organisateur (insensible à la casse)."""
        return self.type and self.type.lower() == 'organisateur'
        
    @property
    def is_pj(self):
        """Vérifie si le participant est un PJ (insensible à la casse)."""
        return self.type and self.type.lower() == 'pj'
        
    @property
    def is_pnj(self):
        """Vérifie si le participant est un PNJ (insensible à la casse)."""
        return self.type and self.type.lower() == 'pnj'

    @validates('type')
    def validate_type(self, key, value):
        """Assure que le type est normalisé (Organisateur, PJ, PNJ)."""
        if value:
            v_lower = value.lower()
            if v_lower == 'organisateur':
                return 'Organisateur'
            if v_lower == 'pj':
                return 'PJ'
            if v_lower == 'pnj':
                return 'PNJ'
        return value

    # Database indexes for foreign keys (improves query performance)
    __table_args__ = (
        db.Index('idx_participant_event', 'event_id'),
        db.Index('idx_participant_user', 'user_id'),
        db.Index('idx_participant_status', 'registration_status'),
    )
    
    # Relations
    user = db.relationship('User', backref='participations')
    event = db.relationship('Event', backref='participants')
    role = db.relationship('Role', foreign_keys=[role_id], backref='participants_with_role')
    
    def __repr__(self):
        return f'<Participant User:{self.user_id} Event:{self.event_id}>'


class PasswordResetToken(db.Model):
    """
    Token de réinitialisation de mot de passe.
    
    Attributes:
        id: Identifiant unique
        token: Token UUID unique
        email: Email de l'utilisateur
        created_at: Date de création (expiration après 1h)
    """
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PasswordResetToken {self.email}>'


class AccountValidationToken(db.Model):
    """
    Token de validation de nouveau compte utilisateur.
    
    Attributes:
        id: Identifiant unique
        token: Token UUID unique
        email: Email de l'utilisateur
        temp_data: Données temporaires (JSON) en attente de validation
        created_at: Date de création (expiration après 24h)
    """
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    temp_data = db.Column(db.Text)  # Stockage temporaire JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AccountValidationToken {self.email}>'


class ActivityLog(db.Model):
    """
    Journal d'activité pour l'administration.
    
    Enregistre toutes les actions importantes:
    - Inscriptions d'utilisateurs
    - Créations d'événements
    - Demandes de participation aux événements
    
    Attributes:
        id: Identifiant unique
        action_type: Type d'action (user_registration/event_creation/event_participation)
        user_id: ID de l'utilisateur concerné
        event_id: ID de l'événement (si applicable)
        details: Détails JSON de l'action
        is_viewed: Si l'admin a déjà consulté ce log
        created_at: Date et heure de l'action
    """
    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    details = db.Column(db.Text)  # JSON
    is_viewed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref='activity_logs')
    event = db.relationship('Event', backref='activity_logs')
    
    def __repr__(self):
        return f'<ActivityLog {self.action_type} by User:{self.user_id}>'


class CastingProposal(db.Model):
    """
    Représente une colonne de proposition de casting pour un événement.
    
    Chaque événement peut avoir plusieurs propositions (colonnes) pour
    comparer différentes options d'attribution de rôles.
    
    Attributes:
        id: Identifiant unique
        event_id: ID de l'événement associé
        name: Nom de la proposition (affiché comme titre de colonne)
        position: Position d'affichage (ordre des colonnes)
        created_at: Date de création
    """
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    event = db.relationship('Event', backref='casting_proposals')
    assignments = db.relationship('CastingAssignment', backref='proposal', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CastingProposal {self.name} - Event {self.event_id}>'


class CastingAssignment(db.Model):
    """
    Attribution d'un participant à un rôle dans une proposition de casting.
    
    Attributes:
        id: Identifiant unique
        proposal_id: ID de la proposition de casting
        role_id: ID du rôle
        participant_id: ID du participant (nullable si non attribué)
        event_id: ID de l'événement (pour requêtes optimisées)
    """
    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('casting_proposal.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    score = db.Column(db.Integer, nullable=True, default=0)  # Score 0-10 for casting preference
    
    # Database indexes for performance
    __table_args__ = (
        db.Index('idx_casting_assignment_proposal', 'proposal_id'),
        db.Index('idx_casting_assignment_role', 'role_id'),
        db.Index('idx_casting_assignment_event', 'event_id'),
        db.UniqueConstraint('proposal_id', 'role_id', name='uq_proposal_role'),
    )
    
    # Relations
    role = db.relationship('Role', backref='casting_assignments')
    participant = db.relationship('Participant', backref='casting_assignments')
    event = db.relationship('Event', backref='casting_assignments')
    
    def __repr__(self):
        return f'<CastingAssignment Proposal:{self.proposal_id} Role:{self.role_id} Participant:{self.participant_id}>'


class FormResponse(db.Model):
    """
    Stockage brut des réponses reçues via le Webhook Google Forms.
    
    Attributes:
        id: Identifiant unique
        form_id: ID du formulaire Google
        response_id: ID persistent de la réponse (fourni par Google Forms)
        respondent_email: Email du répondant (si collecté)
        answers: Charge utile JSON complète des réponses
        created_at: Date de création
        updated_at: Date de dernière mise à jour
    """
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    form_id = db.Column(db.String(100))
    response_id = db.Column(db.String(100), unique=True, nullable=False)
    respondent_email = db.Column(db.String(120))
    answers = db.Column(db.Text)  # JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FormResponse {self.response_id} from {self.respondent_email}>'
