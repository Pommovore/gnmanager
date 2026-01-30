"""
Export endpoint for participant data to CSV format.
"""
import csv
import io
from flask import make_response

@participant_bp.route('/event/<int:event_id>/participants/export')
@login_required
@organizer_required
def export_participants(event_id):
    """
    Exporte tous les participants d'un événement en CSV.
    
    Inclut toutes les données visibles par l'organisateur:
    - Informations personnelles (nom, prénom, email, age, genre)
    - Type et groupe
    - Statut d'inscription
    - Coordonnées de contact (si partagées)
    - Informations PAF
    - Commentaires
    """
    event = Event.query.get_or_404(event_id)
    
    # Récupérer tous les participants avec leurs users
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
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=participants_{event.name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return response
