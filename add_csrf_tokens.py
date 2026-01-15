#!/usr/bin/env python3
"""
Script pour ajouter automatiquement les tokens CSRF à tous les templates HTML.

Ce script parcourt tous les fichiers .html dans le dossier templates/ et ajoute
la ligne `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>` 
après chaque balise `<form method="POST">` ou `<form method="post">`.
"""

import os
import re
from pathlib import Path

def add_csrf_to_template(file_path):
    """Ajoute un token CSRF à un template HTML si nécessaire."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier si csrf_token() est déjà présent
    if 'csrf_token()' in content:
        print(f"✓ {file_path.name} - Déjà protégé")
        return False
    
    # Pattern pour trouver les balises <form method="POST">
    # Chercher <form...method="POST"...> ou <form...method="post"...>
    pattern = r'(<form[^>]*method=["\'](?:POST|post)["\'][^>]*>)'
    
    # Vérifier si le fichier contient des formulaires POST
    if not re.search(pattern, content, re.IGNORECASE):
        print(f"- {file_path.name} - Pas de formulaire POST")
        return False
    
    # Ajouter le token CSRF après chaque balise <form method="POST">
    # On ajoute le token avec une indentation appropriée
    def add_token(match):
        form_tag = match.group(1)
        # Détecter l'indentation en comptant les espaces avant <form
        indent_match = re.search(r'(\s*)<form', content[max(0, match.start()-50):match.start()])
        indent = indent_match.group(1) if indent_match else '                    '
        
        # Ajouter 4 espaces supplémentaires pour le contenu du form
        token_indent = indent + '    '
        csrf_input = f'{token_indent}<input type="hidden" name="csrf_token" value="{{{{ csrf_token() }}}}"/>'
        
        return form_tag + '\n' + csrf_input
    
    new_content = re.sub(pattern, add_token, content, flags=re.IGNORECASE)
    
    # Sauvegarder le fichier modifié
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✓ {file_path.name} - Token CSRF ajouté")
    return True

def main():
    """Fonction principale."""
    templates_dir = Path(__file__).parent / 'templates'
    
    if not templates_dir.exists():
        print(f"❌ Dossier templates non trouvé: {templates_dir}")
        return
    
    print("🔒 Ajout des tokens CSRF aux templates...")
    print("-" * 50)
    
    modified_count = 0
    for html_file in templates_dir.glob('*.html'):
        if add_csrf_to_template(html_file):
            modified_count += 1
    
    print("-" * 50)
    print(f"✅ Terminé ! {modified_count} fichier(s) modifié(s)")

if __name__ == '__main__':
    main()
