"""
Routes d'administration pour GN Manager.

Ce module gère:
- Dashboard utilisateur
- Profil utilisateur
- Gestion des utilisateurs (CRUD) 
- Journal d'activité (logs)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user, logout_user
from models import db, User, Event, Participant, ActivityLog
from auth import generate_password, send_email
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import datetime
from decorators import admin_required
from constants import UserRole, ActivityLogType, DefaultValues, RegistrationStatus
from exceptions import DatabaseError
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
    
    # Identifier les événements de l'utilisateur avec eager loading
    my_participations = Participant.query\
        .filter_by(user_id=current_user.id)\
        .options(joinedload(Participant.event))\
        .all()
    my_event_ids = [p.event_id for p in my_participations]
    my_roles = {p.event_id: p for p in my_participations}
    
    events = []
    now = datetime.now()
    
    # Filtrage de visibilité (sauf pour les admins qui voient tout/le filtre 'mine' qui implique déjà l'accès)
    # Pour 'future', 'past', et 'all', on doit exclure les événements privés où l'utilisateur n'est pas participant
    base_query = Event.query
    if not current_user.is_admin and filter_type != 'mine':
        # On inclut les événements publics OU les événements privés où l'utilisateur est participant
        from sqlalchemy import or_
        base_query = base_query.filter(
            or_(
                Event.visibility != 'private',
                Event.id.in_(my_event_ids)
            )
        )

    if filter_type == 'mine':
        # Événements auxquels je participe
        if my_event_ids:
            events = Event.query.filter(Event.id.in_(my_event_ids)).order_by(Event.date_start).all()
    elif filter_type == 'future':
        events = base_query.filter(Event.date_start >= now).order_by(Event.date_start).all()
    elif filter_type == 'past':
        events = base_query.filter(Event.date_end < now).order_by(Event.date_start.desc()).all()
    else:
        # 'all'
        events = base_query.order_by(Event.date_start).all()
        
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


@admin_bp.route('/admin', methods=['GET'])
@login_required
@admin_required
def admin_page():
    """
    Affiche la page d'administration système.
    
    Returns:
        Template admin avec gestion des utilisateurs
    """
    page = request.args.get('page', 1, type=int)
    admin_view = request.args.get('admin_view', 'users')
    search_query = request.args.get('q', '')
    
    query = User.query
    
    if search_query:
        from sqlalchemy import or_
        term = f"%{search_query}%"
        query = query.filter(
            or_(
                User.email.ilike(term),
                User.nom.ilike(term),
                User.prenom.ilike(term)
            )
        )
        
    users_pagination = query.paginate(page=page, per_page=DefaultValues.USERS_PER_PAGE, error_out=False)
    
    breadcrumbs = [
        ('Dashboard', url_for('admin.dashboard')),
        ('Administration', '#')
    ]
    
    return render_template('admin.html', 
                         user=current_user,
                         users_pagination=users_pagination,
                         admin_view=admin_view,
                         breadcrumbs=breadcrumbs)


@admin_bp.route('/profile', methods=['GET'])
@login_required
def profile_page():
    """
    Affiche la page de profil utilisateur.
    
    Returns:
        Template de profil avec les informations de l'utilisateur courant
    """
    breadcrumbs = [
        ('Dashboard', url_for('admin.dashboard')),
        ('Mon Profil', '#')
    ]
    return render_template('profile.html', user=current_user, breadcrumbs=breadcrumbs)


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
    
    # Coordonnées de contact
    current_user.phone = request.form.get('phone')
    current_user.discord = request.form.get('discord')
    current_user.facebook = request.form.get('facebook')
    
    # Checkbox fields
    # Note: Checkboxes only send 'on' if checked, otherwise nothing.
    current_user.is_profile_photo_public = request.form.get('is_profile_photo_public') == 'on'
    
    # Note: is_admin is not user-editable here, only via specific admin panel if any.
    # The previous code snippet looked like it was trying to set is_admin, which might be a security risk if exposed in user profile.
    # I will assumes this is the user profile update route.
    
    # Gestion des images avec validation stricte
    from utils.file_validation import FileValidationError, process_and_save_image
    
    # 1. Avatar (80x80)
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename != '':
            try:
                # Supprimer l'ancien avatar si existant
                if current_user.avatar_url:
                    old_path = os.path.join(current_app.root_path, current_user.avatar_url.lstrip('/'))
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except OSError:
                            pass
                
                avatar_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'users', 'avatars')
                filename = process_and_save_image(
                    file, 
                    avatar_folder, 
                    prefix=f"avatar_{current_user.id}", 
                    target_size=DefaultValues.DEFAULT_AVATAR_SIZE
                )
                current_user.avatar_url = f"/static/uploads/users/avatars/{filename}"
            except FileValidationError as e:
                flash(f"Erreur Avatar: {str(e)}", 'danger')
            except Exception as e:
                 flash(f"Erreur inattendue Avatar: {str(e)}", 'danger')

    # 2. Photo de Profil (600x800)
    if 'profile_photo' in request.files:
        file = request.files['profile_photo']
        if file and file.filename != '':
            try:
                # Supprimer l'ancienne photo de profil si existante
                if current_user.profile_photo_url:
                    old_path = os.path.join(current_app.root_path, current_user.profile_photo_url.lstrip('/'))
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except OSError:
                            pass
                
                profile_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'users', 'profile')
                filename = process_and_save_image(
                    file, 
                    profile_folder, 
                    prefix=f"profile_{current_user.id}", 
                    target_size=DefaultValues.DEFAULT_PROFILE_PHOTO_SIZE
                )
                current_user.profile_photo_url = f"/static/uploads/users/profile/{filename}"
            except FileValidationError as e:
                flash(f"Erreur Photo Profil: {str(e)}", 'danger')
            except Exception as e:
                 flash(f"Erreur inattendue Photo Profil: {str(e)}", 'danger')

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
    
    page = request.args.get('page', 1, type=int)
    
    breadcrumbs = [
        ('Dashboard', url_for('admin.dashboard')),
        ('Utilisateurs', url_for('admin.admin_page', admin_view='users', page=page) + '#admin'),
        (user.email, '#')
    ]
    
    return render_template(
        'user_events.html',
        user=user,
        events_data=events_data,
        breadcrumbs=breadcrumbs,
        page=page
    )


@admin_bp.route('/admin/user/add', methods=['POST'])
@login_required
@admin_required
def admin_add_user():
    """Ajouter un utilisateur (admin uniquement)."""
    email = request.form.get('email')
    if User.query.filter_by(email=email).first():
        flash('Cet email existe déjà.', 'warning')
        return redirect(url_for('admin.admin_page', admin_view='add', _anchor='admin'))
        
    password = generate_password()
    hashed_password = generate_password_hash(password)
    
    new_user = User(email=email, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    send_email(email, "Bienvenue", f"Votre compte a été créé. Mot de passe : {password}")
    flash(f'Utilisateur {email} ajouté.', 'success')
    return redirect(url_for('admin.admin_page', admin_view='users', open_edit=new_user.id, _anchor='admin'))


@admin_bp.route('/admin/user/<int:user_id>/update_full', methods=['POST'])
@login_required
@admin_required
def admin_update_full_user(user_id):
    """Mise à jour complète d'un utilisateur (admin)."""
    user = User.query.get_or_404(user_id)
    
    # Sécurité: Non-Créateurs ne peuvent pas éditer les Créateurs
    if user.role == UserRole.CREATEUR.value and current_user.role != UserRole.CREATEUR.value:
        flash('Vous ne pouvez pas modifier un compte administrateur suprême (Créateur).', 'danger')
        return redirect(url_for('admin.admin_page', admin_view='users', _anchor='admin'))
    
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
    # Redirect to admin page (users view) instead of dashboard
    page = request.args.get('page', 1, type=int)
    return redirect(url_for('admin.admin_page', admin_view='users', page=page, _anchor='admin'))


