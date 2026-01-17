"""
Routes d'administration pour GN Manager.

Ce module gère:
- Dashboard utilisateur
- Profil utilisateur
- Gestion des utilisateurs (CRUD) 
- Journal d'activité (logs)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Event, Participant, ActivityLog
from auth import generate_password, send_email
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import datetime
from decorators import admin_required
from constants import UserRole, ActivityLogType, DefaultValues, RegistrationStatus
from sqlalchemy.orm import joinedload
import json
import os

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard principal avec liste des événements et admin panel.
    
    Affiche:
    - Liste des événements (avec filtres)
    - Profil utilisateur
    - Panel admin (si admin)
    """
    users_pagination = None
    if current_user.is_admin:
        page = request.args.get('page', 1, type=int)
        users_pagination = User.query.paginate(page=page, per_page=DefaultValues.USERS_PER_PAGE, error_out=False)
        
    # Logique de filtrage
    filter_type = request.args.get('filter', 'future')
    
    # Identifier les événements de l'utilisateur
    my_participations = Participant.query.filter_by(user_id=current_user.id).all()
    my_event_ids = [p.event_id for p in my_participations]
    my_roles = {p.event_id: p for p in my_participations}
    
    events = []
    now = datetime.now()
    
    if filter_type == 'mine':
        # Événements auxquels je participe
        if my_event_ids:
            events = Event.query.filter(Event.id.in_(my_event_ids)).order_by(Event.date_start).all()
    elif filter_type == 'future':
        events = Event.query.filter(Event.date_start >= now).order_by(Event.date_start).all()
    elif filter_type == 'past':
        events = Event.query.filter(Event.date_end < now).order_by(Event.date_start.desc()).all()
    else:
        # 'all'
        events = Event.query.order_by(Event.date_start).all()
        
    # Admin Sub-Navigation
    admin_view = request.args.get('admin_view')
    
    return render_template('dashboard.html', 
                         user=current_user, 
                         users_pagination=users_pagination, 
                         events=events, 
                         my_event_ids=my_event_ids, 
                         my_roles=my_roles, 
                         current_filter=filter_type, 
                         admin_view=admin_view)


@admin_bp.route('/profile', methods=['POST'])
@login_required
def update_profile():
    """
    Mise à jour du profil utilisateur.
    
    Permet de modifier:
    - Informations personnelles (nom, prénom, âge, genre)
    - Avatar (image redimensionnée à 80x80)
    - Mot de passe
    """
    current_user.nom = request.form.get('nom')
    current_user.prenom = request.form.get('prenom')
    current_user.age = request.form.get('age')
    current_user.genre = request.form.get('genre')
    
    # Traitement de l'avatar
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename != '':
            # Créer le répertoire de stockage
            static_folder = os.path.join(os.getcwd(), 'static', 'uploads')
            os.makedirs(static_folder, exist_ok=True)
            
            # Redimensionner l'image
            img = Image.open(file)
            img.thumbnail(DefaultValues.DEFAULT_AVATAR_SIZE)
            
            # Sauvegarder avec l'ID utilisateur comme nom
            save_path = os.path.join(static_folder, f"avatar_{current_user.id}.png")
            img.save(save_path)
            current_user.avatar_url = f"/static/uploads/avatar_{current_user.id}.png"

    # Mise à jour du mot de passe
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password:
        if new_password == confirm_password:
            current_user.password_hash = generate_password_hash(new_password)
            flash('Mot de passe mis à jour.', 'success')
        else:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('admin.dashboard'))

    db.session.commit()
    flash('Profil mis à jour.', 'success')
    return redirect(url_for('admin.dashboard'))




@admin_bp.route('/admin/user/<int:user_id>/events')
@login_required
@admin_required
def user_events(user_id):
    """
    Affiche tous les événements auxquels un utilisateur participe.
    
    Args:
        user_id: ID de l'utilisateur
        
    Returns:
        Template avec liste des événements de l'utilisateur
    """
    user = User.query.get_or_404(user_id)
    
    # Récupérer toutes les participations de l'utilisateur avec les événements liés
    participations = Participant.query.filter_by(user_id=user_id)\
        .options(joinedload(Participant.event))\
        .options(joinedload(Participant.role))\
        .order_by(Participant.event_id.desc())\
        .all()
    
    # Grouper par événement (au cas où plusieurs rôles)
    events_data = []
    seen_events = set()
    
    for p in participations:
        if p.event_id not in seen_events:
            seen_events.add(p.event_id)
            events_data.append({
                'event': p.event,
                'participation': p,
                'role_name': p.role.name if p.role else None
            })
    
    breadcrumbs = [
        ('Dashboard', url_for('admin.dashboard')),
        ('Utilisateurs', url_for('admin.dashboard', admin_view='users') + '#admin'),
        (user.email, '#')
    ]
    
    return render_template(
        'user_events.html',
        user=user,
        events_data=events_data,
        breadcrumbs=breadcrumbs
    )


