"""
Blueprint pour les routes li

ées aux événements.

Ce module gère :
- Création d'événements
- Consultation des détails
- Modification des informations générales
- Modification du statut
- Configuration des groupes
- Inscription à un événement
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from markupsafe import Markup
from flask_login import login_required, current_user
from models import db, Event, Participant, Role, CastingProposal, CastingAssignment, ActivityLog, User
import json
import logging
from datetime import datetime
from constants import ParticipantType, EventStatus, RegistrationStatus, ActivityLogType
from decorators import organizer_required
from exceptions import DatabaseError
from sqlalchemy.orm import joinedload
import numpy as np
from scipy.optimize import linear_sum_assignment

event_bp = Blueprint('event', __name__)


@event_bp.route('/event/create', methods=['GET', 'POST'])
@login_required
def create_event():
    """
    Création d'un nouvel événement.
    
    L'utilisateur qui crée l'événement devient automatiquement organisateur.
    
    Returns:
        Template event_create.html ou redirection vers l'événement créé
    """
    if request.method == 'POST':
        name = request.form.get('name')
        date_start_str = request.form.get('date_start')
        date_end_str = request.form.get('date_end')
        location = request.form.get('location')
        visibility = request.form.get('visibility')
        
        try:
            date_start = datetime.strptime(date_start_str, '%Y-%m-%d')
            date_end = datetime.strptime(date_end_str, '%Y-%m-%d')
        except (ValueError, TypeError) as e:
            flash('Format de date invalide. Veuillez utiliser le format AAAA-MM-JJ.', 'danger')
            return redirect(url_for('event.create_event'))
        
        new_event = Event(
            name=name, 
            description=request.form.get('description', ''),
            date_start=date_start, 
            date_end=date_end, 
            location=location, 
            visibility=visibility, 
            statut=EventStatus.PREPARATION.value,  # 'En préparation'
            org_link_title=request.form.get('org_link_title', ''),
            google_form_url=request.form.get('google_form_url', ''),
            organizing_association=request.form.get('organizing_association'),
            display_organizers=request.form.get('display_organizers') == 'on'
        )
        
        # Generate generic webhook secret
        import secrets
        new_event.webhook_secret = secrets.token_hex(16).upper()
        
        db.session.add(new_event)
        db.session.commit()
        
        # Ajouter le créateur comme organisateur
        participant = Participant(
            event_id=new_event.id, 
            user_id=current_user.id, 
            type=ParticipantType.ORGANISATEUR.value,
            role_communicated=True, 
            registration_status=RegistrationStatus.VALIDATED.value
        )
        db.session.add(participant)
        db.session.commit()
        
        # Logger la création de l'événement
        log = ActivityLog(
            action_type=ActivityLogType.EVENT_CREATION.value,
            user_id=current_user.id,
            event_id=new_event.id,
            details=json.dumps({
                'event_name': name,
                'location': location,
                'date_start': date_start.strftime('%Y-%m-%d'),
                'date_end': date_end.strftime('%Y-%m-%d')
            })
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Événement créé avec succès !', 'success')
        return redirect(url_for('event.detail', event_id=new_event.id))
        
    return render_template('event_create.html')


@event_bp.route('/event/<int:event_id>')
@login_required
def detail(event_id):
    """
    Affiche les détails d'un événement.
    
    Args:
        event_id: ID de l'événement à afficher
        
    Returns:
        Template avec les informations de l'événement
    """
    from sqlalchemy.orm import joinedload
    
    # Eager load participants and users to avoid N+1 queries
    event = Event.query\
        .options(joinedload(Event.participants).joinedload(Participant.user))\
        .get_or_404(event_id)
    # Vérifier si l'utilisateur est participant
    participant = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    
    is_organizer = participant and participant.is_organizer and participant.registration_status == RegistrationStatus.VALIDATED.value
    groups_config = json.loads(event.groups_config or '{}')

    # Calcul des compteurs de participants (hors rejetés)
    from sqlalchemy import func
    count_pjs = Participant.query.filter_by(event_id=event.id).filter(
        func.lower(Participant.type) == ParticipantType.PJ.value.lower(),
        Participant.registration_status != RegistrationStatus.REJECTED.value
    ).count()
    count_pnjs = Participant.query.filter_by(event_id=event.id).filter(
        func.lower(Participant.type) == ParticipantType.PNJ.value.lower(),
        Participant.registration_status != RegistrationStatus.REJECTED.value
    ).count()
    count_orgs = Participant.query.filter_by(event_id=event.id).filter(
        func.lower(Participant.type) == ParticipantType.ORGANISATEUR.value.lower(),
        Participant.registration_status != RegistrationStatus.REJECTED.value
    ).count()
    
    # Récupérer les rôles de l'événement avec eager loading des assignments pour la modale de suppression
    roles = Role.query.filter_by(event_id=event.id)\
        .options(
            joinedload(Role.casting_assignments).joinedload(CastingAssignment.proposal),
            joinedload(Role.casting_assignments).joinedload(CastingAssignment.participant).joinedload(Participant.user)
        )\
        .order_by(Role.name).all()
    
    # Récupérer le rôle assigné au participant courant (si casting validé)
    assigned_role = None
    if participant and event.is_casting_validated:
        # Check if participant has a role assigned via Role.assigned_participant_id
        assigned_role = Role.query.filter_by(
            event_id=event.id,
            assigned_participant_id=participant.id
        ).first()
    
    # PAF Config
    try:
        paf_config = json.loads(event.paf_config or '[]')
    except json.JSONDecodeError:
        paf_config = []
    
    paf_map = {item['name']: item['amount'] for item in paf_config if 'name' in item and 'amount' in item}
    
    # Récupérer les notifications pour les organisateurs
    notifications = []
    unread_count = 0
    if is_organizer:
        from services.notification_service import get_event_notifications, count_unread_notifications
        notifications = get_event_notifications(event_id)
        unread_count = count_unread_notifications(event_id)

    breadcrumbs = [
        ('GN Manager', url_for('admin.dashboard')),
        (event.name, '#')  # Page actuelle
    ]

    return render_template('event_detail.html', event=event, participant=participant, is_organizer=is_organizer, groups_config=groups_config, breadcrumbs=breadcrumbs,
                          count_pjs=count_pjs, count_pnjs=count_pnjs, count_orgs=count_orgs, roles=roles, assigned_role=assigned_role,
                          paf_config=paf_config, paf_map=paf_map, notifications=notifications, unread_count=unread_count)


@event_bp.route('/event/<int:event_id>/update_general', methods=['POST'])
@login_required
@organizer_required
def update_general(event_id):
    """
    Mise à jour des informations générales d'un événement.
    
    Accès réservé aux organisateurs.
    
    Args:
        event_id: ID de l'événement à modifier
    """
    event = Event.query.get_or_404(event_id)
        
    name = request.form.get('name')
    location = request.form.get('location')
    date_start_str = request.form.get('date_start')
    date_end_str = request.form.get('date_end')
    description = request.form.get('description')
    org_link_url = request.form.get('org_link_url')
    org_link_title = request.form.get('org_link_title')
    org_link_title = request.form.get('org_link_title')
    google_form_url = request.form.get('google_form_url')
    organizing_association = request.form.get('organizing_association')
    discord_webhook_url = request.form.get('discord_webhook_url')
    display_organizers = request.form.get('display_organizers') == 'on'
    statut = request.form.get('statut')
    
    try:
        # Validation des dates AVANT toute modification
        if date_start_str and date_end_str:
            start = datetime.strptime(date_start_str, '%Y-%m-%d')
            end = datetime.strptime(date_end_str, '%Y-%m-%d')
            if end < start:
                flash("La date de fin ne peut pas être antérieure à la date de début.", "danger")
                return redirect(url_for('event.detail', event_id=event_id))
        
        # Application des modifications si validation OK
        if name: event.name = name
        if location: event.location = location
        if organizing_association: event.organizing_association = organizing_association
        event.display_organizers = display_organizers
        if statut: event.statut = statut
        event.discord_webhook_url = discord_webhook_url
        
        if date_start_str: 
            event.date_start = datetime.strptime(date_start_str, '%Y-%m-%d')
        if date_end_str: 
            event.date_end = datetime.strptime(date_end_str, '%Y-%m-%d')
            
        if description is not None: event.description = description
        if google_form_url is not None: event.google_form_url = google_form_url
        
        # Upload des images de fond avec validation stricte
        import os
        from flask import current_app
        from utils.file_validation import save_validated_file, FileValidationError
        
        def save_event_image(file, suffix):
            """Sauvegarder une image d'événement avec validation stricte."""
            if file and file.filename:
                try:
                    upload_folder = os.path.join(current_app.root_path, 'static/uploads/events')
                    filename = save_validated_file(file, upload_folder, prefix=f"{event.id}_{suffix}")
                    return f"uploads/events/{filename}"
                except FileValidationError as e:
                    flash(str(e), 'danger')
                    return None
            return None

        if 'background_image_light' in request.files:
            path = save_event_image(request.files['background_image_light'], 'light')
            if path: event.background_image_light = path

        if 'background_image_dark' in request.files:
            path = save_event_image(request.files['background_image_dark'], 'dark')
            if path: event.background_image_dark = path

        # Gestion des liens multiples
        # 1. Nettoyer les anciens liens
        from models import EventLink
        for link in event.links:
            db.session.delete(link)
            
        # 2. Ajouter les nouveaux liens
        link_titles = request.form.getlist('link_titles[]')
        link_urls = request.form.getlist('link_urls[]')
        
        for i, (title, url) in enumerate(zip(link_titles, link_urls)):
            if title.strip() and url.strip():
                new_link = EventLink(
                    event_id=event.id,
                    title=title.strip(),
                    url=url.strip(),
                    position=i
                )
                db.session.add(new_link)
        
        # Mise à jour des jauges
        if request.form.get('max_pjs'):
            event.max_pjs = int(request.form.get('max_pjs'))
        if request.form.get('max_pnjs'):
            event.max_pnjs = int(request.form.get('max_pnjs'))
        if request.form.get('max_organizers'):
            event.max_organizers = int(request.form.get('max_organizers'))
            
        # Configuration PAF
        paf_names = request.form.getlist('paf_names[]')
        paf_amounts = request.form.getlist('paf_amounts[]')
        paf_config = []
        for name, amount in zip(paf_names, paf_amounts):
            if name.strip():
                try:
                    paf_config.append({'name': name.strip(), 'amount': float(amount) if amount else 0})
                except ValueError:
                    pass
        event.paf_config = json.dumps(paf_config)
        
        # Configuration des moyens de paiement
        payment_methods_raw = request.form.get('payment_methods', '').strip()
        if payment_methods_raw:
            # Parse comma-separated list
            methods = [m.strip() for m in payment_methods_raw.split(',') if m.strip()]
            event.payment_methods = json.dumps(methods)
        elif payment_methods_raw == '':
            # Si le champ est vide, garder au moins Helloasso
            event.payment_methods = json.dumps(['Helloasso'])
        
        # Checkbox handling: presence means True
        event.google_form_active = 'google_form_active' in request.form
             
        db.session.commit()
        
        # Log update
        log = ActivityLog(
            action_type=ActivityLogType.EVENT_UPDATE.value,
            user_id=current_user.id,
            event_id=event.id,
            details=json.dumps({'updated_fields': 'General Info (Name, Date, Limits, Links, Image)', 'event_name': event.name})
        )
        db.session.add(log)
        db.session.commit()
        
        # Créer une notification pour les organisateurs
        from services.notification_service import create_notification
        changed_fields = []
        if name and name != event.name: changed_fields.append('nom')
        if location and location != event.location: changed_fields.append('lieu')
        if date_start_str: changed_fields.append('dates')
        if description is not None: changed_fields.append('description')
        
        if changed_fields:
            create_notification(
                event_id=event.id,
                user_id=current_user.id,
                action_type='event_updated',
                description=f"{current_user.prenom} {current_user.nom} a modifié: {', '.join(changed_fields)}"
            )

        flash('Informations générales mises à jour.', 'success')
    except (ValueError, TypeError) as e:
        flash('Erreur de format de date. Veuillez utiliser le format AAAA-MM-JJ.', 'danger')
        
    return redirect(url_for('event.detail', event_id=event.id))


