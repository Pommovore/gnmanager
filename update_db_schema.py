
import sqlite3
import os

def update_schema():
    db_path = 'instance/gnmanager.db'
    if not os.path.exists(db_path):
        # Fallback if instance folder isn't used or db is in root
        if os.path.exists('gnmanager.db'):
            db_path = 'gnmanager.db'
        else:
            print(f"Base de données non trouvée (cherché dans instance/gnmanager.db et ./gnmanager.db)")
            return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    columns = [
        ('max_pjs', 'INTEGER DEFAULT 50'),
        ('max_pnjs', 'INTEGER DEFAULT 10'),
        ('max_organizers', 'INTEGER DEFAULT 5')
    ]
    
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE event ADD COLUMN {col_name} {col_type}")
            print(f"Colonne {col_name} ajoutée avec succès.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Colonne {col_name} existe déjà.")
            else:
                print(f"Erreur lors de l'ajout de {col_name}: {e}")
                
    conn.commit()
    conn.close()
    print("Mise à jour du schéma terminée.")

if __name__ == '__main__':
    update_schema()
