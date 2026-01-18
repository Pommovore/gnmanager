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

from flask import Blueprint, render_template, request, redirect, url_for, flash
from markupsafe import Markup
from flask_login import login_required, current_user
from models import db, Event, Participant, ActivityLog, Role
from datetime import datetime
from constants import ParticipantType, EventStatus, ActivityLogType, RegistrationStatus
from decorators import organizer_required
from exceptions import DatabaseError
import json

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
            org_link_url=request.form.get('org_link_url', ''),
            org_link_title=request.form.get('org_link_title', ''),
            google_form_url=request.form.get('google_form_url', '')
        )
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
    
    is_organizer = participant and participant.type.lower() == ParticipantType.ORGANISATEUR.value.lower()
    groups_config = json.loads(event.groups_config or '{}')

    # Calcul des compteurs de participants (hors rejetés)
    count_pjs = Participant.query.filter_by(event_id=event.id, type=ParticipantType.PJ.value).filter(Participant.registration_status != RegistrationStatus.REJECTED.value).count()
    count_pnjs = Participant.query.filter_by(event_id=event.id, type=ParticipantType.PNJ.value).filter(Participant.registration_status != RegistrationStatus.REJECTED.value).count()
    count_orgs = Participant.query.filter_by(event_id=event.id, type=ParticipantType.ORGANISATEUR.value).filter(Participant.registration_status != RegistrationStatus.REJECTED.value).count()
    
    breadcrumbs = [
        ('GN Manager', url_for('admin.dashboard')),
        (event.name, '#')  # Page actuelle
    ]

    return render_template('event_detail.html', event=event, participant=participant, is_organizer=is_organizer, groups_config=groups_config, breadcrumbs=breadcrumbs,
                          count_pjs=count_pjs, count_pnjs=count_pnjs, count_orgs=count_orgs)


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
    discord_webhook_url = request.form.get('discord_webhook_url')
    
    try:
        if name: event.name = name
        if location: event.location = location
        # On sauvegarde le webhook tel quel, même si vide
        event.discord_webhook_url = discord_webhook_url
        if date_start_str: 
            event.date_start = datetime.strptime(date_start_str, '%Y-%m-%d')
        if date_end_str: 
            event.date_end = datetime.strptime(date_end_str, '%Y-%m-%d')
        if description is not None: event.description = description
        if org_link_url is not None: event.org_link_url = org_link_url
        if org_link_title is not None: event.org_link_title = org_link_title
        if google_form_url is not None: event.google_form_url = google_form_url
        
        # Mise à jour des jauges
        if request.form.get('max_pjs'):
            event.max_pjs = int(request.form.get('max_pjs'))
        if request.form.get('max_pnjs'):
            event.max_pnjs = int(request.form.get('max_pnjs'))
        if request.form.get('max_organizers'):
            event.max_organizers = int(request.form.get('max_organizers'))
        
        # Checkbox handling: presence means True
        event.google_form_active = 'google_form_active' in request.form
            
        event.google_form_active = 'google_form_active' in request.form
            
        db.session.commit()
        
        # Log update
        log = ActivityLog(
            action_type=ActivityLogType.EVENT_UPDATE.value,
            user_id=current_user.id,
            event_id=event.id,
            details=json.dumps({'updated_fields': 'General Info (Name, Date, Limits, etc.)', 'event_name': event.name})
        )
        db.session.add(log)
        db.session.commit()

        flash('Informations générales mises à jour.', 'success')
    except (ValueError, TypeError) as e:
        flash('Erreur de format de date. Veuillez utiliser le format AAAA-MM-JJ.', 'danger')
        
    return redirect(url_for('event.detail', event_id=event.id))


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
        # Création et sauvegarde de la participation
        participant = Participant(
            event_id=event.id, 
            user_id=current_user.id,
            type=registration_type,
            registration_status=status,
            comment=comment,
            paf_status='non versée'
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
    if participant and participant.type.lower() == ParticipantType.ORGANISATEUR.value.lower():
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
