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
from flask_login import login_required, current_user
from models import db, Event, Participant, ActivityLog
from datetime import datetime
from constants import ParticipantType, EventStatus, ActivityLogType, RegistrationStatus
from decorators import organizer_required
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
    event = Event.query.get_or_404(event_id)
    # Vérifier si l'utilisateur est participant
    participant = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    
    is_organizer = participant and participant.type.lower() == ParticipantType.ORGANISATEUR.value.lower()
    groups_config = json.loads(event.groups_config or '{}')
    
    breadcrumbs = [
        ('GN Manager', '/dashboard'),
        (event.name, '#')  # Page actuelle
    ]

    return render_template('event_detail.html', event=event, participant=participant, is_organizer=is_organizer, groups_config=groups_config, breadcrumbs=breadcrumbs)


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
    google_form_url = request.form.get('google_form_url')
    
    try:
        if name: event.name = name
        if location: event.location = location
        if date_start_str: 
            event.date_start = datetime.strptime(date_start_str, '%Y-%m-%d')
        if date_end_str: 
            event.date_end = datetime.strptime(date_end_str, '%Y-%m-%d')
        if description is not None: event.description = description
        if org_link_url is not None: event.org_link_url = org_link_url
        if org_link_title is not None: event.org_link_title = org_link_title
        if google_form_url is not None: event.google_form_url = google_form_url
            
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
    event = Event.query.get_or_404(event_id)
        
    statut = request.form.get('statut')
    if statut:
        event.statut = statut
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
    
    p_type = request.form.get('type', ParticipantType.PJ.value)
    p_group = request.form.get('group', 'Aucun')
    
    # Registration status default 'À valider'
    participant = Participant(
        event_id=event.id, 
        user_id=current_user.id, 
        type=p_type, 
        group=p_group,
        registration_status=RegistrationStatus.TO_VALIDATE.value
    )
    db.session.add(participant)
    db.session.commit()
    
    # Logger la demande de participation
    log = ActivityLog(
        action_type=ActivityLogType.EVENT_PARTICIPATION.value,
        user_id=current_user.id,
        event_id=event.id,
        details=json.dumps({
            'type': p_type,
            'group': p_group,
            'event_name': event.name
        })
    )
    db.session.add(log)
    db.session.commit()
    
    flash("Demande d'inscription envoyée ! En attente de validation.", 'success')
    return redirect(url_for('event.detail', event_id=event.id))