@event_bp.route('/event/<int:event_id>/regenerate_secret', methods=['POST'])
@login_required
@organizer_required
def regenerate_secret(event_id):
    """
    Régénère le webhook_secret d'un événement.
    
    Accès réservé aux organisateurs.
    """
    event = Event.query.get_or_404(event_id)
    
    import secrets
    new_secret = secrets.token_hex(16).upper()
    event.webhook_secret = new_secret
    
    # Log deletion/update
    log = ActivityLog(
        action_type=ActivityLogType.EVENT_UPDATE.value,
        user_id=current_user.id,
        event_id=event.id,
        details=json.dumps({
            'updated_fields': 'webhook_secret (regenerated)',
            'event_name': event.name
        })
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'new_secret': new_secret
    })


@event_bp.route('/event/<int:event_id>/update_status', methods=['POST'])
@login_required
@organizer_required
def update_status(event_id):
    """
    Mise à jour du statut d'un événement.
    
    Accès réservé aux organisateurs.
    """
    # Import sqlalchemy for eager loading
    from sqlalchemy.orm import joinedload
    
    # Eager load participants and their users to avoid N+1 queries
    event = Event.query\
        .options(joinedload(Event.participants).joinedload(Participant.user))\
        .get_or_404(event_id)
        
    statut = request.form.get('statut')
    if statut:
        old_status = event.statut
        event.statut = statut
        db.session.commit()
        
        # Log status change
        log = ActivityLog(
            action_type=ActivityLogType.STATUS_CHANGE.value,
            user_id=current_user.id,
            event_id=event.id,
            details=json.dumps({
                'old_status': old_status, 
                'new_status': statut, 
                'target': 'EVENT',
                'event_name': event.name,
                'changed_by': current_user.email
            })
        )
        db.session.add(log)
        db.session.commit()

        flash('Statut mis à jour.', 'success')
        
    return redirect(url_for('event.detail', event_id=event.id))


