import sqlite3
import unicodedata
import os
import sys

# Forcer le flush du stdout pour voir les messages immédiatement
def print_flush(msg):
    print(msg)
    sys.stdout.flush()

def remove_accents(input_str):
    if not input_str:
        return input_str
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def clean_emails(db_path, dry_run=True):
    print_flush(f"Vérification de la base : {db_path}")
    if not os.path.exists(db_path):
        print_flush(f"Erreur : Le fichier de base de données '{db_path}' n'existe pas.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print_flush("Lecture des utilisateurs...")
        cursor.execute("SELECT id, email FROM user")
        users = cursor.fetchall()
        print_flush(f"Nombre d'utilisateurs trouvés : {len(users)}")

        changes_count = 0
        print_flush(f"--- {'SIMULATION' if dry_run else 'EXÉCUTION'} : Nettoyage des emails ---")
        
        for user_id, email in users:
            if not email:
                continue
                
            cleaned_email = remove_accents(email).lower()
            
            if cleaned_email != email:
                print_flush(f"ID {user_id}: '{email}' -> '{cleaned_email}'")
                if not dry_run:
                    try:
                        cursor.execute("UPDATE user SET email = ? WHERE id = ?", (cleaned_email, user_id))
                        changes_count += 1
                    except sqlite3.IntegrityError:
                        print_flush(f"  [!] Conflit : '{cleaned_email}' existe déjà. Saut ID {user_id}.")
                else:
                    changes_count += 1

        if not dry_run:
            conn.commit()
            print_flush(f"\nSuccès. {changes_count} email(s) mis à jour.")
        else:
            print_flush(f"\nSimulation finie. {changes_count} changement(s).")

        conn.close()

    except Exception as e:
        print_flush(f"Erreur : {e}")

if __name__ == "__main__":
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'gnmanager.db')
    is_dry_run = "--run" not in sys.argv
    clean_emails(DB_PATH, dry_run=is_dry_run)
