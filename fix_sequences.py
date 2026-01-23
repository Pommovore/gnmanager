"""
Script de réparation des séquences PostgreSQL et SQLite.

Ce script est destiné à être exécuté SUR LE SERVEUR DE PRODUCTION.
Il synchronise les compteurs d'auto-incrément (séquences) avec les IDs maximums réels des tables.

Usage:
    python fix_sequences.py
    
Pré-requis:
    - Variables d'environnement configurées (DATABASE_URL, SECRET_KEY, etc.)
    - Environnement virtuel activé
"""
import sys

from app import create_app
from models import db, CastingProposal, CastingAssignment
from sqlalchemy import text

def fix_sequences():
    """
    Réinitialise les séquences (compteurs d'ID auto-itcrement) de la base de données.
    """
    app = create_app()
    with app.app_context():
        import os
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"DEBUG: Configuration SGBD: {db_uri}")
        
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            # Handle relative path
            if not os.path.isabs(db_path):
                db_path = os.path.abspath(os.path.join(app.root_path, '..', db_path))
            
            print(f"DEBUG: Chemin absolu déduit de la base de données : {db_path}")
            if os.path.exists(db_path):
                print(f"DEBUG: Le fichier existe (Taille: {os.path.getsize(db_path)} bytes)")
            else:
                print(f"ERREUR CRITIQUE: Le fichier de base de données est introuvable à cet emplacement !")
        
        print("Vérification et réparation des séquences...")
        
        # Liste des tables à vérifier
        tables = [
            'casting_proposal',
            'casting_assignment',
            'activity_log',
            'user',
            'event',
            'role',
            'participant'
        ]
        
        try:
            if 'postgresql' in db_uri:
                print(" -> Mode PostgreSQL détecté.")
                for table in tables:
                    try:
                        sql = text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id),0) + 1, false) FROM {table};")
                        db.session.execute(sql)
                        print(f"   -> Séquence pour '{table}' mise à jour.")
                    except Exception as e:
                        print(f"   -> Erreur ou saut pour '{table}': {e}")
                db.session.commit()
                
            else:
                # Mode SQLite
                print(" -> Mode SQLite détecté.")
                
                # Check existant sequence
                try:
                    current_seqs = db.session.execute(text("SELECT * FROM sqlite_sequence")).fetchall()
                    print(f"DEBUG: Contenu actuel de sqlite_sequence : {current_seqs}")
                except Exception as e:
                    print(f"DEBUG: Impossible de lire sqlite_sequence (peut-être vide ou inexistante): {e}")

                for table_name in tables:
                    try:
                        # 1. Récupérer l'ID max actuel de la table
                        result = db.session.execute(text(f"SELECT MAX(id) FROM {table_name}")).scalar()
                        max_id = result if result is not None else 0
                        
                        # 2. Mettre à jour (ou insérer) dans sqlite_sequence
                        # On vérifie d'abord si la ligne existe
                        exists = db.session.execute(text("SELECT 1 FROM sqlite_sequence WHERE name = :name"), {'name': table_name}).scalar()
                        
                        if exists:
                            db.session.execute(text("UPDATE sqlite_sequence SET seq = :seq WHERE name = :name"), 
                                             {'name': table_name, 'seq': max_id})
                            action = "mise à jour"
                        else:
                            db.session.execute(text("INSERT INTO sqlite_sequence (name, seq) VALUES (:name, :seq)"), 
                                             {'name': table_name, 'seq': max_id})
                            action = "créée"
                        
                        print(f"   -> Séquence '{table_name}' {action} à {max_id}")
                        
                    except Exception as e:
                        print(f"   -> Erreur pour '{table_name}': {e}")
                        
                db.session.commit()

            print("\nSuccès ! Les séquences ont été synchronisées.")
                
        except Exception as e:
            print(f"Une erreur globale est survenue : {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_sequences()
