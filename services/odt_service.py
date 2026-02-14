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

def generate_trombinoscope_odt(event_id, include_type=True, include_player_name=True, group_by_group=True, layout_cols=4):
    """
    Génère un fichier ODT pour le trombinoscope de l'événement.
    
    Args:
        event_id: ID de l'événement
        include_type (bool): Inclure le type de rôle
        include_player_name (bool): Inclure le nom du joueur
        group_by_group (bool): Grouper par groupe de rôle
        layout_cols (int): Nombre de colonnes (1, 2 ou 4)
        
    Returns:
        BytesIO: Le fichier ODT en mémoire
    """
    event = Event.query.get_or_404(event_id)
    
    # Récupérer les rôles triés
    query = Role.query.filter_by(event_id=event_id)\
        .options(joinedload(Role.assigned_participant).joinedload(Participant.user))
        
    if group_by_group:
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
    
    # --- Styles de Table ---
    # Largeur totale approx 17cm (A4 minus marges)
    total_width_cm = 17.0
    col_width = total_width_cm / layout_cols
    
    # Colonne générique
    s_col = Style(name="ColDef", family="table-column")
    s_col.addElement(TableColumnProperties(columnwidth=f"{col_width}cm"))
    doc.automaticstyles.addElement(s_col)

    # Styles spécifiques pour layout = 1 (Liste)
    # Col 1 : Info (Large) - ~11cm
    s_col1_list = Style(name="co1csv", family="table-column")
    s_col1_list.addElement(TableColumnProperties(columnwidth="11cm"))
    doc.automaticstyles.addElement(s_col1_list)

    # Col 2 : Photo (Restante) - ~6cm
    s_col2_list = Style(name="co2csv", family="table-column")
    s_col2_list.addElement(TableColumnProperties(columnwidth="6cm"))
    doc.automaticstyles.addElement(s_col2_list)

    # Cellule Standard
    s_cell = Style(name="Ce1", family="table-cell")
    s_cell.addElement(TableCellProperties(padding="0.2cm", border="0.05pt solid #000000", verticalalign="middle"))
    doc.automaticstyles.addElement(s_cell)
    
    # Cellule Centrée (pour la grille)
    s_cell_center = Style(name="CeCenter", family="table-cell")
    s_cell_center.addElement(TableCellProperties(padding="0.2cm", border="0.05pt solid #000000", verticalalign="middle"))
    doc.automaticstyles.addElement(s_cell_center)
    
    # Paragraphe Centré (pour la grille)
    s_p_center = Style(name="PCenter", family="paragraph")
    s_p_center.addElement(ParagraphProperties(textalign="center"))
    doc.automaticstyles.addElement(s_p_center)
    
    # Cellule de Titre de Groupe (fusionnée)
    s_cell_group = Style(name="CeGroup", family="table-cell")
    s_cell_group.addElement(TableCellProperties(padding="0.3cm", border="0.05pt solid #000000", backgroundcolor="#e9ecef", verticalalign="middle"))
    doc.automaticstyles.addElement(s_cell_group)

    # Styles Texte
    s_role_name = Style(name="RoleName", family="paragraph")
    s_role_name.addElement(TextProperties(fontweight="bold", fontsize="12pt"))
    doc.automaticstyles.addElement(s_role_name)
    
    s_role_name_center = Style(name="RoleNameCenter", family="paragraph")
    s_role_name_center.addElement(TextProperties(fontweight="bold", fontsize="11pt"))
    s_role_name_center.addElement(ParagraphProperties(textalign="center"))
    doc.automaticstyles.addElement(s_role_name_center)
    
    s_info = Style(name="Info", family="paragraph")
    s_info.addElement(TextProperties(fontsize="9pt", color="#555555"))
    doc.automaticstyles.addElement(s_info)

    s_info_center = Style(name="InfoCenter", family="paragraph")
    s_info_center.addElement(TextProperties(fontsize="8pt", color="#555555"))
    s_info_center.addElement(ParagraphProperties(textalign="center"))
    doc.automaticstyles.addElement(s_info_center)

    s_player_name = Style(name="PlayerName", family="paragraph")
    s_player_name.addElement(TextProperties(fontsize="11pt", fontweight="bold", color="#0d6efd"))
    doc.automaticstyles.addElement(s_player_name)
    
    s_player_name_center = Style(name="PlayerNameCenter", family="paragraph")
    s_player_name_center.addElement(TextProperties(fontsize="10pt", fontweight="bold", color="#0d6efd"))
    s_player_name_center.addElement(ParagraphProperties(textalign="center"))
    doc.automaticstyles.addElement(s_player_name_center)
    
    s_group_title = Style(name="GroupTitle", family="paragraph")
    s_group_title.addElement(TextProperties(fontsize="14pt", fontweight="bold", color="#333333"))
    doc.automaticstyles.addElement(s_group_title)

    # Styles Statut
    def create_status_style(name, color, align="left"):
        s = Style(name=name, family="paragraph")
        s.addElement(TextProperties(color=color, fontweight="bold"))
        if align == "center":
            s.addElement(ParagraphProperties(textalign="center"))
        doc.automaticstyles.addElement(s)
        return s

    create_status_style("StatusGreen", "#198754")
    create_status_style("StatusOrange", "#fd7e14")
    create_status_style("StatusRed", "#dc3545")
    create_status_style("StatusGrey", "#6c757d")
    
    create_status_style("StatusGreenCenter", "#198754", align="center")
    create_status_style("StatusOrangeCenter", "#fd7e14", align="center")
    create_status_style("StatusRedCenter", "#dc3545", align="center")
    create_status_style("StatusGreyCenter", "#6c757d", align="center")

    # --- CONTENU ---

    doc.text.addElement(P(stylename="Title", text=f"Trombinoscope - {event.name}"))
    
    table = Table(name="Trombinoscope")
    
    # Définition des colonnes
    if layout_cols == 1:
        table.addElement(TableColumn(stylename="co1csv")) # Infos
        table.addElement(TableColumn(stylename="co2csv")) # Photo
    else:
        # Grille
        table.addElement(TableColumn(stylename="ColDef", numbercolumnsrepeated=layout_cols))
    
    doc.text.addElement(table)
    
    current_group = None
    row_buffer = [] # Pour stocker les cellules de la ligne en cours (mode grille)
    
    def flush_row(buffer, table, cols_needed):
        """Ajoute une ligne complète à la table depuis le buffer."""
        if not buffer:
            return
            
        tr = TableRow()
        for cell in buffer:
            tr.addElement(cell)
            
        # Combler les cellules vides si la ligne n'est pas pleine
        # Note: ODF mandate d'avoir le bon nombre de cellules pour respecter la structure
        missing = cols_needed - len(buffer)
        for _ in range(missing):
            tr.addElement(TableCell(stylename="Ce1"))
            
        table.addElement(tr)
        buffer.clear()

    # --- HELPER: Contenu de cellule ---
    def create_role_content_list(role, participant):
        """Crée le contenu pour le format LISTE (1 par ligne). Renvoie (cell_info, cell_photo)"""
        # Cellule Info
        tc_info = TableCell(stylename="Ce1")
        tc_info.addElement(P(stylename="RoleName", text=role.name))
        
        infos_parts = []
        if include_type: infos_parts.append(f"Type: {role.type or 'Indéfini'}")
        if not group_by_group and role.group: infos_parts.append(f"Groupe: {role.group}")
        if infos_parts: tc_info.addElement(P(stylename="Info", text=" | ".join(infos_parts)))
        if role.comment: tc_info.addElement(P(stylename="Info", text=f"Note: {role.comment}"))
        tc_info.addElement(P(stylename="Standard", text=""))
        
        if participant and include_player_name:
            tc_info.addElement(P(stylename="PlayerName", text=f"Joueur : {participant.user.nom} {participant.user.prenom}"))
        elif not participant:
            tc_info.addElement(P(stylename="StatusGrey", text="Rôle non attribué"))
            
        # Cellule Photo
        tc_photo = TableCell(stylename="Ce1")
        add_photo_to_cell(tc_photo, participant, layout="list")
        
        return tc_info, tc_photo

    def create_role_content_grid(role, participant):
        """Crée le contenu pour le format GRILLE (>1 par ligne). Renvoie une seule cell."""
        tc = TableCell(stylename="CeCenter")
        
        # 1. Photo au dessus
        add_photo_to_cell(tc, participant, layout="grid")
        
        # 2. Infos en dessous
        tc.addElement(P(stylename="RoleNameCenter", text=role.name))
        
        infos_parts = []
        if include_type: infos_parts.append(role.type or '-')
        # On n'affiche pas le groupe dans la case en mode grid si groupé, sinon ça charge trop
        if infos_parts: tc.addElement(P(stylename="InfoCenter", text=" | ".join(infos_parts)))
        
        if participant and include_player_name:
             tc.addElement(P(stylename="PlayerNameCenter", text=f"{participant.user.prenom} {participant.user.nom}"))
        elif not participant:
             tc.addElement(P(stylename="StatusGreyCenter", text="(Libre)"))
             
        return tc

    def add_photo_to_cell(cell, participant, layout="list"):
        """Ajoute l'image dans la cellule donnée."""
        if not participant:
            if layout == "grid":
                 # Spacer pour garder la hauteur en grid
                 cell.addElement(P(stylename="Standard", text=""))
            else:
                 cell.addElement(P(stylename="StatusGrey", text="--"))
            return

        image_path = None
        status_style = "StatusRed" if layout == "list" else "StatusRedCenter"
        status_text = "Aucune photo"
        
        if participant.custom_image:
            rel_path = participant.custom_image.lstrip('/')
            abs_path = os.path.join(current_app.root_path, rel_path)
            if os.path.exists(abs_path):
                image_path = abs_path
                status_style = "StatusGreen" if layout == "list" else "StatusGreenCenter"
                status_text = ""
        elif participant.user.is_profile_photo_public and participant.user.profile_photo_url:
            rel_path = participant.user.profile_photo_url.lstrip('/')
            abs_path = os.path.join(current_app.root_path, rel_path)
            if os.path.exists(abs_path):
                image_path = abs_path
                status_style = "StatusOrange" if layout == "list" else "StatusOrangeCenter"
                status_text = "Photo de profil"
        
        if image_path:
            try:
                with PILImage.open(image_path) as img:
                    orig_w, orig_h = img.size
                    ratio = orig_w / orig_h
                    
                    # Dimensions max
                    if layout == "list":
                        max_w_cm = 5.5 # Col is 6cm
                    else:
                        # Grid: depend sur nb cols. 
                        # 4 cols -> ~4cm width total cell -> img 3.5cm
                        # 2 cols -> ~8cm width total cell -> img 6cm
                        max_w_cm = 3.5 if layout_cols >= 4 else 6.0
                    
                    new_h_cm = max_w_cm / ratio
                    
                    # Frame
                    photo_frame = Frame(width=f"{max_w_cm}cm", height=f"{new_h_cm}cm", anchortype="as-char")
                    image_ref = doc.addPicture(image_path)
                    photo_frame.addElement(Image(href=image_ref))
                    
                    p_img = P(stylename="PCenter" if layout == "grid" else "Standard")
                    p_img.addElement(photo_frame)
                    cell.addElement(p_img)
            except Exception:
                cell.addElement(P(stylename=status_style, text="Erreur image"))
        else:
             cell.addElement(P(stylename=status_style, text="Pas d'image"))

        if status_text:
            cell.addElement(P(stylename=status_style, text=status_text))


    # --- BOUCLE PRINCIPALE ---
    
    for role in roles:
        # Gestion Groupe
        if group_by_group:
            role_group = role.group or "Hors Groupe"
            if role_group != current_group:
                # Changement de groupe : on flush la ligne en cours (si grille)
                if layout_cols > 1:
                    flush_row(row_buffer, table, layout_cols)
                
                current_group = role_group
                
                # Titre de Groupe
                tr_group = TableRow()
                table.addElement(tr_group)
                
                # Span sur toutes les colonnes
                # Layout 1 -> 2 colonnes (Info + Photo)
                # Layout X -> X colonnes
                span = 2 if layout_cols == 1 else layout_cols
                
                tc_group = TableCell(stylename="CeGroup", numbercolumnsspanned=span)
                tc_group.addElement(P(stylename="GroupTitle", text=current_group))
                tr_group.addElement(tc_group)
                
                # En ODF, les cellules couvertes par un span ne doivent pas être ajoutées physiquement
                # (Sauf si on veut être puriste XML, mais numbercolumnsspanned suffit souvent avec odfpy)
                pass

        # Création des cellules pour le rôle
        p = role.assigned_participant
        
        if layout_cols == 1:
            # Mode Liste Standard
            tr = TableRow()
            tc_info, tc_photo = create_role_content_list(role, p)
            tr.addElement(tc_info)
            tr.addElement(tc_photo)
            table.addElement(tr)
        else:
            # Mode Grille
            tc_cell = create_role_content_grid(role, p)
            row_buffer.append(tc_cell)
            
            if len(row_buffer) == layout_cols:
                flush_row(row_buffer, table, layout_cols)

    # Flush final (pour la grille)
    if layout_cols > 1 and row_buffer:
         flush_row(row_buffer, table, layout_cols)

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    
    return output