@event_bp.route('/event/<int:event_id>/update_groups', methods=['POST'])
@login_required
@organizer_required
def update_groups(event_id):
    """
    Mise à jour de la configuration des groupes pour un événement.
    
    Accès réservé aux organisateurs.
    """
    event = Event.query.get_or_404(event_id)
        
    # Expecting form data: groups_pj, groups_pnj, groups_org (comma separated strings)
    groups_pj = [g.strip() for g in request.form.get('groups_pj', '').split(',') if g.strip()]
    groups_pnj = [g.strip() for g in request.form.get('groups_pnj', '').split(',') if g.strip()]
    groups_org = [g.strip() for g in request.form.get('groups_org', '').split(',') if g.strip()]
    
    config = {
        "PJ": groups_pj,
        "PNJ": groups_pnj,
        "Organisateur": groups_org
    }
    
    event.groups_config = json.dumps(config)
    db.session.commit()
    
    # Log groups update
    log = ActivityLog(
        action_type=ActivityLogType.GROUPS_UPDATE.value,
        user_id=current_user.id,
        event_id=event.id,
        details=json.dumps({'message': 'Groups configuration updated'})
    )
    db.session.add(log)
    db.session.commit()
    
    flash('Configuration des groupes mise à jour.', 'success')
    return redirect(url_for('event.detail', event_id=event.id))


