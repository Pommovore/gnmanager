#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime
import os

os.environ.setdefault('FLASK_ENV', 'development')


# Imports déplacés à l'intérieur des fonctions pour éviter les imports circulaires


class DateTimeEncoder(json.JSONEncoder):
    """Client JSONEncoder pour gérer les objets datetime."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def serialize_model(instance):
    """Convertit une instance SQLAlchemy en dictionnaire."""
    data = {}
    for column in instance.__table__.columns:
        value = getattr(instance, column.name)
        data[column.name] = value
    return data

def export_data(args):
    """Exporte les données vers un fichier JSON."""
    file_path = args.file
    print(f"Exportation des données vers {file_path}...")
    
    data = {
        'timestamp': datetime.now().isoformat(),
        'users': [],
        'events': [],
        'participants': []
    }
    
    from app import create_app
    from models import User, Event, Participant
    
    app = create_app()
    with app.app_context():
        # Users
        users = User.query.all()
        data['users'] = [serialize_model(u) for u in users]
        print(f"  - {len(users)} utilisateurs exportés")
        
        # Events
        events = Event.query.all()
        data['events'] = [serialize_model(e) for e in events]
        print(f"  - {len(events)} événements exportés")

        # Participants
        participants = Participant.query.all()
        data['participants'] = [serialize_model(p) for p in participants]
        print(f"  - {len(participants)} participations exportées")
        
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, cls=DateTimeEncoder, indent=2, ensure_ascii=False)
        
    print("Export terminé avec succès.")

def import_data(args):
    """Importe les données depuis un fichier JSON."""
    file_path = args.file
    clean = args.clean
    
    print(f"Importation des données depuis {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Erreur: Le fichier {file_path} n'existe pas.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Erreur: Le fichier {file_path} n'est pas un JSON valide.")
        sys.exit(1)
        
    from app import create_app
    from extensions import db
    from models import User, Event, Participant
    
    app = create_app()
    with app.app_context():
        if clean:
            print("Nettoyage de la base de données...")
            try:
                # SQLite specific cascade truncate simulation
                # Ou simplement drop_all / create_all si on veut être radical
                # Ici on supprime content
                db.session.query(Participant).delete()
                db.session.query(Event).delete()
                db.session.query(User).delete()
                db.session.commit()
                print("Données existantes supprimées.")
            except Exception as e:
                db.session.rollback()
                print(f"Erreur lors du nettoyage: {e}")
                sys.exit(1)

        # Import Users
        print("Importation des utilisateurs...")
        for user_data in data.get('users', []):
            if not User.query.get(user_data['id']): # Avoid dupes if not clean
                # Convertir id si nécessaire ou laisser faire?
                # On assume que l'ID est dans data
                user = User()
                for key, value in user_data.items():
                    setattr(user, key, value)
                db.session.add(user)
        db.session.commit()
        print(f"  - Utilisateurs importés.")

        # Import Events
        print("Importation des événements...")
        for event_data in data.get('events', []):
            if not Event.query.get(event_data['id']):
                event = Event()
                for key, value in event_data.items():
                    # Handle datetime conversion
                    if key in ['date_start', 'date_end'] and value:
                        value = datetime.fromisoformat(value)
                    setattr(event, key, value)
                db.session.add(event)
        db.session.commit()
        print("  - Événements importés.")

        # Import Participants
        print("Importation des participants...")
        for part_data in data.get('participants', []):
            # Composite key check might be needed if strictly adding
            # But let's rely on cleaning or non-collision for now
            # check existence
            exists = False
            if 'id' in part_data:
                 if Participant.query.get(part_data['id']):
                     exists = True
            
            if not exists:
                part = Participant()
                for key, value in part_data.items():
                    setattr(part, key, value)
                db.session.add(part)
        db.session.commit()
        print("  - Participations importées.")
        
    print("Import terminé avec succès.")

def main():
    parser = argparse.ArgumentParser(description="Outil de gestion de base de données import/export JSON.")
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    subparsers.required = True
    
    # Export Parser
    export_parser = subparsers.add_parser('export', help='Exporter la base de données vers JSON')
    export_parser.add_argument('-f', '--file', required=True, help='Chemin du fichier JSON de sortie')
    export_parser.set_defaults(func=export_data)
    
    # Import Parser
    import_parser = subparsers.add_parser('import', help='Importer la base de données depuis JSON')
    import_parser.add_argument('-f', '--file', required=True, help='Chemin du fichier JSON source')
    import_parser.add_argument('--clean', action='store_true', help='Vider la base avant l\'importation')
    import_parser.set_defaults(func=import_data)
    
    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
