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
import csv
import io
from flask import Response, session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime

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
        .options(joinedload(Participant.user), joinedload(Participant.role), joinedload(Participant.assigned_role_ref)).all()
        
    groups_config = json.loads(event.groups_config or '{}')
    
    breadcrumbs = [
        ('GN Manager', url_for('admin.dashboard')),
        (event.name, url_for('event.detail', event_id=event.id)),
        ('Gestion des Participants', '#')
    ]
        
    return render_template('manage_participants.html', event=event, participants=participants, groups_config=groups_config, breadcrumbs=breadcrumbs, is_organizer=True)


@participant_bp.route('/event/<int:event_id>/participants/export')
@login_required
@organizer_required
def export_participants(event_id):
    """
    Exporte tous les participants d'un événement en CSV avec toutes les données visibles.
    """
    event = Event.query.get_or_404(event_id)
    
    # Récupérer tous les participants avec leurs users et rôles
    participants = Participant.query.filter_by(event_id=event.id)\
        .options(joinedload(Participant.user), joinedload(Participant.role)).all()
    
    # Créer le CSV en mémoire
    output = io.StringIO()
    writer = csv.writer(output)
    
    # En-têtes
    headers = [
        'Nom', 'Prénom', 'Email', 'Age', 'Genre',
        'Type', 'Groupe', 'Statut Inscription',
        'Téléphone', 'Discord', 'Facebook',
        'Rôle Assigné',
        'Statut PAF', 'Type PAF', 'Montant Versé', 'Moyen Paiement', 'Montant Dû',
        'Commentaire Général', 'Info Paiement'
    ]
    writer.writerow(headers)
    
    # Données
    for p in participants:
        # Calculer montant dû basé sur le type PAF
        paf_config = json.loads(event.paf_config or '[]')
        due_amount = 0.0
        if p.paf_type:
            for config in paf_config:
                if config.get('name') == p.paf_type:
                    due_amount = float(config.get('amount', 0))
                    break
        
        row = [
            p.user.nom or '',
            p.user.prenom or '',
            p.user.email or '',
            p.user.age or '',
            p.user.genre or '',
            p.type or '',
            p.group or '',
            p.registration_status or '',
            # Contacts (seulement si partagés)
            p.participant_phone if p.share_phone else '',
            p.participant_discord if p.share_discord else '',
            p.participant_facebook if p.share_facebook else '',
            # Rôle
            p.role.name if p.role else '',
            # PAF
            p.paf_status or '',
            p.paf_type or '',
            p.payment_amount or 0.0,
            p.payment_method or '',
            due_amount,
            # Commentaires
            p.global_comment or '',
            p.info_payement or ''
        ]
        writer.writerow(row)
    
    # Préparer la réponse
    output.seek(0)
    from flask import make_response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=participants_{event.name.replace(" ", "_")}_{datetime.datetime.now().strftime("%Y%m%d")}.csv'
    
    return response


@participant_bp.route('/event/<int:event_id>/participant/<int:participant_id>/update_contact', methods=['POST'])
@login_required
def update_contact(event_id, participant_id):
    """
    Met à jour un champ de contact d'un participant pour un événement spécifique.
    
    Permet aux utilisateurs de modifier leurs coordonnées (Facebook, Discord, Téléphone)
    pour un événement particulier.
    """
    participant = Participant.query.get_or_404(participant_id)
    
    # Vérifier que l'utilisateur est propriétaire de cette participation
    if participant.user_id != current_user.id:
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('event.detail', event_id=event_id))
    
    # Récupérer le champ à modifier et la nouvelle valeur
    field = request.form.get('field')
    value = request.form.get('value', '').strip()
    
    # Mise à jour selon le champ
    if field == 'facebook':
        participant.participant_facebook = value if value else None
    elif field == 'discord':
        participant.participant_discord = value if value else None
    elif field == 'phone':
        participant.participant_phone = value if value else None
    else:
        flash('Champ invalide', 'danger')
        return redirect(url_for('event.detail', event_id=event_id))
    
    db.session.commit()
    flash('Coordonnées mises à jour', 'success')
    return redirect(url_for('event.detail', event_id=event_id))


