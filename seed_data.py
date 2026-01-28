import json
import os
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Configuration
OUTPUT_FILE = 'config/seed_data.json'

def serialize_date(dt):
    """Sortie ISO pour le JSON"""
    return dt.isoformat() if dt else None

def generate_users(count=300):
    first_names_male = ["Lucas", "Hugo", "Louis", "Gabriel", "Arthur", "Jules", "Maël", "Paul", "Adam", "Nathan", "Léo", "Théo", "Raphaël", "Liam", "Ethan", "Noah", "Sacha", "Tom", "Gabin", "Timéo", "Pierre", "Thomas", "Clément", "Maxime", "Alexandre", "Antoine", "Nicolas", "Julien", "Romain", "Florian", "Guillaume", "Kévin", "Jérémy", "Mathieu", "Adrien", "Alexis", "Benjamin", "Valentin", "Anthony", "Aurélien"]
    first_names_female = ["Emma", "Jade", "Louise", "Alice", "Chloé", "Lina", "Léa", "Rose", "Anna", "Mila", "Inès", "Sarah", "Julia", "Lola", "Juliette", "Zoé", "Manon", "Camille", "Lucie", "Eva", "Marie", "Sophie", "Clara", "Charlotte", "Ambre", "Océane", "Laura", "Julie", "Anaïs", "Pauline", "Marine", "Elise", "Mathilde", "Célia", "Mélanie", "Audrey", "Noémie", "Justine", "Morgane", "Céline"]
    last_names = ["Martin", "Bernard", "Thomas", "Petit", "Robert", "Richard", "Durand", "Dubois", "Moreau", "Laurent", "Simon", "Michel", "Lefebvre", "Leroy", "Roux", "David", "Bertrand", "Morel", "Fournier", "Girard", "Bonnet", "Dupont", "Lambert", "Fontaine", "Rousseau", "Vincent", "Muller", "Lefevre", "Faure", "Andre", "Mercier", "Blanc", "Guerin", "Boyer", "Garnier", "Chevalier", "Francois", "Legrand", "Gauthier", "Garcia", "Perrin", "Robin", "Clement", "Morin", "Nicolas", "Henry", "Roussel", "Mathieu", "Gautier", "Masson"]
    
    users = []
    emails = set()
    
    # Admins fixes avec mots de passe spécifiques
    admins = [
        {'email': 'jchodorowski@gmail.com', 'nom': 'Chodorowski', 'prenom': 'Jacques', 'role': 'createur', 'genre': 'Homme', 'password': 'jach1612'},
        {'email': 'gwengm@gmail.com', 'nom': 'GARRIOUX-MORIEN', 'prenom': 'Gwenaëlle', 'role': 'sysadmin', 'genre': 'Femme', 'password': 'gwgm1234'},
        {'email': 'slytherogue@gmail.com', 'nom': 'Michaud', 'prenom': 'Sylvain', 'role': 'sysadmin', 'genre': 'Homme', 'password': 'slym0000'}
    ]
    
    user_id = 1
    for admin in admins:
        users.append({
            "id": user_id,
            "email": admin['email'],
            "password_hash": generate_password_hash(admin['password']),
            "nom": admin['nom'],
            "prenom": admin['prenom'],
            "age": random.randint(30, 50),
            "genre": admin['genre'],
            "role": admin['role'],
            "avatar_url": None,
            "is_banned": False,
            "is_deleted": False
        })
        emails.add(admin['email'])
        user_id += 1
        
    # Génération aléatoire
    while len(users) < count:
        is_male = random.choice([True, False])
        prenom = random.choice(first_names_male) if is_male else random.choice(first_names_female)
        nom = random.choice(last_names)
        email = f"{prenom.lower()}.{nom.lower()}{random.randint(1,99)}@example.com"
        
        if email in emails:
            continue
            
        emails.add(email)
        users.append({
            "id": user_id,
            "email": email,
            "password_hash": generate_password_hash('test1234'),
            "nom": nom,
            "prenom": prenom,
            "age": random.randint(18, 60),
            "genre": "Homme" if is_male else "Femme",
            "role": "user",
            "avatar_url": None,
            "is_banned": False,
            "is_deleted": False
        })
        user_id += 1
        
    return users

