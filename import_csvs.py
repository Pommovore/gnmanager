import csv
import os
from app import create_app
from models import db, User, Event, Role, Participant
from werkzeug.security import generate_password_hash
from datetime import datetime

DATA_DIR = 'tests/data'
app = create_app()

def import_users():
    path = os.path.join(DATA_DIR, 'users.csv')
    if not os.path.exists(path):
        print("users.csv not found")
        return

    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if User.query.filter_by(email=row['email']).first():
                continue
            
            user = User(
                email=row['email'],
                nom=row['nom'],
                prenom=row['prenom'],
                age=int(row['age']) if row['age'] else None,
                avatar_url=row['avatar_url'],
                role=row['role'],
                is_banned=row['is_banned'] == 'True'
            )
            user.password_hash = generate_password_hash(row['password'])
            db.session.add(user)
            count += 1
        db.session.commit()
        print(f"Imported {count} users")

def import_events():
    path = os.path.join(DATA_DIR, 'events.csv')
    if not os.path.exists(path):
        return

    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            # Simple check by name
            if Event.query.filter_by(name=row['name']).first():
                continue
                
            event = Event(
                name=row['name'],
                date_start=datetime.strptime(row['date_start'], '%Y-%m-%d %H:%M:%S'),
                date_end=datetime.strptime(row['date_end'], '%Y-%m-%d %H:%M:%S'),
                location=row['location'],
                background_image=row['background_image'],
                visibility=row['visibility'],
                organizer_structure=row['organizer_structure'],
                statut=row['statut']
            )
            db.session.add(event)
            count += 1
        db.session.commit()
        print(f"Imported {count} events")

def import_roles():
    path = os.path.join(DATA_DIR, 'roles.csv')
    if not os.path.exists(path):
        return

    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            # We assume event_ids match 1-to-1 with creation order if DB was empty, 
            # but ideally we should query. For 'Test' data we assume clean slate or matching IDs.
            # To be safer, let's just insert.
            
            # Check if exists (by name and event_id)
            if Role.query.filter_by(name=row['name'], event_id=int(row['event_id'])).first():
                continue

            role = Role(
                event_id=int(row['event_id']),
                name=row['name'],
                genre=row['genre'],
                comment=row['comment']
            )
            db.session.add(role)
            count += 1
        db.session.commit()
        print(f"Imported {count} roles")

def import_participants():
    path = os.path.join(DATA_DIR, 'participants.csv')
    if not os.path.exists(path):
        return

    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            # Check existence
            if Participant.query.filter_by(user_id=int(row['user_id']), event_id=int(row['event_id'])).first():
                continue
                
            p = Participant(
                event_id=int(row['event_id']),
                user_id=int(row['user_id']),
                type=row['type'],
                group=row['group'],
                payment_amount=float(row['payment_amount']) if row['payment_amount'] else 0.0,
                registration_status='Validé'
            )
            if row['role_id']:
                p.role_id = int(row['role_id'])
                
            db.session.add(p)
            count += 1
        db.session.commit()
        print(f"Imported {count} participants")

if __name__ == "__main__":
    with app.app_context():
        import_users()
        import_events()
        import_roles()
        import_participants()
        print("Data import finished.")