@admin_bp.route('/admin/user/add', methods=['POST'])
@login_required
@admin_required
def admin_add_user():
    """Ajouter un utilisateur (admin uniquement)."""
    email = request.form.get('email')
    if User.query.filter_by(email=email).first():
        flash('Cet email existe déjà.', 'warning')
        return redirect(url_for('admin.dashboard', admin_view='add', _anchor='admin'))
        
    password = generate_password()
    hashed_password = generate_password_hash(password)
    
    new_user = User(email=email, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    send_email(email, "Bienvenue", f"Votre compte a été créé. Mot de passe : {password}")
    flash(f'Utilisateur {email} ajouté.', 'success')
    return redirect(url_for('admin.dashboard', admin_view='users', open_edit=new_user.id, _anchor='admin'))


@admin_bp.route('/admin/user/<int:user_id>/update_full', methods=['POST'])
@login_required
@admin_required
def admin_update_full_user(user_id):
    """Mise à jour complète d'un utilisateur (admin)."""
    user = User.query.get_or_404(user_id)
    
    # Sécurité: Non-Créateurs ne peuvent pas éditer les Créateurs
    if user.role == UserRole.CREATEUR.value and current_user.role != UserRole.CREATEUR.value:
        flash('Vous ne pouvez pas modifier un compte administrateur suprême (Créateur).', 'danger')
        return redirect(url_for('admin.dashboard', admin_view='users', _anchor='admin'))
    
    # Mise à jour des champs standard
    user.email = request.form.get('email')
    user.nom = request.form.get('nom')
    user.prenom = request.form.get('prenom')
    user.age = request.form.get('age')
    user.genre = request.form.get('genre')
    
    # Mise à jour du mot de passe si fourni
    new_password = request.form.get('password')
    if new_password:
        user.password_hash = generate_password_hash(new_password)
    
    # Mise à jour du statut/rôle
    status_code = request.form.get('status')
    
    if status_code == UserRole.CREATEUR.value:
        if current_user.role == UserRole.CREATEUR.value:
            user.role = UserRole.CREATEUR.value
            user.is_banned = False
        else:
            flash("Vous ne pouvez pas nommer un Créateur.", "danger")
    elif status_code == UserRole.SYSADMIN.value:
        user.role = UserRole.SYSADMIN.value
        user.is_banned = False
        
    db.session.commit()
    
    # Log user update
    log = ActivityLog(
        user_id=current_user.id,
        action_type=ActivityLogType.USER_UPDATE.value,
        details=json.dumps({
            'target_user_id': user.id,
            'target_email': user.email,
            'updated_fields': 'Admin Full Update',
            'new_role': user.role
        })
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f"Utilisateur {user.email} mis à jour.", "success")
    return redirect(url_for('admin.dashboard', admin_view='users', _anchor='admin'))


@admin_bp.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    """Suppression d'un utilisateur (admin)."""
    user = User.query.get_or_404(user_id)
    
    # Sécurité: Ne peut pas se supprimer soi-même
    if user.id == current_user.id:
        flash("Vous ne pouvez pas supprimer votre propre compte ici.", "danger")
        return redirect(url_for('admin.dashboard', admin_view='users', _anchor='admin'))
        
    # Sécurité: Non-Creator ne peut pas supprimer Creator
    if user.role == UserRole.CREATEUR.value and current_user.role != UserRole.CREATEUR.value:
        flash("Vous ne pouvez pas supprimer un compte Créateur.", "danger")
        return redirect(url_for('admin.dashboard', admin_view='users', _anchor='admin'))

    try:
        # Suppression en cascade des entités liées
        participants = Participant.query.filter_by(user_id=user.id).all()
        participant_ids = [p.id for p in participants]
        
        if participant_ids:
            # Désassigner les rôles liés aux participants
            from models import Role
            roles_to_unassign = Role.query.filter(Role.assigned_participant_id.in_(participant_ids)).all()
            for role in roles_to_unassign:
                role.assigned_participant_id = None
        
        # Supprimer les tokens
        from models import AccountValidationToken, PasswordResetToken
        AccountValidationToken.query.filter_by(email=user.email).delete()
        PasswordResetToken.query.filter_by(email=user.email).delete()
        
        # Supprimer les participations
        Participant.query.filter_by(user_id=user.id).delete()
        
        # Logger l'action
        log = ActivityLog(
            user_id=current_user.id,
            action_type=ActivityLogType.USER_DELETION.value,
            details=json.dumps({
                'target_email': user.email,
                'name': f"{user.nom or ''} {user.prenom or ''}".strip()
            })
        )
        db.session.add(log)
        
        db.session.delete(user)
        db.session.commit()
        
        flash(f"Utilisateur {user.email} supprimé définitivement.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
        
    return redirect(url_for('admin.dashboard', admin_view='users', _anchor='admin'))


@admin_bp.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    """
    Affiche le journal d'activité pour les administrateurs.
    
    Montre toutes les inscriptions, créations d'événements et
    demandes de participation. Les logs non consultés sont
    surlignés en jaune.
    """
    # Récupérer tous les logs, les plus récents en premier
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).all()
    
    # Enrichir avec les détails JSON
    for log in logs:
        try:
            log.details_dict = json.loads(log.details or '{}')
        except json.JSONDecodeError:
            log.details_dict = {}
    
    return render_template('admin_logs.html', logs=logs)


@admin_bp.route('/admin/logs/mark-viewed', methods=['POST'])
@login_required
@admin_required
def mark_logs_viewed():
    """
    Marque tous les logs comme consultés.
    
    Supprime le surlignage jaune des logs.
    """
    ActivityLog.query.filter_by(is_viewed=False).update({'is_viewed': True})
    db.session.commit()
    
    return jsonify({'success': True})
