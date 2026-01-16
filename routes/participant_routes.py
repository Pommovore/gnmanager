"""
Blueprint pour les routes liées aux participants et au casting.

Ce module gère :
- Gestion des participants (affichage, mise à jour, statut)
- Interface de casting
- API d'assignation de rôles
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Event, Participant, Role, ActivityLog
from sqlalchemy.orm import joinedload
from constants import ParticipantType, RegistrationStatus, PAFStatus, ActivityLogType
from decorators import organizer_required
import json

participant_bp = Blueprint('participant', __name__)


@participant_bp.route('/event/<int:event_id>/participants')
@login_required
@organizer_required
def manage(event_id):
    """
    Interface de gestion des participants pour les organ

isateurs.
    
    Args:
        event_id: ID de l'événement
        
    Returns:
        Template de gestion des participants
    """
    event = Event.query.get_or_404(event_id)
        
    # Optimisation N+1 avec joinedload
    participants = Participant.query.filter_by(event_id=event.id)\
        .options(joinedload(Participant.user)).all()
        
    groups_config = json.loads(event.groups_config or '{}')
    
    breadcrumbs = [
        ('GN Manager', '/dashboard'),
        (event.name, url_for('event.detail', event_id=event.id)),
        ('Gestion des Participants', '#')
    ]
        
    return render_template('manage_participants.html', event=event, participants=participants, groups_config=groups_config, breadcrumbs=breadcrumbs)


@participant_bp.route('/event/<int:event_id>/participants/bulk_update', methods=['POST'])
@login_required
@organizer_required
def bulk_update(event_id):
    """
    Mise à jour groupée des participants.
    """
    event = Event.query.get_or_404(event_id)
        
    p_ids = request.form.getlist('participant_ids')
    
    for p_id in p_ids:
        p = Participant.query.get(p_id)
        if p and p.event_id == event.id:
            # Mise à jour des champs
            p.type = request.form.get(f'type_{p_id}', p.type)
            p.group = request.form.get(f'group_{p_id}', p.group)
            p.paf_status = request.form.get(f'paf_{p_id}', p.paf_status)
            
            # Mise à jour paiement
            pay_amt = request.form.get(f'pay_amount_{p_id}', '')
            p.payment_amount = float(pay_amt) if pay_amt else 0.0
            p.payment_method = request.form.get(f'pay_method_{p_id}', p.payment_method)
            p.comment = request.form.get(f'comment_{p_id}', p.comment)
            
    db.session.commit()
    flash('Participants mis à jour avec succès.', 'success')
    return redirect(url_for('participant.manage', event_id=event.id))


@participant_bp.route('/event/<int:event_id>/participant/<int:p_id>/update', methods=['POST'])
@login_required
@organizer_required
def update(event_id, p_id):
    """
    Met à jour un participant depuis la modal d'édition.
    """
    event = Event.query.get_or_404(event_id)
    
    p = Participant.query.get_or_404(p_id)
    if p.event_id != event_id:
        flash('Participant invalide pour cet événement.', 'danger')
        return redirect(url_for('participant.manage', event_id=event_id))
    
    # Mise à jour des champs
    p.type = request.form.get('type')
    p.group = request.form.get('group')
    p.paf_status = request.form.get('paf_status', PAFStatus.NOT_PAID.value)
    p.payment_amount = float(request.form.get('payment_amount', 0))
    p.payment_method = request.form.get('payment_method')
    p.comment = request.form.get('comment')
    
    db.session.commit()
    flash('Participant mis à jour.', 'success')
    return redirect(url_for('participant.manage', event_id=event_id))


@participant_bp.route('/event/<int:event_id>/participant/<int:p_id>/change-status', methods=['POST'])
@login_required
@organizer_required
def change_status(event_id, p_id):
    """
    Change le statut d'inscription d'un participant.
    
    Actions possibles via le paramètre 'action':
    - 'validate': Passe le statut à 'Validé'
    - 'reject': Passe le statut à 'Rejeté'
    - 'pending': Passe le statut à 'En attente'
    """
    event = Event.query.get_or_404(event_id)
    
    participant = Participant.query.get_or_404(p_id)
    if participant.event_id != event_id:
        flash('Participant invalide pour cet événement.', 'danger')
        return redirect(url_for('participant.manage', event_id=event_id))
    
    action = request.form.get('action')
    
    if action == 'validate':
        participant.registration_status = RegistrationStatus.VALIDATED.value
        flash(f'Participant {participant.user.email} validé.', 'success')
    elif action == 'reject':
        participant.registration_status = RegistrationStatus.REJECTED.value
        flash(f'Participant {participant.user.email} rejeté.', 'warning')
    elif action == 'pending':
        participant.registration_status = RegistrationStatus.PENDING.value
        flash(f'Participant {participant.user.email} mis en attente.', 'info')
    else:
        flash('Action invalide.', 'danger')
        return redirect(url_for('participant.manage', event_id=event_id))
    
    # Log de l'activité
    log = ActivityLog(
        user_id=current_user.id,
        action_type=ActivityLogType.STATUS_CHANGE.value,
        details=f"{participant.user.email} {participant.user.nom or ''} {participant.user.prenom or ''}"
    )
    db.session.add(log)
    
    db.session.commit()
    return redirect(url_for('participant.manage', event_id=event_id))


@participant_bp.route('/event/<int:event_id>/casting')
@login_required
@organizer_required
def casting(event_id):
    """
    Interface de casting pour assigner des rôles aux participants.
    
    Optimisé avec joinedload pour éviter les requêtes N+1.
    """
    event = Event.query.get_or_404(event_id)
        
    # Participants validés sans rôle (avec joinedload pour éviter N+1)
    participants_no_role = Participant.query.filter_by(
        event_id=event.id, 
        role_id=None,
        registration_status=RegistrationStatus.VALIDATED.value
    ).options(joinedload(Participant.user)).all()

    # Rôles de l'événement
    roles = Role.query.filter_by(event_id=event.id).order_by(Role.group).all()
    
    return render_template('casting.html', event=event, participants=participants_no_role, roles=roles)


@participant_bp.route('/api/casting/assign', methods=['POST'])
@login_required
def api_assign():
    """
    API pour assigner un rôle à un participant.
    
    Nécessite des droits d'organisateur.
    """
    data = request.json
    event_id = data.get('event_id')
    participant_id = data.get('participant_id')
    role_id = data.get('role_id')
    
    # Security check (organizer)
    event = Event.query.get_or_404(event_id)
    me = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not me or me.type != ParticipantType.ORGANISATEUR.value:
        return jsonify({'error': 'Unauthorized'}), 403
        
    participant = Participant.query.get_or_404(participant_id)
    role = Role.query.get_or_404(role_id)
    
    # Update both sides
    participant.role_id = role.id
    role.assigned_participant_id = participant.id
    
    db.session.commit()
    return jsonify({'success': True})


@participant_bp.route('/api/casting/unassign', methods=['POST'])
@login_required
def api_unassign():
    """
    API pour désassigner un rôle d'un participant.
    
    Nécessite des droits d'organisateur.
    """
    data = request.json
    event_id = data.get('event_id')
    role_id = data.get('role_id')
    
    event = Event.query.get_or_404(event_id)
    me = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not me or me.type != ParticipantType.ORGANISATEUR.value:
        return jsonify({'error': 'Unauthorized'}), 403

    if role_id:
        role = Role.query.get(role_id)
        if role and role.assigned_participant_id:
            p = Participant.query.get(role.assigned_participant_id)
            if p:
                p.role_id = None
            role.assigned_participant_id = None
            db.session.commit()
            return jsonify({'success': True})
            
    return jsonify({'error': 'Invalid request'}), 400