@participant_bp.route('/event/<int:event_id>/participants/bulk_update', methods=['POST'])
@login_required
@organizer_required
def bulk_update(event_id):
    """
    Mise à jour groupée des participants.
    """
    event = Event.query.get_or_404(event_id)
        
    p_ids = request.form.getlist('participant_ids')
    
    # Optimisation N+1: Récupérer tous les participants en une seule requête
    participants = Participant.query.filter(
        Participant.id.in_(p_ids),
        Participant.event_id == event.id
    ).all()
    participants_map = {str(p.id): p for p in participants}
    
    for p_id in p_ids:
        # Utiliser le dictionnaire au lieu de faire une requête SQL à chaque itération
        p = participants_map.get(str(p_id))
        
        if p:
            # Mise à jour des champs
            p.type = request.form.get(f'type_{p_id}', p.type)
            p.group = request.form.get(f'group_{p_id}', p.group)
            p.paf_status = request.form.get(f'paf_{p_id}', p.paf_status)
            
            # Mise à jour paiement
            pay_amt = request.form.get(f'pay_amount_{p_id}', '')
            p.payment_amount = float(pay_amt) if pay_amt else 0.0
            p.payment_method = request.form.get(f'pay_method_{p_id}', p.payment_method)
            p.comment = request.form.get(f'comment_{p_id}', p.comment)
            
            # Log bulk update for this participant
            log = ActivityLog(
                user_id=current_user.id,
                action_type=ActivityLogType.PARTICIPANT_UPDATE.value,
                event_id=event.id,
                details=json.dumps({
                    'participant_id': p.id,
                    'update_type': 'bulk_update',
                    'new_type': p.type,
                    'new_group': p.group
                })
            )
            db.session.add(log)
            
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
    
    # Mise à jour des informations de contact de l'utilisateur
    p.user.discord = request.form.get('discord')
    p.user.phone = request.form.get('phone')
    p.user.facebook = request.form.get('facebook')
    
    # Log individual update
    log = ActivityLog(
        user_id=current_user.id,
        action_type=ActivityLogType.PARTICIPANT_UPDATE.value,
        event_id=event.id,
        details=json.dumps({
            'participant_id': p.id,
            'update_type': 'single_update',
            'new_type': p.type,
            'new_group': p.group,
            'paf_status': p.paf_status
        })
    )
    db.session.add(log)
    
    db.session.commit()
    flash('Participant mis à jour.', 'success')
    return redirect(url_for('participant.manage', event_id=event_id))