def generate_seed_json():
    print(f"Génération du fichier de seed JSON : {OUTPUT_FILE}...")
    
    data = {
        "users": generate_users(300),
        "events": [],
        "roles": [],
        "participants": [],
        "casting_proposals": [],
        "casting_assignments": []
    }
    
    user_ids = [u['id'] for u in data['users'] if u['role'] == 'user']
    users_map = {u['email']: u['id'] for u in data['users']} # Pour accès rapide
    
    # IDs counters
    event_id_counter = 1
    role_id_counter = 1
    part_id_counter = 1
    assign_id_counter = 1
    prop_id_counter = 1
    
    # =========================================================================
    # 1. EVENT STAR WARS (FIXE) -> Organisateur: Jacques
    # =========================================================================
    print("  Génération Star Wars...")
    now = datetime.now()
    sw_date_start = now + timedelta(days=60)
    
    evt_sw = {
        "id": event_id_counter,
        "name": "Star Wars - Ombres sur Tatooine",
        "description": "Une aventure galactique aux confins de la bordure extérieure.",
        "date_start": serialize_date(sw_date_start),
        "date_end": serialize_date(sw_date_start + timedelta(hours=14)),
        "location": "Tatooine (Mos Eisley)",
        "organizer_structure": "Rebel Alliance",
        "visibility": "public",
        "statut": "En préparation",
        "groups_config": json.dumps({
            "PJ": ["Peu importe", "Rebelles", "Empire", "Contrebandiers"],
            "PNJ": ["Peu importe", "Aliens", "Stormtroopers", "Citoyens"],
            "Organisateur": ["général", "coordinateur", "scénariste", "logisticien", "crafteur", "en charge des PNJ"]
        }),
        "max_pjs": 30,
        "max_pnjs": 15,
        "max_organizers": 10
    }
    data["events"].append(evt_sw)
    sw_id = event_id_counter
    event_id_counter += 1
    
    # Roles SW
    pj_roles_sw = [
        ("Commandant Kerillian", "Rebelles"), ("Dame Elira", "Rebelles"), ("Sire Morvan", "Empire"), ("Capitaine Vex", "Contrebandiers"),
        ("Mage Theron", "Rebelles"), ("Chasseur Lynx", "Empire"), ("Prêtresse Selene", "Empire"), ("Guerrier Drago", "Contrebandiers"),
        ("Éclaireur Zara", "Rebelles"), ("Barde Orphéo", "Contrebandiers"), ("Voleur Shade", "Contrebandiers"), ("Paladin Aldric", "Empire"),
        ("Druide Rowan", "Rebelles"), ("Assassin Viper", "Empire"), ("Chevalier Gaëtan", "Empire"), ("Sorcière Morgana", "Contrebandiers"),
        ("Archer Silvan", "Rebelles"), ("Berserker Thork", "Contrebandiers"), ("Nécromancien Kael", "Empire"), ("Templier Marcus", "Empire"),
        ("Rôdeur Fenris", "Rebelles"), ("Alchimiste Vera", "Rebelles"), ("Gladiateur Maximus", "Empire"), ("Oracle Pythia", "Rebelles")
    ]
    pnj_roles_sw = [
         ("Soldat Impérial #1", "Stormtroopers"), ("Soldat Impérial #2", "Stormtroopers"), 
        ("Barman Cantina", "Citoyens"), ("Chasseur de primes", "Aliens"),
        ("Jawa #1", "Aliens"), ("Jawa #2", "Aliens"), ("Tusken Raider", "Aliens"),
        ("Officier Impérial", "Stormtroopers"), ("Espion Rebelle", "Citoyens")
    ]
    
    sw_roles_objs = []
    
    for name, group in pj_roles_sw:
        r = {"id": role_id_counter, "event_id": sw_id, "name": name, "type": "PJ", "genre": random.choice(["Homme", "Femme", "Autre"]), "group": group, "assigned_participant_id": None}
        data["roles"].append(r)
        sw_roles_objs.append(r)
        role_id_counter += 1
        
    for name, group in pnj_roles_sw:
        r = {"id": role_id_counter, "event_id": sw_id, "name": name, "type": "PNJ", "genre": random.choice(["Homme", "Femme", "Autre"]), "group": group, "assigned_participant_id": None}
        data["roles"].append(r)
        sw_roles_objs.append(r)
        role_id_counter += 1
        
    # Participants SW -> Jacques SEUL orga
    # (Les autres admins peuvent être PJs/PNJs ou rien, pour cet event)
    orga_sw_config = [
        ('jchodorowski@gmail.com', 'coordinateur')
    ]
    
    for email, group in orga_sw_config:
        uid = users_map[email]
        p = {
            "id": part_id_counter,
            "event_id": sw_id,
            "user_id": uid,
            "type": "Organisateur",
            "group": group,
            "registration_status": "Validé",
            "role_communicated": False,
            "role_received": False
        }
        data["participants"].append(p)
        part_id_counter += 1
        
    avail_users = list(user_ids)
    random.shuffle(avail_users)
    
    sw_participants_valid = []
    
    # PJ Validés (Fill all roles)
    for _ in range(len(pj_roles_sw)):
        uid = avail_users.pop()
        p = {"id": part_id_counter, "event_id": sw_id, "user_id": uid, "type": "PJ", "group": "Peu importe", "registration_status": "Validé"}
        data["participants"].append(p)
        sw_participants_valid.append(p)
        part_id_counter += 1
        
    # PNJ Validés
    for _ in range(len(pnj_roles_sw)):
        uid = avail_users.pop()
        p = {"id": part_id_counter, "event_id": sw_id, "user_id": uid, "type": "PNJ", "group": "Peu importe", "registration_status": "Validé"}
        data["participants"].append(p)
        sw_participants_valid.append(p)
        part_id_counter += 1
        
    # Waiting
    for _ in range(5): # PJ
        data["participants"].append({"id": part_id_counter, "event_id": sw_id, "user_id": avail_users.pop(), "type": "PJ", "group": "Peu importe", "registration_status": "En attente"})
        part_id_counter += 1
    for _ in range(2): # PNJ
        data["participants"].append({"id": part_id_counter, "event_id": sw_id, "user_id": avail_users.pop(), "type": "PNJ", "group": "Peu importe", "registration_status": "En attente"})
        part_id_counter += 1

    # Casting SW
    prop = {"id": prop_id_counter, "event_id": sw_id, "name": "Jack", "position": 1, "created_at": serialize_date(now)}
    data["casting_proposals"].append(prop)
    prop_id_counter += 1
    
    num_cast = int(len(sw_participants_valid) * 0.75)
    to_cast = random.sample(sw_participants_valid, num_cast)
    pj_roles_avail = [r for r in sw_roles_objs if r['type'] == 'PJ']
    pnj_roles_avail = [r for r in sw_roles_objs if r['type'] == 'PNJ']
    
    for p in to_cast:
        pool = pj_roles_avail if p['type'] == 'PJ' else pnj_roles_avail
        if pool:
            role = random.choice(pool)
            pool.remove(role)
            data["casting_assignments"].append({
                "id": assign_id_counter, "proposal_id": 1, "role_id": role['id'], "participant_id": p['id'], "event_id": sw_id, "score": 8
            })
            assign_id_counter += 1
            
    # =========================================================================
    # 2. EVENT CTHULHU (FIXE 30/09/2026) -> Orgas: Gwen & Sylvain
    # =========================================================================
    print("  Génération Cthulhu...")
    cth_date = datetime(2026, 9, 30, 20, 0)
    
    evt_cth = {
        "id": event_id_counter,
        "name": "Cthulhu - ca me gratte dans la tentacule",
        "description": "Une horreur indicible se réveille dans les abysses de R'lyeh.",
        "date_start": serialize_date(cth_date),
        "date_end": serialize_date(cth_date + timedelta(hours=6)),
        "location": "Arkham",
        "organizer_structure": "Université Miskatonic",
        "visibility": "public",
        "statut": "En préparation",
        "groups_config": json.dumps({
            "PJ": ["Investigateurs", "Cultistes"],
            "PNJ": ["Monstres", "Habitants"],
            "Organisateur": ["Gardien des arcanes"]
        }),
        "max_pjs": 12,
        "max_pnjs": 5,
        "max_organizers": 5
    }
    data["events"].append(evt_cth)
    cth_id = event_id_counter
    event_id_counter += 1
    
    # Orgas Cthulhu
    for email in ['gwengm@gmail.com', 'slytherogue@gmail.com']:
        uid = users_map[email]
        data["participants"].append({
            "id": part_id_counter, "event_id": cth_id, "user_id": uid, "type": "Organisateur", "group": "Gardien des arcanes", "registration_status": "Validé"
        })
        part_id_counter += 1
        
    # Remplir Cthulhu un peu
    for _ in range(10): # PJs
        if not avail_users: break
        data["participants"].append({"id": part_id_counter, "event_id": cth_id, "user_id": avail_users.pop(), "type": "PJ", "group": "Investigateurs", "registration_status": "Validé"})
        part_id_counter += 1
        
    for i in range(15): # Roles Cthulhu
        data["roles"].append({
             "id": role_id_counter, "event_id": cth_id, "name": f"Investigateur {i+1}", "type": "PJ", "genre": "Autre", "group": "Investigateurs", "assigned_participant_id": None
        })
        role_id_counter += 1

    # =========================================================================
    # 3. OTHER EVENTS (10 others -> total ~12 events)
    # =========================================================================
    print("  Génération des autres événements...")
    
    event_templates = [
        # 3 TERMINÉS
        {
            "name": "Chroniques de l'Ancien Monde", "theme": "Fantasy", "status": "Terminé", 
            "pj_range": (30, 50), "pnj_range": (5, 10), "orga_range": (2, 7),
            "date_delta": -400, "desc": "Une épopée médiévale fantastique qui a marqué les esprits."
        },
        {
            "name": "Projet: Oméga", "theme": "Sci-Fi", "status": "Terminé",
            "pj_range": (30, 50), "pnj_range": (5, 10), "orga_range": (2, 7),
            "date_delta": -250, "desc": "Expérience scientifique ayant tourné au désastre dans un laboratoire secret."
        },
        {
            "name": "Le Bal des Vampires 1889", "theme": "Horreur Gothique", "status": "Terminé",
            "pj_range": (30, 50), "pnj_range": (5, 10), "orga_range": (2, 7),
            "date_delta": -120, "desc": "Intrigues politiques et soif de sang dans le Paris de la Belle Époque."
        },
        # 1 EN COURS
        {
            "name": "Dernier Refuge", "theme": "Post-Apo", "status": "Événement en cours",
            "pj_range": (20, 30), "pnj_range": (3, 6), "orga_range": (3, 5),
            "date_delta": 0, "desc": "Survie en milieu hostile. L'événement se déroule actuellement."
        },
        # 6 FUTURS (2026)
        {
            "name": "Légendes d'Hyboria", "theme": "Fantasy", "status": "En préparation",
            "date_delta": 30, "desc": "Barbares et sorciers s'affrontent."
        },
        {
            "name": "Cyber-Net 2077", "theme": "Cyberpunk", "status": "En préparation",
            "date_delta": 90, "desc": "Piratage et corporations."
        },
        {
            "name": "L'Appel de Cthulhu: Innsmouth", "theme": "Horreur", "status": "En préparation",
            "date_delta": 120, "desc": "Enquête sombre en bord de mer."
        },
         {
            "name": "Western: Gold Rush", "theme": "Historique", "status": "En préparation",
            "date_delta": 180, "desc": "Duels au soleil et pépites d'or."
        },
         {
            "name": "Space Opera: Fédération", "theme": "Sci-Fi", "status": "En préparation",
            "date_delta": 240, "desc": "Diplomatie intergalactique."
        },
         {
            "name": "Zombies: Jour Z", "theme": "Post-Apo", "status": "En préparation",
            "date_delta": 300, "desc": "Ils reviennent..."
        }
    ]
    
    # Reload fresh list of unused users for these events
    # We want to use the 'avail_users' left over, OR just recycle everyone to simulate activity
    current_users = list(user_ids) 
    random.shuffle(current_users)
    
    for t in event_templates:
        evt_id = event_id_counter
        event_id_counter += 1
        
        # Date management
        d_start = now + timedelta(days=t['date_delta'])
        d_end = d_start + timedelta(days=2)
        
        # Config
        groups = {
            "PJ": ["Peu importe", "Groupe A", "Groupe B", "Groupe C"],
            "PNJ": ["Peu importe", "Adversaires", "Ambiance"],
            "Organisateur": ["Orga Principal", "Scénario", "Logistique"]
        }
        
        evt = {
            "id": evt_id,
            "name": t["name"],
            "description": t["desc"],
            "date_start": serialize_date(d_start),
            "date_end": serialize_date(d_end),
            "location": "Lieu Inconnu",
            "organizer_structure": "Association GN",
            "visibility": "public",
            "statut": t["status"],
            "groups_config": json.dumps(groups),
            "max_pjs": 60,
            "max_pnjs": 20,
            "max_organizers": 10
        }
        data["events"].append(evt)
        
        # Participant filling
        num_pj = random.randint(t.get("pj_range", (5, 20))[0], t.get("pj_range", (5, 20))[1])
        num_pnj = random.randint(t.get("pnj_range", (2, 8))[0], t.get("pnj_range", (2, 8))[1])
        num_orga = random.randint(t.get("orga_range", (1, 3))[0], t.get("orga_range", (1, 3))[1])
        
        # Orgas
        for _ in range(num_orga):
            if current_users:
                data["participants"].append({
                    "id": part_id_counter, "event_id": evt_id, "user_id": current_users.pop(), 
                    "type": "Organisateur", "group": "Orga Principal", "registration_status": "Validé"
                })
                part_id_counter += 1
                if not current_users: # Refresh if empty
                    current_users = list(user_ids)
                    random.shuffle(current_users)
                
        # PJs
        for _ in range(num_pj):
             if current_users:
                data["participants"].append({
                    "id": part_id_counter, "event_id": evt_id, "user_id": current_users.pop(), 
                    "type": "PJ", "group": random.choice(groups["PJ"]), "registration_status": "Validé" if t["status"] in ["Terminé", "Événement en cours"] else random.choice(["Validé", "En attente"])
                })
                part_id_counter += 1
                if not current_users:
                    current_users = list(user_ids)
                    random.shuffle(current_users)
                
        # PNJs
        for _ in range(num_pnj):
             if current_users:
                data["participants"].append({
                    "id": part_id_counter, "event_id": evt_id, "user_id": current_users.pop(), 
                    "type": "PNJ", "group": random.choice(groups["PNJ"]), "registration_status": "Validé"
                })
                part_id_counter += 1
                if not current_users:
                    current_users = list(user_ids)
                    random.shuffle(current_users)
                
        # Generate Roles for these events (Basic)
        for i in range(num_pj + 5):
            data["roles"].append({
                "id": role_id_counter, "event_id": evt_id, "name": f"Rôle PJ {i+1}", "type": "PJ", "genre": random.choice(["Homme", "Femme"]), "group": random.choice(groups["PJ"]), "assigned_participant_id": None
            })
            role_id_counter += 1
        for i in range(num_pnj + 3):
            data["roles"].append({
                "id": role_id_counter, "event_id": evt_id, "name": f"Rôle PNJ {i+1}", "type": "PNJ", "genre": random.choice(["Homme", "Femme"]), "group": random.choice(groups["PNJ"]), "assigned_participant_id": None
            })
            role_id_counter += 1

    # Write
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"✓ Terminé ! {len(data['users'])} users, {len(data['events'])} events, {len(data['participants'])} participants.")

if __name__ == '__main__':
    generate_seed_json()

