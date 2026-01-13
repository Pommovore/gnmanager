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
    user_map = {} # email -> id
    current_id = 1
    
    # 1. Admin (Createur)
    if args:
        admin_email = args.admin_email
        users.append(['admin', admin_email, args.admin_password, args.admin_nom, args.admin_prenom, '30', '', 'createur', 'False'])
    else:
        admin_email = 'admin@gnmanager.fr'
        users.append(['admin', admin_email, 'admin1234', 'Admin', 'System', '30', '', 'createur', 'False'])
    
    user_map[admin_email] = current_id
    current_id += 1
        
    # 2. Organizers
    for i in range(2):
        email = f'orga{i}@test.com'
        if email != admin_email: # Safety check
            users.append([
                f'orga{i}', 
                email, 
                'test1234', 
                f'Orga{i}', 
                'User', 
                '25', 
                '', 
                'user',
                'False'
            ])
            user_map[email] = current_id
            current_id += 1
            
    # 3. Players
    for i in range(count):
        email = f'player{i}@test.com'
        if email != admin_email: 
            users.append([
                f'player{i}', 
                email, 
                'test1234', 
                f'Player{i}', 
                'User', 
                str(20 + i), 
                '', 
                'user',
                'False'
            ])
            user_map[email] = current_id
            current_id += 1
            
    # 4. Custom Users
    special_users = [
        ['jchodorowski', 'jchodorowski@gmail.com', 'jach1612', 'Chodorowski', 'Jacques', '40', '', 'createur', 'False'],
        ['gwengm', 'gwengm@gmail.com', 'gwgm1234', 'GARRIOUX-MORIEN', 'Gwenaëlle', '35', '', 'user', 'False'],
        ['slytherogue', 'slytherogue@gmail.com', 'slym0000', 'Michaud', 'Sylvain', '35', '', 'user', 'False']
    ]
    
    for u in special_users:
        email = u[1]
        if email == admin_email:
            # Already added as ID 1, map matches, skip adding to list to avoid duplicate in CSV
            pass
        else:
            users.append(u)
            user_map[email] = current_id
            current_id += 1

    with open(os.path.join(DATA_DIR, 'users.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['username', 'email', 'password', 'nom', 'prenom', 'age', 'avatar_url', 'role', 'is_banned'])
        writer.writerows(users)
    print(f"Generated {len(users)} users in users.csv")
    return user_map

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
        'En préparation', 
        'Inscriptions ouvertes', 
        'Inscriptions fermées', 
        'Casting en cours',
        'Casting terminé',
        'Annulé',
        'Reporté'
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
        'En préparation'
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
        'En préparation'
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

def generate_participants(user_map, user_count=10, event_count=3):
    participants = []
    # User map helps us find IDs for specific emails
    
    # Generic logic for generic users
    # "Orga 0" (ID 2 usually, check map)
    # "Orga 1" (ID 3 usually)
    # Players 0..4 (IDs 4..8 usually)
    
    # Define IDs based on map if possible, else fallback to assumptions or skip if missing
    def get_id(email):
        return user_map.get(email)
        
    orga1_id = get_id('orga0@test.com')
    
    for event_id in range(1, event_count + 1):
        if orga1_id:
            participants.append([event_id, orga1_id, 'organisateur', 'Staff', '', '0.0'])
        
        # Players
        for i in range(5):
             pid = get_id(f'player{i}@test.com')
             if pid:
                 participants.append([event_id, pid, 'PJ', 'Groupe A', '', '50.0'])
            
    # Custom Participants
    
    # Event 4 (Star Wars): Jacques
    jacques_id = get_id('jchodorowski@gmail.com')
    if jacques_id:
        participants.append([4, jacques_id, 'organisateur', 'Staff', '', '0.0'])
    
    # Event 5 (Cthulhu): Gwenaëlle and Sylvain
    gwen_id = get_id('gwengm@gmail.com')
    if gwen_id:
        participants.append([5, gwen_id, 'organisateur', 'Staff', '', '0.0'])
        
    sylvain_id = get_id('slytherogue@gmail.com')
    if sylvain_id:
        participants.append([5, sylvain_id, 'organisateur', 'Staff', '', '0.0'])

    with open(os.path.join(DATA_DIR, 'participants.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['event_id', 'user_id', 'type', 'group', 'role_id', 'payment_amount'])
        writer.writerows(participants)
    print(f"Generated {len(participants)} participants in participants.csv")


if __name__ == "__main__":
    args = parse_args()
    ensure_dir(DATA_DIR)
    
    user_map = generate_users(10, args)
    generate_events(3)
    generate_roles(3, 10)
    generate_participants(user_map, 10, 3)
