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
    avatar_url = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    background_image = db.Column(db.String(200))
    visibility = db.Column(db.String(20), default='public') # public, private
    organizer_structure = db.Column(db.String(100))
    status = db.Column(db.String(50), default='non_ouvertes') # non_ouvertes, pre_inscriptions, attribution_roles, clos

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(20))
    assigned_participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=True)
    comment = db.Column(db.Text)

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50)) # organisateur, PJ, PNJ
    group = db.Column(db.String(50))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=True)
    role_communicated = db.Column(db.Boolean, default=False)
    payment_method = db.Column(db.String(50))
    payment_amount = db.Column(db.Float, default=0.0)
    comment = db.Column(db.Text)
    custom_image = db.Column(db.String(200))

class LoginToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    is_validated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
