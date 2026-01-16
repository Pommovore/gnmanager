#!/usr/bin/env python3
"""
Script pour mettre à jour les url_for() dans les templates HTML.

Remplace les anciens endpoints 'main.*' par les nouveaux blueprints modulaires.
"""

import os
import re

# Mapping des anciens vers nouveaux endpoints
ENDPOINT_MAP = {
    # Auth blueprint
    'main.index': 'auth.index',
    'main.login': 'auth.login',
    'main.register': 'auth.register',
    'main.validate_account': 'auth.validate_account',
    'main.forgot_password': 'auth.forgot_password',
    'main.reset_password': 'auth.reset_password',
    'main.logout': 'auth.logout',
    
    # Admin blueprint
    'main.dashboard': 'admin.dashboard',
    'main.update_profile': 'admin.update_profile',
    'main.admin_add_user': 'admin.admin_add_user',
    'main.admin_update_full_user': 'admin.admin_update_full_user',
    'main.admin_delete_user': 'admin.admin_delete_user',
    'main.admin_logs': 'admin.admin_logs',
    'main.mark_logs_viewed': 'admin.mark_logs_viewed',
    
    # Event blueprint (à créer plus tard, pour l'instant on laisse 'main')
    # 'main.create_event': 'event.create_event',
    # 'main.event_detail': 'event.detail',
    # etc.
}

def update_template(filepath):
    """Met à jour les url_for() dans un template."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    # Pour chaque mapping, remplacer dans le contenu
    for old_endpoint, new_endpoint in ENDPOINT_MAP.items():
        # Pattern pour matcher url_for('main.xxx')
        pattern = re.escape(f"url_for('{old_endpoint}'")
        replacement = f"url_for('{new_endpoint}'"
        
        # Compter les occurrences
        count = content.count(pattern.replace('\\', ''))
        if count > 0:
            content = content.replace(pattern.replace('\\', ''), replacement)
            changes_made += count
    
    # Sauvegarder si changements
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return changes_made
    
    return 0

def main():
    """Fonction principale."""
    templates_dir = 'templates'
    
    print("🔧 Mise à jour des url_for() dans les templates...")
    print("=" * 60)
    
    total_changes = 0
    files_modified = 0
    
    for filename in os.listdir(templates_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(templates_dir, filename)
            changes = update_template(filepath)
            
            if changes > 0:
                print(f"✓ {filename}: {changes} endpoint(s) mis à jour")
                total_changes += changes
                files_modified += 1
            else:
                print(f"- {filename}: aucun changement")
    
    print("=" * 60)
    print(f"✅ Terminé ! {total_changes} endpoint(s) mis à jour dans {files_modified} fichier(s)")

if __name__ == '__main__':
    main()
