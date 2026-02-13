import io
import os
import zipfile
import re
from PIL import Image, ImageDraw, ImageFont
from flask import current_app
from models import Event, Role, Participant
from sqlalchemy.orm import joinedload

import unicodedata

def sanitize_filename(name):
    """
    Remplace les caractères non alphanumériques par des underscores
    et supprime les accents.
    """
    if not name:
        return ""
    
    # Normaliser pour séparer les accents (NFD splitting)
    nfkd_form = unicodedata.normalize('NFKD', name)
    # Garder uniquement les caractères ASCII (supprime les accents)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    
    # Remplacer tout ce qui n'est pas a-z, A-Z, 0-9 par _
    return re.sub(r'[^a-zA-Z0-9]', '_', only_ascii)

def generate_placeholder_image(text, width=400, height=500, bg_color=(200, 200, 200), text_color=(50, 50, 50)):
    """
    Génère une image placeholder avec du texte centré.
    """
    img = Image.new('RGB', (width, height), color=bg_color)
    d = ImageDraw.Draw(img)
    
    # Essayer de charger une police par défaut, sinon utiliser celle par défaut de PIL
    try:
        # On essaie une police système si dispo, sinon défaut
        # Linux paths often have DejaVuSans
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, 24)
        else:
             font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
        
    # Calculer la position du texte (centré)
    # create_text is newer, textsize is deprecated. Using textbbox if available (Pillow 8+)
    try:
        left, top, right, bottom = d.textbbox((0, 0), text, font=font)
        text_w = right - left
        text_h = bottom - top
    except AttributeError:
        # Fallback for older Pillow
        text_w, text_h = d.textsize(text, font=font)

    x = (width - text_w) / 2
    y = (height - text_h) / 2
    
    d.text((x, y), text, fill=text_color, font=font)
    
    output = io.BytesIO()
    img.save(output, format='JPEG')
    output.seek(0)
    return output

def generate_trombinoscope_zip(event_id, include_placeholders=True, filename_pattern='role_group_player'):
    """
    Génère une archive ZIP contenant les images du trombinoscope.
    
    Args:
        event_id: ID de l'événement
        include_placeholders: Inclure les images générées si pas de photo
        filename_pattern: Modèle de nommage (role_group_player, group_role_player, etc.)
    """
    event = Event.query.get_or_404(event_id)
    
    roles = Role.query.filter_by(event_id=event_id)\
        .options(joinedload(Role.assigned_participant).joinedload(Participant.user))\
        .all()
        
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for role in roles:
            # 1. Prépare les composants du nom
            s_role = sanitize_filename(role.name)
            s_group = sanitize_filename(role.group or "Hors_Groupe")
            
            p = role.assigned_participant
            s_player = "Non_attribue"
            if p:
                s_player = sanitize_filename(f"{p.user.nom}_{p.user.prenom}")
            
            # 2. Construit le nom de base selon le pattern
            if filename_pattern == 'group_role_player':
                filename_base = f"{s_group}_{s_role}_{s_player}.jpg"
            elif filename_pattern == 'player_role_group':
                filename_base = f"{s_player}_{s_role}_{s_group}.jpg"
            elif filename_pattern == 'player_group_role':
                filename_base = f"{s_player}_{s_group}_{s_role}.jpg"
            else: # Default: role_group_player
                filename_base = f"{s_role}_{s_group}_{s_player}.jpg"

            # 3. Récupère l'image source
            image_source = None
            if p:
                # Custom Image
                if p.custom_image:
                    rel_path = p.custom_image.lstrip('/')
                    # Handle URL path vs filesystem path if needed, assuming relative from app root
                    # Often custom_image is stored as /static/... url path. 
                    # strip leading slash to join with root_path
                    abs_path = os.path.join(current_app.root_path, rel_path)
                    if os.path.exists(abs_path):
                        image_source = abs_path
                
                # Profile Image (fallback)
                if not image_source and p.user.is_profile_photo_public and p.user.profile_photo_url:
                    rel_path = p.user.profile_photo_url.lstrip('/')
                    abs_path = os.path.join(current_app.root_path, rel_path)
                    if os.path.exists(abs_path):
                        image_source = abs_path
                        
            # 4. Ajout au ZIP
            if image_source:
                # Ajouter l'image existante
                zip_file.write(image_source, arcname=filename_base)
            elif include_placeholders:
                # Générer placeholder si demandé
                if p:
                    img_data = generate_placeholder_image("Pas de photo", bg_color=(255, 200, 200), text_color=(200, 50, 50))
                else:
                    img_data = generate_placeholder_image("Non attribué", bg_color=(230, 230, 230), text_color=(100, 100, 100))
                
                zip_file.writestr(filename_base, img_data.getvalue())

    zip_buffer.seek(0)
    return zip_buffer