@admin_bp.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    """Suppression d'un utilisateur (admin)."""
    user = User.query.get_or_404(user_id)
    
    # Sécurité: Ne peut pas se supprimer soi-même
    if user.id == current_user.id:
        flash("Vous ne pouvez pas supprimer votre propre compte ici.", "danger")
        return redirect(url_for('admin.admin_page', admin_view='users', _anchor='admin'))
        
    # Sécurité: Non-Creator ne peut pas supprimer Creator
    if user.role == UserRole.CREATEUR.value and current_user.role != UserRole.CREATEUR.value:
        flash("Vous ne pouvez pas supprimer un compte Créateur.", "danger")
        return redirect(url_for('admin.admin_page', admin_view='users', _anchor='admin'))

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
        from models import AccountValidationToken, PasswordResetToken, GFormsSubmission, EventNotification
        AccountValidationToken.query.filter_by(email=user.email).delete()
        PasswordResetToken.query.filter_by(email=user.email).delete()
        
        # Supprimer les soumissions GForms
        GFormsSubmission.query.filter_by(user_id=user.id).delete()
        
        # Supprimer les notifications liées
        EventNotification.query.filter_by(user_id=user.id).delete()
        
        # Supprimer les logs d'activité générés par cet utilisateur
        ActivityLog.query.filter_by(user_id=user.id).delete()
        
        # Supprimer les participations
        Participant.query.filter_by(user_id=user.id).delete()
        
        # Logger l'action (par l'admin courant)
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
    except DatabaseError as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
        
    page = request.args.get('page', 1, type=int)
    return redirect(url_for('admin.admin_page', admin_view='users', page=page, _anchor='admin'))


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


