import sys
import os
from sqlalchemy import inspect, text

# Ajouter le répertoire parent à sys.path pour permettre l'importation de l'application
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db

def update_database():
    print("Mise à jour de la base de données (v0.12 - Traits de caractère)...")
    app = create_app()
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            columns = [c['name'] for c in inspector.get_columns('role')]
            
            with db.engine.connect() as connection:
                # 1. Colonne character_traits_status
                if 'character_traits_status' in columns:
                    print("- La colonne 'character_traits_status' existe déjà.")
                else:
                    print("- Ajout de la colonne 'character_traits_status'...")
                    connection.execute(text("ALTER TABLE role ADD COLUMN character_traits_status VARCHAR(20) DEFAULT NULL"))
                    connection.commit()
                    print("  -> Colonne ajoutée avec succès.")

                # 2. Colonne character_traits_data
                if 'character_traits_data' in columns:
                    print("- La colonne 'character_traits_data' existe déjà.")
                else:
                    print("- Ajout de la colonne 'character_traits_data'...")
                    connection.execute(text("ALTER TABLE role ADD COLUMN character_traits_data TEXT DEFAULT NULL"))
                    connection.commit()
                    print("  -> Colonne ajoutée avec succès.")
                    
                print("\nMise à jour terminée !")
                
        except Exception as e:
            print(f"\nERREUR lors de la mise à jour : {e}")

if __name__ == "__main__":
    update_database()
