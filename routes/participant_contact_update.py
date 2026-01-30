
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

