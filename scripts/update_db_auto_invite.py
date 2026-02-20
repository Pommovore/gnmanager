import sys
import os
from sqlalchemy import inspect, text

# Add the parent directory to sys.path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db

def update_database():
    print("Mise à jour de la base de données...")
    app = create_app()
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            columns = [c['name'] for c in inspector.get_columns('event')]
            
            with db.engine.connect() as connection:
                if 'auto_invite_email' in columns:
                    print("- La colonne 'auto_invite_email' existe déjà.")
                else:
                    print("- Ajout de la colonne 'auto_invite_email'...")
                    # Le type BOOLEAN avec une valeur par défaut de 0 est géré
                    # sur SQLite comme un entier. Pour une portabilité vers Postgresql,
                    # il faut utiliser FALSE, mais pour la simplicité, on ajoute via ALTER.
                    connection.execute(text("ALTER TABLE event ADD COLUMN auto_invite_email BOOLEAN DEFAULT 0"))
                    connection.commit()
                    print("  -> Colonne ajoutée avec succès.")
                    
                print("\nMise à jour terminée !")
                
        except Exception as e:
            print(f"\nERREUR lors de la mise à jour : {e}")

if __name__ == "__main__":
    update_database()
