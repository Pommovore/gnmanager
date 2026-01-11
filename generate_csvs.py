# GN Manager Data Generator
import csv
import os
import random
from datetime import datetime, timedelta

DATA_DIR = 'tests/data'

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_users(count=10, args=None):
    users = []
    # Admin (Createur) - Dynamic if args provided
    if args:
        users.append(['admin', args.admin_email, args.admin_password, args.admin_nom, args.admin_prenom, '30', '', 'createur', 'False'])
    else:
        users.append(['admin', 'admin@gnmanager.fr', 'admin1234', 'Admin', 'System', '30', '', 'createur', 'False'])
        
    # Organizers
    for i in range(2):
        users.append([
            f'orga{i}', 
            f'orga{i}@test.com', 
            'test1234', 
            f'Orga{i}', 
            'User', 
            '25', 
            '', 
            'user',
            'False'
        ])
    # Players
    for i in range(count):
        users.append([
            f'player{i}', 
            f'player{i}@test.com', 
            'test1234', 
            f'Player{i}', 
            'User', 
            str(20 + i), 
            '', 
            'user',
            'False'
        ])
    # Custom Users
    # Jacques: Createur/SysAdmin? Spec says "administrateur système devient celui qui déploie". 
    # Let's make Jacques SysAdmin as he's a named user, or Createur. Let's make him Createur for test.
    users.append(['jchodorowski', 'jchodorowski@gmail.com', 'jach1612', 'Chodorowski', 'Jacques', '40', '', 'createur', 'False'])
    # Gwenaëlle
    users.append(['gwengm', 'gwengm@gmail.com', 'gwgm1234', 'GARRIOUX-MORIEN', 'Gwenaëlle', '35', '', 'user', 'False'])
    # Sylvain
    users.append(['slytherogue', 'slytherogue@gmail.com', 'slym0000', 'Michaud', 'Sylvain', '35', '', 'user', 'False'])

    with open(os.path.join(DATA_DIR, 'users.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['username', 'email', 'password', 'nom', 'prenom', 'age', 'avatar_url', 'role', 'is_banned'])
        writer.writerows(users)
    print(f"Generated {len(users)} users in users.csv")

def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--admin-email', default='admin@gnmanager.fr')
    parser.add_argument('--admin-password', default='admin1234')
    parser.add_argument('--admin-nom', default='Admin')
    parser.add_argument('--admin-prenom', default='System')
    return parser.parse_args()


def generate_events(count=3):
    events = []
    statuses = [
        'en préparation', 
        'inscriptions ouvertes', 
        'inscriptions fermées - casting en cours', 
        'casting terminé - finalisation des préparations',
        'annulé',
        'reporté à une date indéfinie'
    ]
    visibilities = ['public', 'private']
    
    for i in range(count):
        start_date = datetime.now() + timedelta(days=30*i)
        end_date = start_date + timedelta(days=2) # 2 days event
        
        events.append([
            f'GN Test {i+1}',
            start_date.strftime('%Y-%m-%d %H:%M:%S'),
            end_date.strftime('%Y-%m-%d %H:%M:%S'),
            f'Lieu {i+1}',
            '', # background_image
            random.choice(visibilities),
            f'Asso Orga {i+1}',
            random.choice(statuses)
        ])
    
    # Custom Events
    # Star Wars - ID 4
    events.append([
        'Star Wars - Ombres sur Tatoine',
        '2026-06-30 00:00:00',
        '2026-07-02 00:00:00',
        'Tatooine',
        '',
        'public',
        'Galactic Empire',
        'en préparation'
    ])
    # Cthulhu - ID 5
    events.append([
        'Cthulhu - ca me gratte dans la tentacule',
        '2026-09-30 00:00:00',
        '2026-10-02 00:00:00',
        'Rlyeh',
        '',
        'public',
        'Cult of Cthulhu',
        'en préparation'
    ])
        
    with open(os.path.join(DATA_DIR, 'events.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'date_start', 'date_end', 'location', 'background_image', 'visibility', 'organizer_structure', 'statut'])
        writer.writerows(events)
    print(f"Generated {len(events)} events in events.csv")

def generate_roles(event_count=3, roles_per_event=5):
    roles = []
    genres = ['Homme', 'Femme', 'Neutre']
    
    role_id_counter = 1
    
    for event_id in range(1, event_count + 1):
        for i in range(roles_per_event):
            roles.append([
                role_id_counter,
                event_id,
                f'Role {i+1} pour Event {event_id}',
                random.choice(genres),
                f'Description du role {i+1}...'
            ])
            role_id_counter += 1
            
    with open(os.path.join(DATA_DIR, 'roles.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'event_id', 'name', 'genre', 'comment'])
        writer.writerows(roles)
    print(f"Generated {len(roles)} roles in roles.csv")

def generate_participants(user_count=10, event_count=3):
    participants = []
    types = ['PJ', 'PNJ', 'organisateur']
    
    # Simple assignment: some users participate in some events
    # We have users 2 to 2+user_count (skipping admin and maybe orgas? admin is id 1)
    # Let's assume users 1..N generated.
    # In import, we'll need to resolve IDs. Here let's just create logical CSVs.
    # We will assume User IDs match the order in users.csv (1-based index)
    
    # User 1 is Admin. User 2,3 are Orgas. User 4.. are Players.
    
    for event_id in range(1, event_count + 1):
        # Orga for event
        participants.append([
            event_id,
            2, # Orga1
            'organisateur',
            'Staff',
            '', # role_id
            '0.0'
        ])
        
        # Players
        for u_id in range(4, 9): # 5 players
             participants.append([
                event_id,
                u_id, 
                'PJ',
                'Groupe A',
                '', # role_id (to be assigned)
                '50.0'
            ])
            
    # Custom Participants
    # Event 4 (Star Wars): Jacques (ID 14) as Orga
    participants.append([4, 14, 'organisateur', 'Staff', '', '0.0'])
    
    # Event 5 (Cthulhu): Gwenaëlle (ID 15) and Sylvain (ID 16) as Orga
    participants.append([5, 15, 'organisateur', 'Staff', '', '0.0'])
    participants.append([5, 16, 'organisateur', 'Staff', '', '0.0'])

    with open(os.path.join(DATA_DIR, 'participants.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['event_id', 'user_id', 'type', 'group', 'role_id', 'payment_amount'])
        writer.writerows(participants)
    print(f"Generated {len(participants)} participants in participants.csv")


if __name__ == "__main__":
    args = parse_args()
    ensure_dir(DATA_DIR)
    
    # Pass args to generate_users
    # We need to modify generate_users signature first, but since we call it here:
    # Let's refactor generate_users slightly or just inline logic? 
    # Better to pass valid args.
    
    # Monkey patch or change function signature? Change signature.
    generate_users(10, args)
    generate_events(3)
    generate_roles(3, 10)
    generate_participants(10, 3)
