from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    nom = db.Column(db.String(80))
    prenom = db.Column(db.String(80))
    age = db.Column(db.Integer)
    genre = db.Column(db.String(20))
    avatar_url = db.Column(db.String(200))
    # RBAC Fields
    role = db.Column(db.String(20), default='user') # createur, sysadmin, user
    is_banned = db.Column(db.Boolean, default=False)
    # is_admin deprecated, logic mapped to role in properties for compat if needed, or removed.
    # We'll keep is_admin as a property for backward compat in templates temporarily
    is_deleted = db.Column(db.Boolean, default=False) # Soft delete

    @property
    def is_admin(self):
        return self.role in ['createur', 'sysadmin']
    
    @is_admin.setter
    def is_admin(self, value):
        # Basic setter for backward compat or simple toggle
        if value:
            self.role = 'sysadmin'
        else:
            self.role = 'user'

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text) # Added
    date_start = db.Column(db.DateTime, nullable=False)
    date_end = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    background_image = db.Column(db.String(200))
    visibility = db.Column(db.String(20), default='public') # public, private
    organizer_structure = db.Column(db.String(100))
    external_link = db.Column(db.String(255)) # Added (Google Forms)
    statut = db.Column(db.String(50), default='En préparation') # Added 'statut' as per user correctness
    # Status options: "En préparation", "Inscriptions ouvertes", "Inscriptions fermées", 
    # "Casting en cours", "Casting terminé", "Rôles en cours de préparation", 
    # "Rôles en cours d'envois", "Rôles envoyés, préparatifs de l'evènement",
    # "Evènement en cours", "Terminé", "Annulé", "Reporté"
    groups_config = db.Column(db.Text, default='{"PJ": ["Peu importe"], "PNJ": ["Peu importe"], "Organisateur": ["Peu importe"]}') # JSON stored as string 

    # Removed computed_status property as per "Statut du jeu : Enum manuelle... pas d'automatisation"

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(20))
    group = db.Column(db.String(50)) # Added
    assigned_participant_id = db.Column(db.Integer, db.ForeignKey('participant.id', use_alter=True, name='fk_role_assigned_participant'), nullable=True)
    comment = db.Column(db.Text)
    google_doc_url = db.Column(db.String(255)) # Added
    pdf_url = db.Column(db.String(255)) # Added
    
    # Relationship to get the participant assigned to this role easily
    assigned_participant = db.relationship('Participant', foreign_keys=[assigned_participant_id], backref='assigned_role_ref')

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50)) # Organisateur, PJ, PNJ
    group = db.Column(db.String(50))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id', use_alter=True, name='fk_participant_role'), nullable=True)
    role_communicated = db.Column(db.Boolean, default=False)
    role_received = db.Column(db.Boolean, default=False) # Added
    
    # Registration Status: "À valider", "En attente", "Validé", "Rejeté"
    registration_status = db.Column(db.String(50), default='À valider') # Added
    
    payment_method = db.Column(db.String(50))
    payment_amount = db.Column(db.Float, default=0.0)
    payment_comment = db.Column(db.Text) # Added separate comment for payment if needed, or use generic comment
    comment = db.Column(db.Text)
    custom_image = db.Column(db.String(200))
    
    # Relationships
    user = db.relationship('User', backref='participations')
    event = db.relationship('Event', backref='participants')
    # Use string for Role to avoid circular import issues if any, though here they are in same file
    role = db.relationship('Role', foreign_keys=[role_id], backref='participants_with_role')

class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AccountValidationToken(db.Model): # Added for new Auth flow
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    # Temporary storage for user details until validation
    temp_data = db.Column(db.Text) # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