@event_bp.route('/event/<int:event_id>/add_role', methods=['POST'])
@login_required
@organizer_required
def add_role(event_id):
    """
    Ajout d'un nouveau rôle à un événement.
    
    Accès réservé aux organisateurs.
    """
    event = Event.query.get_or_404(event_id)
    
    name = request.form.get('name')
    if not name:
        flash('Le nom du rôle est obligatoire.', 'danger')
        return redirect(url_for('event.detail', event_id=event.id) + '#list-roles')
    
    new_role = Role(
        event_id=event.id,
        name=name,
        type=request.form.get('type') or None,
        genre=request.form.get('genre') or None,
        group=request.form.get('group') or None,
        google_doc_url=request.form.get('google_doc_url') or None,
        pdf_url=request.form.get('pdf_url') or None,
        comment=request.form.get('comment') or None
    )
    
    db.session.add(new_role)
    db.session.commit()
    
    flash(f'Rôle "{name}" créé avec succès.', 'success')
    return redirect(url_for('event.detail', event_id=event.id) + '#list-roles')


@event_bp.route('/event/<int:event_id>/update_role/<int:role_id>', methods=['POST'])
@login_required
@organizer_required
def update_role(event_id, role_id):
    """
    Mise à jour d'un rôle existant.
    
    Accès réservé aux organisateurs.
    """
    event = Event.query.get_or_404(event_id)
    role = Role.query.filter_by(id=role_id, event_id=event_id).first_or_404()
    
    name = request.form.get('name')
    if not name:
        flash('Le nom du rôle est obligatoire.', 'danger')
        return redirect(url_for('event.detail', event_id=event.id) + '#list-roles')
    
    role.name = name
    role.type = request.form.get('type') or None
    role.genre = request.form.get('genre') or None
    role.group = request.form.get('group') or None
    role.google_doc_url = request.form.get('google_doc_url') or None
    role.pdf_url = request.form.get('pdf_url') or None
    role.comment = request.form.get('comment') or None
    
    db.session.commit()
    
    flash(f'Rôle "{name}" mis à jour.', 'success')
    return redirect(url_for('event.detail', event_id=event.id) + '#list-roles')


@event_bp.route('/event/<int:event_id>/role/<int:role_id>/delete', methods=['POST'])
@login_required
@organizer_required
def delete_role(event_id, role_id):
    """
    Suppression d'un rôle.
    
    Accès réservé aux organisateurs.
    """
    event = Event.query.get_or_404(event_id)
    role = Role.query.filter_by(id=role_id, event_id=event_id).first_or_404()
    
    # Unassign participants associated with this role
    participants = Participant.query.filter_by(role_id=role.id).all()
    for p in participants:
        p.role_id = None
        p.role_communicated = False
        p.role_received = False
        
    # Delete associated casting assignments explicitly to avoid IntegrityError
    # (casting_assignment.role_id cannot be null)
    CastingAssignment.query.filter_by(role_id=role.id).delete()
    
    db.session.delete(role)
    db.session.commit()
    
    flash(f'Rôle "{role.name}" supprimé.', 'success')
    return redirect(url_for('event.detail', event_id=event.id) + '#list-roles')