@participant_bp.route('/event/<int:event_id>/participant/<int:p_id>/update_paf', methods=['POST'])
@login_required
@organizer_required
def update_paf(event_id, p_id):
    """
    Met à jour le type de PAF d'un participant.
    """
    event = Event.query.get_or_404(event_id)
    p = Participant.query.get_or_404(p_id)
    
    if p.event_id != event_id:
        flash('Participant invalide.', 'danger')
        return redirect(url_for('event.detail', event_id=event_id) + '#list-paf')
        
    p.paf_type = request.form.get('paf_type')
    
    log = ActivityLog(
        user_id=current_user.id,
        action_type=ActivityLogType.PARTICIPANT_UPDATE.value,
        event_id=event.id,
        details=json.dumps({
            'participant_id': p.id,
            'update_type': 'paf_type_update',
            'new_paf_type': p.paf_type
        })
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Type de PAF mis à jour pour {p.user.email}.', 'success')
    return redirect(url_for('event.detail', event_id=event_id) + '#list-paf')


@participant_bp.route('/event/<int:event_id>/participant/<int:p_id>/update_paf_inline', methods=['POST'])
@login_required
@organizer_required
def update_paf_inline(event_id, p_id):
    """
    Met à jour les informations de PAF d'un participant via AJAX.
    """
    data = request.json
    p = Participant.query.get_or_404(p_id)
    event = Event.query.get_or_404(event_id)
    
    if p.event_id != event_id:
        return jsonify({'success': False, 'error': 'Participant invalide'}), 400
        
    if 'payment_amount' in data:
        try:
            p.payment_amount = float(data['payment_amount'])
        except (ValueError, TypeError):
            pass
    if 'payment_method' in data:
        p.payment_method = data['payment_method']
    if 'paf_type' in data:
        p.paf_type = data['paf_type']
    if 'info_payement' in data:
        p.info_payement = data['info_payement']
    if 'global_comment' in data:
        p.global_comment = data['global_comment']
        
    # Recalculer le statut PAF si nécessaire
    # Si le statut est 'dispensé(e)' ou 'erreur', on le garde sauf si le montant change vers un montant positif
    recalc_status = True
    if p.paf_status in ['dispensé(e)', 'erreur'] and ('payment_amount' not in data or float(data.get('payment_amount', 0)) == 0):
        recalc_status = False
        
    if recalc_status:
        paf_config = json.loads(event.paf_config or '[]')
        paf_map = {item['name']: float(item['amount']) for item in paf_config}
        due = paf_map.get(p.paf_type, 0.0) if p.paf_type else 0.0
        
        if p.payment_amount >= due and due > 0:
            p.paf_status = 'versée'
        elif p.payment_amount > 0:
            p.paf_status = 'partielle'
        else:
            p.paf_status = 'non versée'
            
    db.session.commit()
    
    # Recalculer due pour le retour AJAX
    paf_config = json.loads(event.paf_config or '[]')
    paf_map = {item['name']: float(item['amount']) for item in paf_config}
    due = paf_map.get(p.paf_type, 0.0) if p.paf_type else 0.0
    remaining = due - p.payment_amount
    
    return jsonify({
        'success': True,
        'paf_status': p.paf_status,
        'paf_status_cap': p.paf_status.capitalize(),
        'payment_amount': p.payment_amount,
        'payment_method': p.payment_method,
        'paf_type': p.paf_type,
        'due': due,
        'remaining': remaining,
        'info_payement_empty': not bool(p.info_payement),
        'info_payement': p.info_payement,
        'global_comment_empty': not bool(p.global_comment),
        'global_comment': p.global_comment
    })


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
    
    # Optimisation N+1: charger user avec joinedload car on accède à participant.user.email
    participant = Participant.query.options(joinedload(Participant.user)).get(p_id)
    if not participant or participant.event_id != event_id:
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
        details=json.dumps({
            'participant': participant.user.email,
            'name': f"{participant.user.prenom or ''} {participant.user.nom or ''}",
            'new_status': participant.registration_status
        })
    )
    db.session.add(log)
    
    db.session.commit()
    return redirect(url_for('participant.manage', event_id=event_id))




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
    if not me or not me.is_organizer:
        return jsonify({'error': 'Unauthorized'}), 403
        
    participant = Participant.query.get_or_404(participant_id)
    role = Role.query.get_or_404(role_id)
    
    # Update both sides
    participant.role_id = role.id
    role.assigned_participant_id = participant.id
    
    # Log assignment
    log = ActivityLog(
        user_id=current_user.id,
        action_type=ActivityLogType.PARTICIPANT_UPDATE.value,
        event_id=event.id,
        details=json.dumps({
            'action': 'role_assign',
            'role_name': role.name,
            'participant_id': participant.id
        })
    )
    db.session.add(log)
    
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
    if not me or not me.is_organizer:
        return jsonify({'error': 'Unauthorized'}), 403

    if role_id:
        role = Role.query.get(role_id)
        if role and role.assigned_participant_id:
            p = Participant.query.get(role.assigned_participant_id)
            if p:
                p.role_id = None
            role.assigned_participant_id = None
            
            # Log unassignment
            log = ActivityLog(
                user_id=current_user.id,
                action_type=ActivityLogType.PARTICIPANT_UPDATE.value,
                event_id=event.id,
                details=json.dumps({
                    'action': 'role_unassign',
                    'role_name': role.name,
                    'assigned_participant_id': p.id if p else None
                })
            )
            db.session.add(log)
            
            db.session.commit()
            return jsonify({'success': True})
            
    return jsonify({'error': 'Invalid request'}), 400


