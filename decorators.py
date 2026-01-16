"""
Décorateurs personnalisés pour GN Manager.

Ce module fournit des décorateurs réutilisables pour:
- Vérification des permissions (admin, organisateur)
- Gestion des accès aux événements
"""

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from models import Participant, Event
from constants import ParticipantType


def admin_required(f):
    """
    Décorateur qui vérifie que l'utilisateur connecté est administrateur.
    
    Utilisation:
        @admin_required
        def my_admin_route():
            ...
    
    Redirige vers le dashboard avec un message d'erreur si l'utilisateur
    n'est pas admin (rôle 'createur' ou 'sysadmin').
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Vous devez être connecté pour accéder à cette page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin:
            flash('Accès réservé aux administrateurs.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def organizer_required(f):
    """
    Décorateur qui vérifie que l'utilisateur est organisateur de l'événement.
    
    Utilisation:
        @organizer_required
        def my_event_route(event_id):
            ...
    
    IMPORTANT: La route doit avoir un paramètre 'event_id' en premier argument.
    
    Redirige vers la page de détail de l'événement avec un message d'erreur
    si l'utilisateur n'est pas organisateur.
    """
    @wraps(f)
    def decorated_function(event_id, *args, **kwargs):
        if not current_user.is_authenticated:
            flash('Vous devez être connecté pour accéder à cette page.', 'warning')
            return redirect(url_for('auth.login'))
        
        event = Event.query.get_or_404(event_id)
        participant = Participant.query.filter_by(
            event_id=event.id, 
            user_id=current_user.id
        ).first()
        
        if not participant or participant.type.lower() != ParticipantType.ORGANISATEUR.value.lower():
            flash('Accès réservé aux organisateurs de cet événement.', 'danger')
            return redirect(url_for('event.detail', event_id=event.id))
        
        return f(event_id, *args, **kwargs)
    return decorated_function


def participant_required(f):
    """
    Décorateur qui vérifie que l'utilisateur participe à l'événement.
    
    Utilisation:
        @participant_required
        def my_event_route(event_id):
            ...
    
    IMPORTANT: La route doit avoir un paramètre 'event_id' en premier argument.
    
    Redirige vers la page de détail de l'événement avec un message d'erreur
    si l'utilisateur ne participe pas à l'événement.
    """
    @wraps(f)
    def decorated_function(event_id, *args, **kwargs):
        if not current_user.is_authenticated:
            flash('Vous devez être connecté pour accéder à cette page.', 'warning')
            return redirect(url_for('auth.login'))
        
        event = Event.query.get_or_404(event_id)
        participant = Participant.query.filter_by(
            event_id=event.id, 
            user_id=current_user.id
        ).first()
        
        if not participant:
            flash('Vous devez participer à cet événement pour accéder à cette page.', 'danger')
            return redirect(url_for('event.detail', event_id=event.id))
        
        return f(event_id, *args, **kwargs)
    return decorated_function


def creator_required(f):
    """
    Décorateur qui vérifie que l'utilisateur est un créateur (super admin).
    
    Utilisation:
        @creator_required
        def my_super_admin_route():
            ...
    
    Redirige vers le dashboard avec un message d'erreur si l'utilisateur
    n'est pas créateur.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Vous devez être connecté pour accéder à cette page.', 'warning')
            return redirect(url_for('auth.login'))
        
        from constants import UserRole
        if current_user.role != UserRole.CREATEUR.value:
            flash('Accès réservé aux créateurs.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function