@event_bp.route('/event/<int:event_id>/join', methods=['POST'])
@login_required
def join(event_id):
    """
    Inscription à un événement.
    
    Le statut initial est 'À valider' et nécessite validation par un organisateur.
    """
    event = Event.query.get_or_404(event_id)
    
    if event.statut in ['Annulé', 'Terminé']:
        flash('Impossible de rejoindre cet événement (Annulé ou Terminé).', 'danger')
        return redirect(url_for('event.detail', event_id=event.id))
        
    if Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first():
        flash('Vous participez déjà à cet événement.', 'warning')
        return redirect(url_for('event.detail', event_id=event.id))
    
    registration_type = request.form.get('type', ParticipantType.PJ.value)
    # The new code snippet does not use p_group, but the Participant model might require it.
    # Assuming 'group' is still relevant and should be passed, or it's handled differently.
    # For now, I'll keep it as it was in the original code, but the new Participant constructor doesn't include it.
    # Based on the provided snippet, the 'group' field is omitted in the new Participant creation.
    # The new code also implies a 'status' variable, which was previously hardcoded as TO_VALIDATE.
    status = RegistrationStatus.TO_VALIDATE.value
    comment = request.form.get('comment')
    if comment is None: # Handle empty comments explicitly
        comment = ""
    
    try:
        # Récupérer les préférences de partage (par défaut True)
        share_phone = request.form.get('share_phone', 'on') == 'on'
        share_discord = request.form.get('share_discord', 'on') == 'on'
        share_facebook = request.form.get('share_facebook', 'on') == 'on'
        
        # Création et sauvegarde de la participation
        participant = Participant(
            event_id=event.id, 
            user_id=current_user.id,
            type=registration_type,
            registration_status=status,
            comment=comment,
            paf_status='non versée',
            # Copier les coordonnées du User vers le Participant
            participant_phone=current_user.phone if share_phone else None,
            participant_discord=current_user.discord if share_discord else None,
            participant_facebook=current_user.facebook if share_facebook else None,
            # Flags de consentement
            share_phone=share_phone,
            share_discord=share_discord,
            share_facebook=share_facebook
        )
        db.session.add(participant)
        
        # Log de l'activité
        log = ActivityLog(
            user_id=current_user.id,
            action_type=ActivityLogType.EVENT_PARTICIPATION.value,
            event_id=event.id,
            details=json.dumps({
                'type': registration_type,
                'status': status,
                'comment': comment
            })
        )
        db.session.add(log)
        db.session.commit()
        
        # Créer une notification pour les organisateurs
        from services.notification_service import create_notification
        create_notification(
            event_id=event.id,
            user_id=current_user.id,
            action_type='participant_join_request',
            description=f"{current_user.prenom} {current_user.nom} a demandé à participer en tant que {registration_type}"
        )
        
        # Notification Discord
        if event.discord_webhook_url:
            from services.discord_service import send_discord_notification
            user_data = {
                'nom': current_user.nom,
                'prenom': current_user.prenom,
                'email': current_user.email
            }
            # On lance la notif mais on ne bloque pas si ça échoue (loggé dans le service)
            send_discord_notification(event.discord_webhook_url, event.name, user_data, registration_type)
            
        flash('Votre demande de participation a été enregistrée.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f"Une erreur est survenue lors de l'inscription : {str(e)}", 'danger')

    if event.google_form_active and event.google_form_url:
        message = Markup(f"Veuillez remplir ce formulaire si ce n'est pas déjà fait : <a href='{event.google_form_url}' target='_blank' class='alert-link'>Formulaire</a>")
        flash(message, 'info')
        
    return redirect(url_for('event.detail', event_id=event.id))


@event_bp.route('/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    """
    Suppression complète d'un événement et de ses données associées.
    
    Accessible aux admin, créateurs et organisateurs de l'événement.
    """
    event = Event.query.get_or_404(event_id)
    
    # Vérification des permissions
    is_organizer = False
    participant = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if participant and participant.type.lower() == ParticipantType.ORGANISATEUR.value.lower() and participant.registration_status == RegistrationStatus.VALIDATED.value:
        is_organizer = True
        
    if not (current_user.is_admin or is_organizer):
        flash("Vous n'avez pas les droits pour supprimer cet événement.", "danger")
        return redirect(url_for('event.detail', event_id=event_id))
        
    try:
        event_name = event.name # Sauvegarde du nom pour le log
        
        # 1. Supprimer les Rôles (Cascade manuelle si nécessaire, mais foreign key set to null or delete logic needed)
        # Note: SQLAlchemy cascade might handle this depending on model def, but explicit is safer here to be sure
        Role.query.filter_by(event_id=event.id).delete()
        
        # 2. Supprimer les Participants
        Participant.query.filter_by(event_id=event.id).delete()
        
        # 3. Supprimer les Logs liés directement à l'événement ?
        # Le User demande "toutes les données concernant cet événement". 
        # Les anciens ActivityLogs référençant l'event_id vont avoir event_id=NULL si on ne les supprime pas et que la contrainte le fait.
        # Mais pour l'historique système, on préfère souvent garder les traces même si l'objet est supprimé.
        # Cependant, pour respecter "toutes les données", on va laisser l'activity log de suppression faire foi.
        # On va mettre à NULL les event_id des logs existants pour éviter les incohérences ou erreurs FK, 
        # ou les laisser tels quels si la BDD est configurée en CASCADE (ce qui n'est pas garanti par défaut en SQLite/SQLAlchemy sans config explicite).
        # On va explicitement set NULL pour être propre.
        ActivityLog.query.filter_by(event_id=event.id).update({'event_id': None})
        
        # 4. Supprimer l'événement
        db.session.delete(event)
        
        # 5. Logger la suppression
        log = ActivityLog(
            action_type=ActivityLogType.EVENT_DELETION.value,
            user_id=current_user.id,
            details=json.dumps({
                'event_name': event_name,
                'deleted_by_email': current_user.email
            })
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash(f"L'événement '{event_name}' et toutes ses données ont été supprimés.", "success")
        return redirect(url_for('admin.dashboard'))
        
    except DatabaseError as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
        return redirect(url_for('event.detail', event_id=event_id))


# ============================================================================
# Casting Routes
# ============================================================================

@event_bp.route('/event/<int:event_id>/casting')
@login_required
@organizer_required
def casting_interface(event_id):
    """
    Interface de gestion du casting.
    """
    event = Event.query.get_or_404(event_id)
    
    breadcrumbs = [
        ('GN Manager', url_for('admin.dashboard')),
        (event.name, url_for('event.detail', event_id=event.id)),
        ('Casting', '#')
    ]
    
    return render_template('casting.html', event=event, breadcrumbs=breadcrumbs)


@event_bp.route('/event/<int:event_id>/casting_data')
@login_required
@organizer_required
def casting_data(event_id):
    """
    Retourne les données de casting au format JSON.
    
    Inclut les participants groupés par type, les propositions, les attributions et les scores.
    """
    event = Event.query.get_or_404(event_id)
    
    # Get validated participants grouped by type
    participants = Participant.query.filter_by(
        event_id=event_id,
        registration_status=RegistrationStatus.VALIDATED.value
    ).options(joinedload(Participant.user)).all()
    
    participants_by_type = {}
    for p in participants:
        # Defensive check for missing user
        if not p.user:
            continue
            
        p_type = p.type or 'Autre'
        if p_type not in participants_by_type:
            participants_by_type[p_type] = []
        participants_by_type[p_type].append({
            'id': p.id,
            'nom': p.user.nom or '',
            'prenom': p.user.prenom or '',
            'genre': (p.user.genre or '').strip(),
            'global_comment': p.global_comment or ''
        })
    
    # Get proposals with assignments to avoid N+1
    proposals = CastingProposal.query.filter_by(event_id=event_id)\
        .options(joinedload(CastingProposal.assignments))\
        .order_by(CastingProposal.position).all()
    proposals_data = [{'id': p.id, 'name': p.name} for p in proposals]
    
    # Get assignments: {proposal_id: {role_id: {participant_id, score}}}
    assignments = {}
    scores = {}  # {proposal_id: {role_id: score}}
    
    # Add 'main' key for the default column (uses Role.assigned_participant_id)
    assignments['main'] = {}
    roles = Role.query.filter_by(event_id=event_id).all()
    for role in roles:
        if role.assigned_participant_id:
            assignments['main'][str(role.id)] = role.assigned_participant_id
    
    # Add proposal assignments and scores
    for proposal in proposals:
        assignments[str(proposal.id)] = {}
        scores[str(proposal.id)] = {}
        # Access assignments from eager loaded relationship instead of query
        try:
            for assignment in proposal.assignments:
                if assignment.participant_id:
                    assignments[str(proposal.id)][str(assignment.role_id)] = assignment.participant_id
                if assignment.score is not None:
                    scores[str(proposal.id)][str(assignment.role_id)] = assignment.score
        except Exception:
            pass
    
    return jsonify({
        'participants_by_type': participants_by_type,
        'proposals': proposals_data,
        'assignments': assignments,
        'scores': scores,
        'is_casting_validated': event.is_casting_validated or False,
        'groups_config': json.loads(event.groups_config) if event.groups_config else {},
        'roles': [{'id': r.id, 'name': r.name, 'type': r.type, 'genre': (getattr(r, 'genre', None) or '').strip(), 'group': getattr(r, 'group', None)} for r in roles]
    })


@event_bp.route('/event/<int:event_id>/casting/add_proposal', methods=['POST'])
@login_required
@organizer_required
def add_proposal(event_id):
    """
    Ajoute une nouvelle proposition de casting.
    """
    event = Event.query.get_or_404(event_id)
    
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'error': 'Le nom est requis'}), 400
    
    # Calculate next position
    max_pos = db.session.query(db.func.max(CastingProposal.position)).filter_by(event_id=event_id).scalar() or 0
    
    proposal = CastingProposal(
        event_id=event_id,
        name=name,
        position=max_pos + 1
    )
    db.session.add(proposal)
    db.session.commit()
    
    return jsonify({'id': proposal.id, 'name': proposal.name})


@event_bp.route('/event/<int:event_id>/casting/assign', methods=['POST'])
@login_required
@organizer_required
def casting_assign(event_id):
    """
    Attribue un participant à un rôle pour une proposition donnée.
    """
    event = Event.query.get_or_404(event_id)
    
    data = request.get_json()
    role_id = data.get('role_id')
    proposal_id = data.get('proposal_id')
    participant_id = data.get('participant_id')
    
    if not role_id:
        return jsonify({'error': 'role_id requis'}), 400
    
    role = Role.query.filter_by(id=role_id, event_id=event_id).first_or_404()
    
    # Handle 'main' proposal (direct role assignment)
    if proposal_id == 'main':
        if participant_id:
            role.assigned_participant_id = int(participant_id)
        else:
            role.assigned_participant_id = None
        db.session.commit()
        return jsonify({'success': True})
    
    # Handle custom proposal assignments
    # Find or create assignment
    proposal = CastingProposal.query.filter_by(id=proposal_id, event_id=event_id).first_or_404()
    
    # ... (rest of casting_assign logic if needed, but we are just appending new route)
    # Actually I should be appending *after* the function. The grep showed it around line 772.
    # I will target the end of casting_assign function to append. 
    # Wait, viewing the file showed casting_assign starts at 772. It ends around line 830 (not visible yet).
    # I'll just append to the end of the file or after add_proposal if I can find a clear spot.
    
    # Let me view the end of casting_assign first to place it correctly.

    assignment = CastingAssignment.query.filter_by(
        proposal_id=proposal_id,
        role_id=role_id
    ).first()
    
    if participant_id:
        if assignment:
            assignment.participant_id = int(participant_id)
        else:
            assignment = CastingAssignment(
                proposal_id=proposal_id,
                role_id=role_id,
                participant_id=int(participant_id),
                event_id=event_id
            )
            db.session.add(assignment)
    else:
        if assignment:
            db.session.delete(assignment)
    
    db.session.commit()
    return jsonify({'success': True})


@event_bp.route('/event/<int:event_id>/casting/delete_proposal', methods=['POST'])
@login_required
@organizer_required
def delete_proposal(event_id):
    """
    Supprime une proposition de casting et toutes ses attributions.
    """
    event = Event.query.get_or_404(event_id)
    
    data = request.get_json()
    proposal_id = data.get('proposal_id')
    
    if not proposal_id:
        return jsonify({'error': 'proposal_id requis'}), 400
    
    proposal = CastingProposal.query.filter_by(id=proposal_id, event_id=event_id).first_or_404()
    
    # Cascade delete handles assignments
    db.session.delete(proposal)
    db.session.commit()
    
    return jsonify({'success': True})


@event_bp.route('/event/<int:event_id>/casting/toggle_validation', methods=['POST'])
@login_required
@organizer_required
def toggle_casting_validation(event_id):
    """
    Bascule l'état de validation du casting.
    
    Quand validé, les participants peuvent voir leur rôle assigné.
    """
    event = Event.query.get_or_404(event_id)
    
    data = request.get_json() or {}
    validated = data.get('validated')
    
    if validated is not None:
        event.is_casting_validated = bool(validated)
    else:
        event.is_casting_validated = not event.is_casting_validated
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_casting_validated': event.is_casting_validated
    })


@event_bp.route('/event/<int:event_id>/casting/update_score', methods=['POST'])
@login_required
@organizer_required
def update_casting_score(event_id):
    """
    Met à jour le score d'une attribution de casting.
    """
    event = Event.query.get_or_404(event_id)
    
    data = request.get_json()
    proposal_id = data.get('proposal_id')
    role_id = data.get('role_id')
    score = data.get('score')
    
    if not proposal_id or not role_id:
        return jsonify({'error': 'proposal_id et role_id requis'}), 400
    
    if proposal_id == 'main':
        # Main column doesn't support scores (direct assignment)
        return jsonify({'error': 'Scores non supportés pour la colonne principale'}), 400
    
    # Find or create assignment
    assignment = CastingAssignment.query.filter_by(
        proposal_id=proposal_id,
        role_id=role_id
    ).first()
    
    if not assignment:
        # Create assignment with just the score (no participant yet)
        assignment = CastingAssignment(
            proposal_id=proposal_id,
            role_id=role_id,
            event_id=event_id,
            score=int(score) if score is not None and score != '' else None
        )
        db.session.add(assignment)
    else:
        assignment.score = int(score) if score is not None and score != '' else None
    
    db.session.commit()
    
    return jsonify({'success': True})


@event_bp.route('/event/<int:event_id>/casting/auto_assign', methods=['POST'])
@login_required
@organizer_required
def auto_assign_casting(event_id):
    """
    Calcule et attribue automatiquement les rôles en utilisant l'algorithme Hongrois (Kuhn-Munkres).
    Cela garantit une solution mathématiquement optimale pour maximiser le score global.
    """
    event = Event.query.get_or_404(event_id)
    
    # Vérifier que le casting n'est pas validé
    if event.is_casting_validated:
        return jsonify({'error': 'Le casting est déjà validé'}), 400
    
    # 1. Récupérer les données
    roles = Role.query.filter_by(event_id=event_id).all()
    n_roles = len(roles)
    
    # Récupérer tous les participants validés
    participants = Participant.query.filter_by(
        event_id=event_id, 
        registration_status=RegistrationStatus.VALIDATED.value
    ).all()
    n_parts = len(participants)
    
    if n_roles == 0 or n_parts == 0:
        return jsonify({
            'success': True,
            'assigned_count': 0,
            'total_roles': n_roles,
            'message': 'Pas de rôles ou pas de participants.'
        })
        
    # Mapping ID -> Index pour la matrice
    role_to_idx = {r.id: i for i, r in enumerate(roles)}
    part_to_idx = {p.id: i for i, p in enumerate(participants)}
    
    # 2. Construction de la Matrice d'Utilité
    utility_matrix = np.zeros((n_roles, n_parts))
    
    assignments = CastingAssignment.query.filter_by(event_id=event_id).all()
    
    for a in assignments:
        if a.participant_id and a.score is not None:
             if a.role_id in role_to_idx and a.participant_id in part_to_idx:
                 r_idx = role_to_idx[a.role_id]
                 p_idx = part_to_idx[a.participant_id]
                 # On somme les scores
                 utility_matrix[r_idx, p_idx] += a.score
    
    # 3. Matrice de Coût (Maximiser l'utilité => Minimiser -Utilité)
    cost_matrix = -utility_matrix
    
    # 4. Résolution (Algorithme Hongrois)
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    # 5. Application
    assigned_count = 0
    
    # Reset
    for role in roles:
        role.assigned_participant_id = None
        
    for i in range(len(row_ind)):
        r_idx = row_ind[i]
        p_idx = col_ind[i]
        
        role = roles[r_idx]
        participant = participants[p_idx]
        
        role.assigned_participant_id = participant.id
        assigned_count += 1
        
    db.session.commit()
    
    return jsonify({
        'success': True,
        'assigned_count': assigned_count,
        'total_roles': n_roles
    })


@event_bp.route('/event/<int:event_id>/notification/<int:notif_id>/mark_read', methods=['POST'])
@login_required
@organizer_required
def mark_notification_read(event_id, notif_id):
    """
    Marque une notification comme lue.
    
    Accès réservé aux organisateurs.
    """
    from models import EventNotification
    from services.notification_service import mark_as_read
    
    notification = EventNotification.query.get_or_404(notif_id)
    
    # Vérifier que la notification appartient bien à cet événement
    if notification.event_id != event_id:
        return jsonify({'success': False, 'error': 'Notification not found'}), 403
    
    success = mark_as_read(notif_id)
    return jsonify({'success': success})


@event_bp.route('/event/<int:event_id>/notifications/mark_all_read', methods=['POST'])
@login_required
@organizer_required
def mark_all_notifications_read(event_id):
    """
    Marque toutes les notifications d'un événement comme lues.
    """
    from models import EventNotification
    notifications = EventNotification.query.filter_by(event_id=event_id, is_read=False).all()
    for notif in notifications:
        notif.is_read = True
    db.session.commit()
    return jsonify({'success': True, 'count': len(notifications)})


@event_bp.route('/event/<int:event_id>/casting/reset_main', methods=['POST'])
@login_required
@organizer_required
def reset_main_casting(event_id):
    """
    Réinitialise toutes les attributions de la colonne principale (casting final).
    """
    event = Event.query.get_or_404(event_id)
    
    # Vérifier que le casting n'est pas validé
    if event.is_casting_validated:
        return jsonify({'error': 'Le casting est validé, impossible de réinitialiser.'}), 400
        
    roles = Role.query.filter_by(event_id=event_id).all()
    count = 0
    for role in roles:
        if role.assigned_participant_id:
            role.assigned_participant_id = None
            count += 1
            
    db.session.commit()
    
    return jsonify({'success': True, 'count': count})