@participant_bp.route('/event/<int:event_id>/export/csv', methods=['POST'])
@login_required
@organizer_required
def export_csv(event_id):
    """
    Export des participants au format CSV.
    """
    event = Event.query.get_or_404(event_id)
    participants = Participant.query.filter_by(event_id=event.id).options(joinedload(Participant.user)).all()
    
    # Création du CSV en mémoire
    si = io.StringIO()
    writer = csv.writer(si, delimiter=';', quoting=csv.QUOTE_ALL)
    
    # En-têtes CSV
    headers = [
        'Email', 'Nom', 'Prénom', 'Age', 'Genre', 
        'Type', 'Groupe', 'Statut Inscription', 
        'PAF Statut', 'Montant (€)', 'Méthode Paiement', 
        'Rôle Assigné', 'Commentaire'
    ]
    writer.writerow(headers)
    
    for p in participants:
        row = [
            p.user.email,
            p.user.nom or '',
            p.user.prenom or '',
            p.user.age or '',
            p.user.genre or '',
            p.type or '',
            p.group or '',
            p.registration_status or '',
            p.paf_status or '',
            p.payment_amount or 0,
            p.payment_method or '',
            p.role.name if p.role else '',
            p.comment or ''
        ]
        writer.writerow(row)
        
    output = si.getvalue()
    si.close()
    
    # Ajouter BOM pour Excel (utf-8-sig)
    output = '\ufeff' + output
    
    # Nom du fichier
    filename = f"{event.name.replace(' ', '_')}_participants.csv"
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


@participant_bp.route('/event/<int:event_id>/export/google', methods=['POST'])
@login_required
@organizer_required
def export_google(event_id):
    """
    Export des participants vers Google Sheets.
    """
    # 1. Vérifier si l'utilisateur a un token Google
    token = session.get('google_token')
    if not token:
        flash('Veuillez d\'abord connecter votre compte Google pour utiliser cette fonctionnalité.', 'warning')
        return redirect(url_for('auth.login_google', _external=True))
        
    try:
        # 2. Préparer les données
        event = Event.query.get_or_404(event_id)
        participants = Participant.query.filter_by(event_id=event.id).options(joinedload(Participant.user)).all()
        
        headers = [
            'Email', 'Nom', 'Prénom', 'Age', 'Genre', 
            'Type', 'Groupe', 'Statut Inscription', 
            'PAF Statut', 'Montant (€)', 'Méthode Paiement', 
            'Rôle Assigné', 'Commentaire'
        ]
        
        rows = [headers]
        for p in participants:
            rows.append([
                p.user.email,
                p.user.nom or '',
                p.user.prenom or '',
                str(p.user.age or ''),
                p.user.genre or '',
                p.type or '',
                p.group or '',
                p.registration_status or '',
                p.paf_status or '',
                str(p.payment_amount or 0),
                p.payment_method or '',
                p.role.name if p.role else '',
                p.comment or ''
            ])
            
        # 3. Construire les credentials
        creds = Credentials(
            token['access_token'],
            refresh_token=token.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ.get('GOOGLE_CLIENT_ID'),
            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
            scopes=token.get('scope')
        )
        
        service = build('sheets', 'v4', credentials=creds)
        
        # 4. Créer la feuille
        spreadsheet_body = {
            'properties': {
                'title': f"{event.name} - Participants ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})"
            }
        }
        
        spreadsheet = service.spreadsheets().create(body=spreadsheet_body, fields='spreadsheetId,spreadsheetUrl').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')
        spreadsheet_url = spreadsheet.get('spreadsheetUrl')
        
        # 5. Écrire les données
        body = {
            'values': rows
        }
        
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range="A1",
            valueInputOption="RAW", body=body
        ).execute()
        
        # 6. Formatting (Optionnel mais sympa)
        # Met la première ligne en gras
        requests = [{
            'repeatCell': {
                'range': {'sheetId': 0, 'startRowIndex': 0, 'endRowIndex': 1},
                'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
                'fields': 'userEnteredFormat.textFormat.bold'
            }
        }]
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()

        flash(f'Export réussi ! Votre feuille est prête : <a href="{spreadsheet_url}" target="_blank">Ouvrir Google Sheets</a>', 'success')
        
    except Exception as e:
        flash(f"Erreur lors de l'export Google : {str(e)}", 'danger')
        # En cas d'expiration de token, on pourrait rediriger vers auth
        if '401' in str(e):
             return redirect(url_for('auth.login_google'))
             
    return redirect(url_for('participant.manage', event_id=event_id))
