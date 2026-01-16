#!/usr/bin/env python3
"""
Script pour mettre à jour automatiquement les url_for() dans les templates HTML.

Ce script remplace les anciens endpoints 'main.*' par les nouveaux endpoints
des blueprints modulaires (event.*, participant.*).
"""

import os
import re

# Mapping des anciens endpoints vers les nouveaux
ENDPOINT_MAPPING = {
    # Event routes
    "main.create_event": "event.create_event",
    "main.event_detail": "event.detail",
    "main.update_event_general": "event.update_general",
    "main.update_event_status": "event.update_status",
    "main.update_event_groups": "event.update_groups",
    "main.join_event": "event.join",
    
    # Participant routes
    "main.manage_participants": "participant.manage",
    "main.bulk_update_participants": "participant.bulk_update",
    "main.update_participant": "participant.update",
    "main.change_participant_status": "participant.change_status",
    "main.casting_interface": "participant.casting",
    "main.api_assign_role": "participant.api_assign",
    "main.api_unassign_role": "participant.api_unassign",
}

def update_file(filepath):
    """Met à jour un fichier HTML en remplaçant les url_for()."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    # Pour chaque mapping, remplacer dans le fichier
    for old_endpoint, new_endpoint in ENDPOINT_MAPPING.items():
        # Pattern pour url_for avec guillemets simples
        pattern1 = f"url_for\\('{old_endpoint}'"
        replacement1 = f"url_for('{new_endpoint}'"
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
            changes_made.append(f"  {old_endpoint} → {new_endpoint}")
        
        # Pattern pour url_for avec guillemets doubles
        pattern2 = f'url_for\\("{old_endpoint}"'
        replacement2 = f'url_for("{new_endpoint}"'
        if re.search(pattern2, content):
            content = re.sub(pattern2, replacement2, content)
            changes_made.append(f"  {old_endpoint} → {new_endpoint}")
    
    # Écrire le fichier seulement s'il y a eu des changements
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return changes_made
    return []

def main():
    """Parcourt tous les templates et met à jour les url_for()."""
    templates_dir = os.path.join(os.getcwd(), 'templates')
    
    if not os.path.exists(templates_dir):
        print(f"❌ Répertoire templates non trouvé : {templates_dir}")
        return
    
    print("🔍 Recherche des templates à mettre à jour...\n")
    
    total_files_updated = 0
    total_changes = 0
    
    for filename in os.listdir(templates_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(templates_dir, filename)
            changes = update_file(filepath)
            
            if changes:
                total_files_updated += 1
                total_changes += len(changes)
                print(f"✅ {filename}")
                for change in changes:
                    print(change)
                print()
    
    print(f"\n📊 Résumé:")
    print(f"   Fichiers modifiés : {total_files_updated}")
    print(f"   Endpoints mis à jour : {total_changes}")
    print(f"\n✨ Migration des URL terminée !")

if __name__ == '__main__':
    main()
