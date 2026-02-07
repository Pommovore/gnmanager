"""
Routes pour la gestion du menu GForms (Google Forms integration).

Ce module gère :
- L'affichage des soumissions de formulaires Google Forms
- La gestion des catégories et couleurs
- Les associations champs → catégories
- Les APIs JSON pour les données dynamiques
"""

import json
import logging
import csv
from io import StringIO
from flask import Blueprint, render_template, request, jsonify, current_app, Response
from flask_login import login_required, current_user
from datetime import datetime

from models import db, Event, GFormsCategory, GFormsFieldMapping, GFormsSubmission, User, Participant
from decorators import organizer_required

# Création du Blueprint
gforms_bp = Blueprint('gforms', __name__)
logger = logging.getLogger(__name__)


@gforms_bp.route('/event/<int:event_id>/gforms')
@login_required
@organizer_required
def gforms_menu(event_id):
    """
    Page principale du menu GForms.
    Affiche les 3 onglets : formulaires, catégories, settings.
    """
    event = Event.query.get_or_404(event_id)
    
    # Vérifier si le webhook secret est configuré
    if not event.webhook_secret:
        # Menu grisé/désactivé sera géré dans le template
        pass
    
    # Initialiser la catégorie par défaut si elle n'existe pas (insensible à la casse)
    default_category = GFormsCategory.query.filter(
        GFormsCategory.event_id == event_id,
        db.func.lower(GFormsCategory.name) == 'généralités'
    ).first()
    
    if not default_category:
        default_category = GFormsCategory(
            event_id=event_id,
            name='Généralités',
            color='neutral',
            position=0
        )
        db.session.add(default_category)
        db.session.commit()
        logger.info(f"Created default 'Généralités' category for event {event_id}")

    # Vérifier et créer les mappings par défaut pour timestamp et type_ajout
    default_fields = ['timestamp', 'type_ajout']
    mappings_changed = False
    
    for field_name in default_fields:
        mapping = GFormsFieldMapping.query.filter_by(
            event_id=event_id,
            field_name=field_name
        ).first()
        
        if not mapping:
            mapping = GFormsFieldMapping(
                event_id=event_id,
                field_name=field_name,
                category_id=default_category.id
            )
            db.session.add(mapping)
            mappings_changed = True
            
    if mappings_changed:
        db.session.commit()
        logger.info(f"Created default field mappings for event {event_id}")
    
    return render_template(
        'gforms/main.html',
        event=event,
        user=current_user
    )


@gforms_bp.route('/event/<int:event_id>/gforms/submissions')
@login_required
@organizer_required
def get_submissions(event_id):
    """
    API: Retourne la liste des soumissions avec pagination.
    """
    event = Event.query.get_or_404(event_id)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Récupérer les soumissions
    submissions_query = GFormsSubmission.query.filter_by(event_id=event_id).order_by(GFormsSubmission.timestamp.desc())
    submissions_paginated = submissions_query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Récupérer les mappings de champs pour connaître tous les champs disponibles
    field_mappings = GFormsFieldMapping.query.filter_by(event_id=event_id).all()
    field_mapping_dict = {fm.field_name: fm for fm in field_mappings}
    
    # Construire la réponse JSON
    submissions_data = []
    for sub in submissions_paginated.items:
        raw_data = json.loads(sub.raw_data) if sub.raw_data else {}
        
        submissions_data.append({
            'id': sub.id,
            'email': sub.email,
            'timestamp': sub.timestamp.strftime('%Y/%m/%d %H:%M'),
            'type_ajout': sub.type_ajout,
            'raw_data': raw_data
        })
    
    return jsonify({
        'submissions': submissions_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': submissions_paginated.total,
            'pages': submissions_paginated.pages,
            'has_prev': submissions_paginated.has_prev,
            'has_next': submissions_paginated.has_next
        }
    })


@gforms_bp.route('/event/<int:event_id>/gforms/categories', methods=['GET'])
@login_required
@organizer_required
def get_categories(event_id):
    """
    API: Retourne la liste des catégories.
    """
    event = Event.query.get_or_404(event_id)
    
    categories = GFormsCategory.query.filter_by(event_id=event_id).order_by(GFormsCategory.position).all()
    
    categories_data = [{
        'id': cat.id,
        'name': cat.name,
        'color': cat.color,
        'position': cat.position
    } for cat in categories]
    
    return jsonify({'categories': categories_data})


