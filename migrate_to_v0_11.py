import sqlite3
import os

def migrate():
    db_path = 'instance/gnmanager.db'
    if not os.path.exists(db_path):
        print(f"❌ Base de données non trouvée à {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    def add_column_if_missing(table, column, definition):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if column not in columns:
            print(f"➕ Ajout de la colonne '{column}' à la table '{table}'...")
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                print(f"✅ Colonne '{column}' ajoutée.")
            except Exception as e:
                print(f"❌ Erreur lors de l'ajout de '{column}': {e}")
        else:
            print(f"ℹ️  La colonne '{column}' existe déjà dans '{table}'.")

    print("🚀 Début de la migration...")

    # --- TABLES ---
    # On laisse SQLAlchemy créer les tables manquantes via un mini app context
    # ou on le fait en SQL brut pour être sûr.
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = [row[0] for row in cursor.fetchall()]

    if 'form_response' not in existing_tables:
        print("🧱 Création de la table 'form_response'...")
        cursor.execute("""
            CREATE TABLE form_response (
                id INTEGER PRIMARY KEY,
                event_id INTEGER,
                form_id VARCHAR(100),
                response_id VARCHAR(100) UNIQUE NOT NULL,
                respondent_email VARCHAR(120),
                answers TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY(event_id) REFERENCES event(id)
            )
        """)

    if 'event_notification' not in existing_tables:
        print("🧱 Création de la table 'event_notification'...")
        cursor.execute("""
            CREATE TABLE event_notification (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                action_type VARCHAR(50) NOT NULL,
                description TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                FOREIGN KEY(event_id) REFERENCES event(id),
                FOREIGN KEY(user_id) REFERENCES user(id)
            )
        """)

    if 'gforms_category' not in existing_tables:
        print("🧱 Création de la table 'gforms_category'...")
        cursor.execute("""
            CREATE TABLE gforms_category (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                color VARCHAR(20) DEFAULT 'neutral',
                position INTEGER DEFAULT 0,
                created_at DATETIME,
                FOREIGN KEY(event_id) REFERENCES event(id)
            )
        """)

    if 'gforms_field_mapping' not in existing_tables:
        print("🧱 Création de la table 'gforms_field_mapping'...")
        cursor.execute("""
            CREATE TABLE gforms_field_mapping (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                field_name VARCHAR(200) NOT NULL,
                field_alias VARCHAR(100),
                category_id INTEGER,
                FOREIGN KEY(event_id) REFERENCES event(id),
                FOREIGN KEY(category_id) REFERENCES gforms_category(id),
                UNIQUE(event_id, field_name)
            )
        """)

    if 'gforms_submission' not in existing_tables:
        print("🧱 Création de la table 'gforms_submission'...")
        cursor.execute("""
            CREATE TABLE gforms_submission (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                user_id INTEGER,
                email VARCHAR(120) NOT NULL,
                timestamp DATETIME NOT NULL,
                type_ajout VARCHAR(20),
                form_response_id INTEGER,
                raw_data TEXT,
                FOREIGN KEY(event_id) REFERENCES event(id),
                FOREIGN KEY(user_id) REFERENCES user(id),
                FOREIGN KEY(form_response_id) REFERENCES form_response(id)
            )
        """)

    # --- COLONNES ---
    # Table User
    add_column_if_missing('user', 'is_profile_photo_public', 'BOOLEAN DEFAULT 1')
    add_column_if_missing('user', 'profile_photo_url', 'VARCHAR(200)')
    
    # Table Participant
    add_column_if_missing('participant', 'paf_type', 'VARCHAR(50)')
    add_column_if_missing('participant', 'info_payement', 'TEXT')
    add_column_if_missing('participant', 'participant_phone', 'VARCHAR(20)')
    add_column_if_missing('participant', 'participant_discord', 'VARCHAR(100)')
    add_column_if_missing('participant', 'participant_facebook', 'VARCHAR(200)')
    add_column_if_missing('participant', 'share_phone', 'BOOLEAN DEFAULT 1')
    add_column_if_missing('participant', 'share_discord', 'BOOLEAN DEFAULT 1')
    add_column_if_missing('participant', 'share_facebook', 'BOOLEAN DEFAULT 1')
    add_column_if_missing('participant', 'is_photo_locked', 'BOOLEAN DEFAULT 0')
    
    # Table Event
    add_column_if_missing('event', 'background_image_light', 'VARCHAR(200)')
    add_column_if_missing('event', 'background_image_dark', 'VARCHAR(200)')
    add_column_if_missing('event', 'visibility', "VARCHAR(20) DEFAULT 'public'")
    add_column_if_missing('event', 'access_code', 'VARCHAR(50)')
    add_column_if_missing('event', 'google_form_active', 'BOOLEAN DEFAULT 0')
    add_column_if_missing('event', 'display_organizers', 'BOOLEAN DEFAULT 1')
    add_column_if_missing('event', 'webhook_secret', 'VARCHAR(32) UNIQUE')
    add_column_if_missing('event', 'discord_webhook_url', 'VARCHAR(255)')
    add_column_if_missing('event', 'is_casting_validated', 'BOOLEAN DEFAULT 0')
    add_column_if_missing('event', 'paf_config', "TEXT DEFAULT '[]'")
    add_column_if_missing('event', 'payment_methods', "TEXT DEFAULT '[\"Helloasso\"]'")
    add_column_if_missing('event', 'max_pjs', 'INTEGER DEFAULT 50')
    add_column_if_missing('event', 'max_pnjs', 'INTEGER DEFAULT 10')
    add_column_if_missing('event', 'max_organizers', 'INTEGER DEFAULT 5')

    conn.commit()
    conn.close()
    print("🏁 Migration terminée.")

if __name__ == "__main__":
    migrate()
