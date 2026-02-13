import io
import os
from odf.opendocument import OpenDocumentText
from odf.style import Style, TextProperties, ParagraphProperties, TableColumnProperties, TableCellProperties, GraphicProperties
from odf.text import P
from odf.table import Table, TableColumn, TableRow, TableCell
from odf.draw import Frame, Image
from flask import current_app
from models import Event, Role, Participant
from sqlalchemy.orm import joinedload
from PIL import Image as PILImage

def generate_trombinoscope_odt(event_id, include_type=True, include_player_name=True, group_by_group=True):
    """
    Génère un fichier ODT pour le trombinoscope de l'événement.
    
    Format: 2 colonnes.
    Col 1: Rôle, Type, Nom du joueur.
    Col 2: Photo (ratio préservé).
    
    Args:
        event_id: ID de l'événement
        include_type (bool): Inclure le type de rôle
        include_player_name (bool): Inclure le nom du joueur
        group_by_group (bool): Grouper par groupe de rôle
        
    Returns:
        BytesIO: Le fichier ODT en mémoire
    """
    event = Event.query.get_or_404(event_id)
    
    # Récupérer les rôles triés
    query = Role.query.filter_by(event_id=event_id)\
        .options(joinedload(Role.assigned_participant).joinedload(Participant.user))
        
    if group_by_group:
        # Tri par groupe (nulls last/first check? SQL alchemy default usually ok, empty string vs None)
        # On assume que group est une string.
        query = query.order_by(Role.group, Role.name)
    else:
        query = query.order_by(Role.name)
        
    roles = query.all()

    doc = OpenDocumentText()
    
    # --- STYLES ---
    
    # Style standard pour le texte
    s_standard = Style(name="Standard", family="paragraph")
    s_standard.addElement(TextProperties(fontfamily="Arial", fontsize="10pt"))
    doc.styles.addElement(s_standard)
    
    # Titre
    s_title = Style(name="Title", family="paragraph")
    s_title.addElement(TextProperties(fontfamily="Arial", fontsize="18pt", fontweight="bold"))
    s_title.addElement(ParagraphProperties(textalign="center", marginbottom="0.5cm"))
    doc.styles.addElement(s_title)
    
    # Colonne 1 : Info (Large)
    s_col1 = Style(name="co1", family="table-column")
    s_col1.addElement(TableColumnProperties(columnwidth="10cm"))
    doc.automaticstyles.addElement(s_col1)

    # Colonne 2 : Photo (Restante)
    s_col2 = Style(name="co2", family="table-column")
    s_col2.addElement(TableColumnProperties(columnwidth="5cm"))
    doc.automaticstyles.addElement(s_col2)

    # Cellules
    s_cell = Style(name="Ce1", family="table-cell")
    s_cell.addElement(TableCellProperties(padding="0.2cm", border="0.05pt solid #000000", verticalalign="middle"))
    doc.automaticstyles.addElement(s_cell)
    
    # Cellule de Titre de Groupe (fusionnée)
    s_cell_group = Style(name="CeGroup", family="table-cell")
    s_cell_group.addElement(TableCellProperties(padding="0.3cm", border="0.05pt solid #000000", backgroundcolor="#e9ecef", verticalalign="middle"))
    doc.automaticstyles.addElement(s_cell_group)

    # Styles Texte
    s_role_name = Style(name="RoleName", family="paragraph")
    s_role_name.addElement(TextProperties(fontweight="bold", fontsize="12pt"))
    doc.automaticstyles.addElement(s_role_name)
    
    s_info = Style(name="Info", family="paragraph")
    s_info.addElement(TextProperties(fontsize="9pt", color="#555555"))
    doc.automaticstyles.addElement(s_info)

    s_player_name = Style(name="PlayerName", family="paragraph")
    s_player_name.addElement(TextProperties(fontsize="11pt", fontweight="bold", color="#0d6efd"))
    doc.automaticstyles.addElement(s_player_name)
    
    s_group_title = Style(name="GroupTitle", family="paragraph")
    s_group_title.addElement(TextProperties(fontsize="14pt", fontweight="bold", color="#333333"))
    doc.automaticstyles.addElement(s_group_title)

    # Styles Statut
    def create_status_style(name, color):
        s = Style(name=name, family="paragraph")
        s.addElement(TextProperties(color=color, fontweight="bold"))
        doc.automaticstyles.addElement(s)
        return s

    create_status_style("StatusGreen", "#198754")
    create_status_style("StatusOrange", "#fd7e14")
    create_status_style("StatusRed", "#dc3545")
    create_status_style("StatusGrey", "#6c757d")

    # --- CONTENU ---

    doc.text.addElement(P(stylename="Title", text=f"Trombinoscope - {event.name}"))
    
    # Tableau - 2 Colonnes
    table = Table(name="Trombinoscope")
    table.addElement(TableColumn(stylename="co1")) # Infos
    table.addElement(TableColumn(stylename="co2")) # Photo
    
    doc.text.addElement(table)
    
    current_group = None
    
    for role in roles:
        # Gestion du changement de groupe
        if group_by_group:
            role_group = role.group or "Hors Groupe"
            if role_group != current_group:
                current_group = role_group
                
                tr_group = TableRow()
                table.addElement(tr_group)
                
                tc_group = TableCell(stylename="CeGroup", numbercolumnsspanned=2)
                tc_group.addElement(P(stylename="GroupTitle", text=current_group))
                tr_group.addElement(tc_group)
                # ODF requires to add covered cells for spanned columns? 
                # odfpy handles covered cells automatically if separate? No, usually just omit.
                # But creating a valid ODF table with spans can be tricky. 
                # Let's try simple span. If issues, we can just put it in col 1 and empty col 2.
        
        tr = TableRow()
        table.addElement(tr)
        
        # --- COLONNE 1 : Infos Complètes ---
        tc_info = TableCell(stylename="Ce1")
        
        # 1. Nom du Rôle
        tc_info.addElement(P(stylename="RoleName", text=role.name))
        
        # 2. Type & Groupe
        infos_parts = []
        if include_type:
             infos_parts.append(f"Type: {role.type or 'Indéfini'}")
        
        # Si on ne groupe pas par groupe, on affiche le groupe dans la ligne
        # Si on groupe, c'est redondant, mais parfois utile. 
        # Le user a dit "roles sont divisés par sections". On peut retirer le groupe de la ligne.
        if not group_by_group and role.group:
            infos_parts.append(f"Groupe: {role.group}")
            
        if infos_parts:
            tc_info.addElement(P(stylename="Info", text=" | ".join(infos_parts)))
        
        if role.comment:
            tc_info.addElement(P(stylename="Info", text=f"Note: {role.comment}"))
            
        tc_info.addElement(P(stylename="Standard", text="")) # Spacer
        
        # 3. Infos Joueur (si assigné et demandé)
        p = role.assigned_participant
        if p:
            if include_player_name:
                tc_info.addElement(P(stylename="PlayerName", text=f"Joueur : {p.user.nom} {p.user.prenom}"))
        else:
            tc_info.addElement(P(stylename="StatusGrey", text="Rôle non attribué"))
            
        tr.addElement(tc_info)
        
        # --- COLONNE 2 : Photo ---
        tc_photo = TableCell(stylename="Ce1")
        
        if p:
            image_path = None
            status_style = "StatusRed"
            status_text = "Aucune photo"
            
            # Détermination du chemin de l'image
            if p.custom_image:
                rel_path = p.custom_image.lstrip('/')
                abs_path = os.path.join(current_app.root_path, rel_path)
                if os.path.exists(abs_path):
                    image_path = abs_path
                    status_style = "StatusGreen"
                    status_text = ""
                
            elif p.user.is_profile_photo_public and p.user.profile_photo_url:
                rel_path = p.user.profile_photo_url.lstrip('/')
                abs_path = os.path.join(current_app.root_path, rel_path)
                if os.path.exists(abs_path):
                    image_path = abs_path
                    status_style = "StatusOrange"
                    status_text = "Photo de profil"
            
            # Traitement de l'image
            if image_path:
                try:
                    # Utiliser PIL pour obtenir les dimensions et conserver le ratio
                    with PILImage.open(image_path) as img:
                        orig_w, orig_h = img.size
                        ratio = orig_w / orig_h
                        
                        # Max largeur fixée à 4.5cm pour rentrer dans la colonne de 5cm
                        max_w_cm = 4.5
                        
                        # Calculer la hauteur proportionnelle
                        new_h_cm = max_w_cm / ratio
                        
                        # Création du cadre
                        photo_frame = Frame(width=f"{max_w_cm}cm", height=f"{new_h_cm}cm", anchortype="as-char")
                        image_ref = doc.addPicture(image_path)
                        photo_frame.addElement(Image(href=image_ref))
                        
                        p_img = P(stylename="Standard")
                        p_img.addElement(photo_frame)
                        tc_photo.addElement(p_img)
                        
                except Exception as e:
                    tc_photo.addElement(P(stylename="StatusRed", text="Erreur image"))
            else:
                 tc_photo.addElement(P(stylename="StatusRed", text="Pas d'image"))

            if status_text:
                tc_photo.addElement(P(stylename=status_style, text=status_text))
                
        else:
            tc_photo.addElement(P(stylename="StatusGrey", text="--"))
            
        tr.addElement(tc_photo)

    # Sauvegarde
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    
    return output