@admin_bp.route('/admin/logs/delete-all', methods=['POST'])
@login_required
@admin_required
def delete_all_logs():
    """Supprime tous les logs d'activité."""
    try:
        # Suppression de tous les enregistrements
        num_deleted = db.session.query(ActivityLog).delete()
        db.session.commit()
        flash(f"{num_deleted} logs ont été supprimés.", "success")
    except DatabaseError as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression des logs : {str(e)}", "danger")
    
    return redirect(url_for('admin.admin_logs'))


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


@admin_bp.route('/deregister', methods=['POST'])
@login_required
def deregister():
    """
    Traite la désinscription d'un utilisateur.
    
    Actions effectuées:
    1. Retrait de tous les événements
    2. Notifications aux organisateurs  
    3. Annulation des événements si organisateur unique
    4. Soft delete ou hard delete selon l'option choisie
    5. Déconnexion de l'utilisateur
    """
    delete_data = request.form.get('delete_data') == 'on'
    
    # Récupérer toutes les participations
    participations = Participant.query.filter_by(user_id=current_user.id).all()
    
    # Traiter chaque participation
    for participant in participations:
        event = participant.event
        
        # Créer une notification pour les organisateurs de l'événement
        from services.notification_service import create_notification
        description = f"{current_user.prenom} {current_user.nom} s'est désinscrit(e) de l'événement ({participant.type})"
        create_notification(
            event_id=event.id,
            user_id=current_user.id,
            action_type='participant_left',
            description=description
        )
        
        # Si l'utilisateur est organisateur, vérifier s'il est le seul
        if participant.type == 'Organisateur':
            remaining_organizers = Participant.query.filter_by(
                event_id=event.id,
                type='Organisateur'
            ).filter(Participant.user_id != current_user.id).count()
            
            # Si c'est le seul organisateur, annuler l'événement
            if remaining_organizers == 0:
                event.statut = 'Annulé'
                db.session.add(event)
        
        # Retirer la participation
        db.session.delete(participant)
    
    # Traiter le compte utilisateur selon l'option choisie
    if delete_data:
        # Hard delete: supprimer complètement l'utilisateur
        # Supprimer les tokens associés
        from models import AccountValidationToken, PasswordResetToken, EventNotification
        AccountValidationToken.query.filter_by(email=current_user.email).delete()
        PasswordResetToken.query.filter_by(email=current_user.email).delete()
        
        # Supprimer les notifications créées par cet utilisateur
        EventNotification.query.filter_by(user_id=current_user.id).delete()
        
        # Supprimer l'utilisateur
        user_email = current_user.email
        db.session.delete(current_user)
        db.session.commit()
        
        logout_user()
        flash(f'Votre compte {user_email} a été complètement supprimé.', 'success')
    else:
        # Soft delete: marquer comme désinscrit
        current_user.account_status = 'deregistered'
        current_user.is_deleted = True
        db.session.commit()
        
        logout_user()
        flash('Vous avez été désinscrit. Vos données ont été conservées.', 'success')
    
    return redirect(url_for('auth.index'))

