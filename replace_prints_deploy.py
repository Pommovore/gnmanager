#!/usr/bin/env python3
"""
Script pour remplacer automatiquement tous les print() par logger dans deploy.py.

Ce script analyse chaque appel print() et le remplace par:
- logger.error() si le message contient "Erreur" ou "error"
- logger.warning() si le message contient "Attention" ou "warning"
- logger.info() pour tous les autres cas
"""

import re

def replace_prints_in_deploy():
    """Remplace tous les print() par des appels logger appropriés."""
    file_path = 'deploy.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern pour trouver les appels print()
    # Gère print("...") et print(f"...")
    pattern = r'print\((f?"[^"]*")\)'
    
    def determine_log_level(message):
        """Détermine le niveau de log en fonction du contenu du message."""
        msg_lower = message.lower()
        if 'erreur' in msg_lower or 'error' in msg_lower:
            return 'logger.error'
        elif 'attention' in msg_lower or 'warning' in msg_lower:
            return 'logger.warning'
        else:
            return 'logger.info'
    
    def replace_print(match):
        """Remplace un appel print() par le logger approprié."""
        message = match.group(1)
        log_level = determine_log_level(message)
        return f'{log_level}({message})'
    
    # Compter les occurrences avant
    before_count = len(re.findall(pattern, content))
    
    # Remplacer tous les print() par logger
    new_content = re.sub(pattern, replace_print, content)
    
    # Sauvegarder le fichier modifié
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    # Compter les occurrences après
    after_count = len(re.findall(pattern, new_content))
    
    print(f"✓ {before_count - after_count} appels print() remplacés par logger")
    print(f"✅ deploy.py mis à jour avec succès")

if __name__ == '__main__':
    replace_prints_in_deploy()
