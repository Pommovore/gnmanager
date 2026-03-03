import sys
import os
from sqlalchemy import inspect, text

# Ajouter le répertoire parent à sys.path pour permettre l'importation de l'application
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env (requis pour SQLALCHEMY_DATABASE_URI)
load_dotenv()

from app import create_app
from models import db

def update_database():
    print("Mise à jour de la base de données (v0.12 - Traits de caractère)...")
    app = create_app()
    with app.app_context():
        # Afficher les infos de connexion pour débogage
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        print(f"📦 Database URI: {db_uri}")
        
        if db_uri and db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            if not os.path.isabs(db_path):
                db_path = os.path.join(app.root_path, db_path)
            print(f"📂 Chemin absolu SQLite: {os.path.abspath(db_path)}")
            if os.path.exists(db_path):
                print(f"✅ Le fichier de base de données existe (taille: {os.path.getsize(db_path)} octets)")
            else:
                print(f"❌ Le fichier de base de données n'existe pas à cet emplacement !")

        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📊 Tables trouvées: {', '.join(tables)}")
            
            if 'role' not in tables:
                print("❌ ERREUR: La table 'role' n'existe pas dans cette base de données.")
                return

            columns = [c['name'] for c in inspector.get_columns('role')]
            print(f"📋 Colonnes actuelles dans 'role': {', '.join(columns)}")
            
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