@gforms_bp.route('/event/<int:event_id>/gforms/categories', methods=['POST'])
@login_required
@organizer_required
def save_categories(event_id):
    """
    API: Crée ou met à jour des catégories.
    Payload: { "categories": [{"id": 1, "name": "...", "color": "...", "position": 0}, ...] }
    """
    event = Event.query.get_or_404(event_id)
    
    data = request.get_json()
    categories_input = data.get('categories', [])
    
    # Couleurs valides
    valid_colors = ['neutral', 'blue', 'green', 'red', 'yellow', 'purple', 'orange', 'pink', 'teal']
    
    try:
        # Récupérer les catégories existantes
        existing_categories = {cat.id: cat for cat in GFormsCategory.query.filter_by(event_id=event_id).all()}
        existing_ids = set(existing_categories.keys())
        updated_ids = set()
        
        for idx, cat_data in enumerate(categories_input):
            cat_id = cat_data.get('id')
            name = cat_data.get('name', '').strip()
            if not name:
                continue  # Skip empty names
            
            # Normalisation : Majuscule au début si possible
            if len(name) > 1:
                name = name[0].upper() + name[1:]
            elif len(name) == 1:
                name = name.upper()
            
            color = cat_data.get('color', 'neutral')
            
            if color not in valid_colors:
                color = 'neutral'
            
            if cat_id and cat_id in existing_categories:
                # Update existing
                category = existing_categories[cat_id]
                category.name = name
                category.color = color
                category.position = idx
                updated_ids.add(cat_id)
            else:
                # Create new
                category = GFormsCategory(
                    event_id=event_id,
                    name=name,
                    color=color,
                    position=idx
                )
                db.session.add(category)
        
        # Delete categories that were removed
        removed_ids = existing_ids - updated_ids
        for cat_id in removed_ids:
            # Ne pas supprimer la catégorie "Généralités" par défaut
            if existing_categories[cat_id].name != 'Généralités':
                db.session.delete(existing_categories[cat_id])
        
        db.session.commit()
        logger.info(f"Saved {len(categories_input)} categories for event {event_id}")
        
        return jsonify({'success': True, 'message': 'Catégories enregistrées'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving categories for event {event_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@gforms_bp.route('/event/<int:event_id>/gforms/fields', methods=['GET'])
@login_required
@organizer_required
def get_fields(event_id):
    """
    API: Retourne la liste des champs détectés avec leurs mappings.
    """
    event = Event.query.get_or_404(event_id)
    
    # Récupérer tous les champs détectés à partir des soumissions
    submissions = GFormsSubmission.query.filter_by(event_id=event_id).all()
    detected_fields = set()
    
    # Champs système toujours présents
    detected_fields.add('timestamp')
    detected_fields.add('type_ajout')
    
    for sub in submissions:
        raw_data = json.loads(sub.raw_data) if sub.raw_data else {}
        detected_fields.update(raw_data.keys())
    
    # Récupérer les mappings existants
    mappings = GFormsFieldMapping.query.filter_by(event_id=event_id).all()
    mapping_dict = {m.field_name: m for m in mappings}
    
    # Récupérer les catégories pour inclure les infos de couleur
    categories = GFormsCategory.query.filter_by(event_id=event_id).all()
    category_dict = {cat.id: cat for cat in categories}
    
    # Construire la réponse
    fields_data = []
    for field_name in sorted(detected_fields):
        mapping = mapping_dict.get(field_name)
        category = category_dict.get(mapping.category_id) if mapping else None
        
        fields_data.append({
            'field_name': field_name,
            'field_alias': mapping.field_alias if mapping else None,
            'category_id': mapping.category_id if mapping else None,
            'category': {
                'id': category.id,
                'name': category.name,
                'color': category.color
            } if category else None
        })
    
    return jsonify({'fields': fields_data})


@gforms_bp.route('/event/<int:event_id>/gforms/field-mappings', methods=['POST'])
@login_required
@organizer_required
def save_field_mappings(event_id):
    """
    API: Sauvegarde les associations champ → catégorie.
    Payload: { "mappings": [{"field_name": "...", "category_id": 1, "field_alias": "..."}, ...] }
    """
    event = Event.query.get_or_404(event_id)
    
    data = request.get_json()
    mappings_input = data.get('mappings', [])
    
    try:
        for mapping_data in mappings_input:
            field_name = mapping_data.get('field_name')
            category_id = mapping_data.get('category_id')
            field_alias = mapping_data.get('field_alias')
            
            if not field_name:
                continue
            
            # Vérifier si le mapping existe already
            mapping = GFormsFieldMapping.query.filter_by(
                event_id=event_id,
                field_name=field_name
            ).first()
            
            if mapping:
                # Update
                mapping.category_id = category_id
                mapping.field_alias = field_alias
            else:
                # Create
                mapping = GFormsFieldMapping(
                    event_id=event_id,
                    field_name=field_name,
                    category_id=category_id,
                    field_alias=field_alias
                )
                db.session.add(mapping)
        
        db.session.commit()
        logger.info(f"Saved field mappings for event {event_id}")
        
        return jsonify({'success': True, 'message': 'Mappings enregistrés'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving field mappings for event {event_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@gforms_bp.route('/event/<int:event_id>/gforms/export')
@login_required
@organizer_required
def export_gforms_data(event_id):
    """
    Export CSV fusionnant les données de Participant et les données GForms.
    """
    event = Event.query.get_or_404(event_id)
    
    # 1. Récupérer toutes les soumissions GForms
    submissions = GFormsSubmission.query.filter_by(event_id=event_id).all()
    sub_map = {}
    for s in submissions:
        try:
            sub_map[s.email.lower()] = json.loads(s.raw_data) if s.raw_data else {}
        except:
            sub_map[s.email.lower()] = {}
            
    # 2. Récupérer tous les participants de l'événement
    participants = Participant.query.filter_by(event_id=event_id).all()
    
    # 3. Collecter tous les champs dynamiques de GForms
    dynamic_fields = set()
    for data in sub_map.values():
        dynamic_fields.update(data.keys())
    
    # Trier les champs pour la consistance
    sorted_dynamic_fields = sorted(list(dynamic_fields))
    
    # 4. Définir les en-têtes CSV
    headers = [
        "Email", "Nom", "Prénom", "Type Participant", "Statut Inscription", 
        "Statut PAF", "Montant Payé", "Méthode Paiement", "Téléphone", 
        "Discord", "Facebook", "Commentaire Global"
    ] + sorted_dynamic_fields
    
    # 5. Construire les lignes
    rows = []
    processed_emails = set()
    
    for p in participants:
        email_key = p.user.email.lower()
        processed_emails.add(email_key)
        form_data = sub_map.get(email_key, {})
        
        row = [
            p.user.email,
            p.user.nom,
            p.user.prenom,
            p.type,
            p.registration_status,
            p.paf_status,
            p.payment_amount,
            p.payment_method,
            p.participant_phone or p.user.phone or "",
            p.participant_discord or p.user.discord or "",
            p.participant_facebook or p.user.facebook or "",
            p.global_comment or ""
        ]
        
        # Ajouter les données du formulaire
        for field in sorted_dynamic_fields:
            row.append(form_data.get(field, ""))
            
        rows.append(row)
        
    # Ajouter les soumissions qui n'ont pas (encore) de participant lié
    # (par exemple si un formulaire arrive mais l'utilisateur n'est pas encore créé/lié)
    for email, form_data in sub_map.items():
        if email not in processed_emails:
            row = [email, "(No Participant)", "", "", "", "", "", "", "", "", "", ""]
            for field in sorted_dynamic_fields:
                row.append(form_data.get(field, ""))
            rows.append(row)
            
    # 6. Générer le CSV (format Excel compatible avec BOM UTF-8 et point-virgule)
    output = StringIO()
    output.write('\ufeff') # BOM for Excel
    writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    writer.writerow(headers)
    writer.writerows(rows)
    
    filename = f"export_gforms_{event.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
