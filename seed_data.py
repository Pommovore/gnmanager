from app import create_app
from models import db, User, Event, Role, Participant, ActivityLog
from werkzeug.security import generate_password_hash
from datetime import datetime, time, timedelta
from dotenv import load_dotenv
import random
import json
import csv
import os

# Charger les variables d'environnement
load_dotenv()

app = create_app()

def export_to_csv():
    """Exporte toutes les données de la base vers des fichiers CSV dans config/"""
    print("\n=== Export des données vers CSV ===")
    
    csv_dir = 'config'
    os.makedirs(csv_dir, exist_ok=True)
    
    # Export Users
    users = User.query.all()
    users_file = os.path.join(csv_dir, 'db_test_users.csv')
    with open(users_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'email', 'password_hash', 'nom', 'prenom', 'age', 'genre', 'avatar_url', 'role', 'is_banned', 'is_deleted'])
        for u in users:
            writer.writerow([
                u.id, u.email, u.password_hash, u.nom, u.prenom, u.age, 
                u.genre or '', u.avatar_url or '', u.role, u.is_banned, u.is_deleted
            ])
    print(f"✓ Exported {len(users)} users to {users_file}")
    
    # Export Events
    events = Event.query.all()
    events_file = os.path.join(csv_dir, 'db_test_events.csv')
    with open(events_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'description', 'date_start', 'date_end', 'location', 
                        'background_image', 'visibility', 'organizer_structure', 'org_link_url',
                        'org_link_title', 'google_form_url', 'google_form_active', 'external_link', 
                        'statut', 'groups_config'])
        for e in events:
            writer.writerow([
                e.id, e.name, e.description or '', 
                e.date_start.isoformat() if e.date_start else '',
                e.date_end.isoformat() if e.date_end else '',
                e.location or '', e.background_image or '', e.visibility or 'public',
                e.organizer_structure or '', e.org_link_url or '', e.org_link_title or '',
                e.google_form_url or '', e.google_form_active or False, e.external_link or '',
                e.statut, e.groups_config or '{}'
            ])
    print(f"✓ Exported {len(events)} events to {events_file}")
    
    # Export Roles
    roles = Role.query.all()
    roles_file = os.path.join(csv_dir, 'db_test_roles.csv')
    with open(roles_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'event_id', 'name', 'type', 'genre', 'group', 'assigned_participant_id', 
                        'comment', 'google_doc_url', 'pdf_url'])
        for r in roles:
            writer.writerow([
                r.id, r.event_id, r.name, r.type or '', r.genre or '', r.group or '',
                r.assigned_participant_id or '', r.comment or '', 
                r.google_doc_url or '', r.pdf_url or ''
            ])
    print(f"✓ Exported {len(roles)} roles to {roles_file}")
    
    # Export Participants
    participants = Participant.query.all()
    participants_file = os.path.join(csv_dir, 'db_test_participants.csv')
    with open(participants_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'event_id', 'user_id', 'type', 'group', 'role_id',
                        'role_communicated', 'role_received', 'registration_status', 'paf_status',
                        'payment_method', 'payment_amount', 'payment_comment', 'comment', 'custom_image'])
        for p in participants:
            writer.writerow([
                p.id, p.event_id, p.user_id, p.type or '', p.group or '', p.role_id or '',
                p.role_communicated, p.role_received, p.registration_status, p.paf_status or 'non versée',
                p.payment_method or '', p.payment_amount or 0.0, p.payment_comment or '',
                p.comment or '', p.custom_image or ''
            ])
    print(f"✓ Exported {len(participants)} participants to {participants_file}")
    
    print("\n✓ Export CSV terminé avec succès!")

def create_user(email, nom, prenom, password, age=None):
    user = User(email=email, nom=nom, prenom=prenom, age=age or random.randint(18, 60))
    user.set_password(password) # Assuming set_password exists or use hash
    # Verify User model has set_password or use direct hash
    user.password_hash = generate_password_hash(password)
    db.session.add(user)
    return user

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    
    print("Creating specific users...")
    # Create Admin/Createur
    # Spec: "createur = celui qui a deployé... sysadmin... actif... banni"
    # We'll make Jacques the Createur here.
    admin_user = User(
        email='jchodorowski@gmail.com', 
        nom='Chodorowski', 
        prenom='Jacques', 
        age=40,
        role='createur', # Super Admin
        is_banned=False
    )
    admin_user.password_hash = generate_password_hash('jach1612')
    db.session.add(admin_user)
    
    # Other users - Admin Système
    user_gwen = User(email='gwengm@gmail.com', nom='GARRIOUX-MORIEN', prenom='Gwenaëlle', age=35, role='sysadmin')  # Admin Système
    user_gwen.password_hash = generate_password_hash('gwgm1234')
    db.session.add(user_gwen)
    
    user_sylvain = User(email='slytherogue@gmail.com', nom='Michaud', prenom='Sylvain', age=35, role='sysadmin')  # Admin Système
    user_sylvain.password_hash = generate_password_hash('slym0000')
    db.session.add(user_sylvain)
    
    # Fictitious Users avec des noms plus parlants
    fictitious_users_data = [
        ('Sophie', 'Dubois', 'sophie.dubois@email.fr'),
        ('Thomas', 'Martin', 'thomas.martin@email.fr'),
        ('Emma', 'Bernard', 'emma.bernard@email.fr'),
        ('Lucas', 'Petit', 'lucas.petit@email.fr'),
        ('Léa', 'Robert', 'lea.robert@email.fr'),
        ('Hugo', 'Richard', 'hugo.richard@email.fr'),
        ('Chloé', 'Durand', 'chloe.durand@email.fr'),
        ('Louis', 'Moreau', 'louis.moreau@email.fr'),
        ('Manon', 'Simon', 'manon.simon@email.fr'),
        ('Arthur', 'Laurent', 'arthur.laurent@email.fr'),
        ('Camille', 'Lefebvre', 'camille.lefebvre@email.fr'),
        ('Nathan', 'Michel', 'nathan.michel@email.fr'),
        ('Sarah', 'Garcia', 'sarah.garcia@email.fr'),
        ('Maxime', 'David', 'maxime.david@email.fr'),
        ('Julie', 'Bertrand', 'julie.bertrand@email.fr'),
        ('Antoine', 'Roux', 'antoine.roux@email.fr'),
        ('Clara', 'Vincent', 'clara.vincent@email.fr'),
        ('Alexandre', 'Fournier', 'alexandre.fournier@email.fr'),
        ('Marine', 'Girard', 'marine.girard@email.fr'),
        ('Julien', 'Bonnet', 'julien.bonnet@email.fr'),
        ('Pauline', 'Dupont', 'pauline.dupont@email.fr'),
        ('Mathieu', 'Lambert', 'mathieu.lambert@email.fr'),
        ('Elise', 'Fontaine', 'elise.fontaine@email.fr'),
        ('Nicolas', 'Rousseau', 'nicolas.rousseau@email.fr'),
        ('Anaïs', 'Morel', 'anais.morel@email.fr'),
        ('Pierre', 'Leroy', 'pierre.leroy@email.fr'),
        ('Laura', 'Gauthier', 'laura.gauthier@email.fr'),
        ('Benjamin', 'Muller', 'benjamin.muller@email.fr'),
        ('Océane', 'Blanc', 'oceane.blanc@email.fr'),
        ('Kevin', 'Guerin', 'kevin.guerin@email.fr'),
        ('Audrey', 'Boyer', 'audrey.boyer@email.fr'),
        ('Romain', 'Martinez', 'romain.martinez@email.fr'),
        ('Morgane', 'Garnier', 'morgane.garnier@email.fr'),
        ('Vincent', 'Chevalier', 'vincent.chevalier@email.fr'),
        ('Jade', 'François', 'jade.francois@email.fr'),
        ('Florian', 'Legrand', 'florian.legrand@email.fr'),
        ('Mélanie', 'Mercier', 'melanie.mercier@email.fr'),
        ('Sylvain', 'Renard', 'sylvain.renard@email.fr'),
        ('Céline', 'Barbier', 'celine.barbier@email.fr'),
    ]
    
    fictitious_users = []
    for prenom, nom, email in fictitious_users_data:
        u = User(email=email, nom=nom, prenom=prenom, age=random.randint(20, 45), role='user')
        u.password_hash = generate_password_hash('test1234')
        db.session.add(u)
        fictitious_users.append(u)
        
    db.session.commit()
    
    # We need to query them back for relationships
    admin_user = User.query.filter_by(email='jchodorowski@gmail.com').first()
    user_gwen = User.query.filter_by(email='gwengm@gmail.com').first()
    user_sylvain = User.query.filter_by(email='slytherogue@gmail.com').first()
    print("Creating Events...")
    # Event 1: Star Wars
    sw_date = datetime(2026, 6, 30, 9, 0)
    event_sw = Event(
        name="Star Wars - Ombres sur Tatooine",
        date_start=sw_date,
        date_end=datetime(2026, 6, 30, 23, 0),
        location="Tatooine (Mos Eisley)",
        description="Une aventure galactique.",
        organizer_structure="Rebel Alliance",
        groups_config=json.dumps({
            "PJ": ["Peu importe", "Rebelles", "Empire", "Contrebandiers"],
            "PNJ": ["Peu importe", "Aliens", "Stormtroopers"],
            "Organisateur": ["général", "coordinateur", "scénariste", "logisticien", "crafteur", "en charge des PNJ"]
        })
    )
    event_sw.statut = "En préparation"
    db.session.add(event_sw)
    
    # Event 2: Cthulhu
    cthulhu_date = datetime(2026, 9, 30, 9, 0)
    event_cthulhu = Event(
        name="Cthulhu - ça me gratte dans la tentacule",
        date_start=cthulhu_date,
        date_end=datetime(2026, 9, 30, 23, 0),
        location="Arkham",
        description="Une enquête horrifique.",
        organizer_structure="Miskatonic U",
        groups_config=json.dumps({
            "PJ": ["Peu importe", "Investigateurs", "Cultistes"],
            "PNJ": ["Peu importe", "Créatures", "Complices"],
            "Organisateur": ["général", "coordinateur", "scénariste", "logisticien", "crafteur", "en charge des PNJ"]
        })
    )
    event_cthulhu.statut = "En préparation"
    db.session.add(event_cthulhu)
    db.session.commit()

    print("Assigning Organizers...")
    # Jacques -> Star Wars (coordinateur)
    p_jacques = Participant(event_id=event_sw.id, user_id=admin_user.id, type="organisateur", group="coordinateur", registration_status="Validé")
    db.session.add(p_jacques)
    
    # Gwen -> Cthulhu (scénariste)
    p_gwen = Participant(event_id=event_cthulhu.id, user_id=user_gwen.id, type="organisateur", group="scénariste", registration_status="Validé")
    db.session.add(p_gwen)
    
    # Sylvain -> Cthulhu (logisticien)
    p_sylvain = Participant(event_id=event_cthulhu.id, user_id=user_sylvain.id, type="organisateur", group="logisticien", registration_status="Validé")
    db.session.add(p_sylvain)
    
    print("Assigning Fictitious Participants...")
    
    # Star Wars: 4 inscrits (2 PJ, 2 PNJ)
    sw_pj = fictitious_users[0:2]  # Sophie, Thomas
    sw_pnj = fictitious_users[2:4]  # Emma, Lucas
    
    for u in sw_pj:
        db.session.add(Participant(event_id=event_sw.id, user_id=u.id, type="PJ", group="Rebelles", registration_status="Validé"))
    for u in sw_pnj:
        db.session.add(Participant(event_id=event_sw.id, user_id=u.id, type="PNJ", group="Aliens", registration_status="Validé"))

    # Cthulhu: 5 inscrits (3 PJ, 2 PNJ) - en plus des 2 organisateurs déjà inscrits
    ct_pj = fictitious_users[4:7]  # Léa, Hugo, Chloé
    ct_pnj = fictitious_users[7:9]  # Louis, Manon
    
    for u in ct_pj:
        db.session.add(Participant(event_id=event_cthulhu.id, user_id=u.id, type="PJ", group="Investigateurs", registration_status="Validé"))
    for u in ct_pnj:
        db.session.add(Participant(event_id=event_cthulhu.id, user_id=u.id, type="PNJ", group="Peu importe", registration_status="Validé"))

    db.session.commit()
    print("Creating additional requested events...")
    admin = User.query.filter_by(email="jchodorowski@gmail.com").first() # Retrieve Jacques/Admin to be organizer
    if not admin:
        admin = User.query.filter_by(is_admin=True).first()
        
    now = datetime(2026, 1, 11) # Fixed reference date or use datetime.now() if system time is correct. 
    # System time is 2026-01-11 per metadata.
    
    # 1. Past Event 1 (-1 year)
    past1 = Event(
        name="L'Appel du Vide (Passé)",
        date_start=now - timedelta(days=365),
        date_end=now - timedelta(days=363),
        location="Ancien Manoir",
        description="Un événement terminé l'an dernier.",
        organizer_structure="Old Guard"
    )
    past1.statut = "Terminé"
    db.session.add(past1)
    
    # 2. Past Event 2 (-6 months)
    past2 = Event(
        name="Tournoi des Trois Lunes (Passé)",
        date_start=now - timedelta(days=180),
        date_end=now - timedelta(days=178),
        location="Plaine de Gaïa",
        description="Un tournoi épique.",
        organizer_structure="Chevaliers"
    )
    past2.statut = "Terminé"
    db.session.add(past2)
    
    # 3. Current Event (Now)
    current_evt = Event(
        name="Siège de la Citadelle (En Cours)",
        date_start=now - timedelta(days=1),
        date_end=now + timedelta(days=1),
        location="La Citadelle",
        description="Une bataille qui fait rage en ce moment même.",
        organizer_structure="Armée Royale"
    )
    current_evt.statut = "Événement en cours"
    db.session.add(current_evt)
    
    # 4. Future Event 1 (+3 months)
    fut1 = Event(
        name="Cyberpunk 2099 (Futur +3 mois)",
        date_start=now + timedelta(days=90),
        date_end=now + timedelta(days=92),
        location="Neo-Tokyo",
        description="Un futur dystopique.",
        organizer_structure="Corpo Arasaka"
    )
    fut1.statut = "En préparation"
    db.session.add(fut1)
    
    # 5. Future Event 2 (+5 months)
    fut2 = Event(
        name="Vampire: La Mascarade (Futur +5 mois)",
        date_start=now + timedelta(days=150),
        date_end=now + timedelta(days=152),
        location="Paris Souterrain",
        description="Intrigues politiques chez les vampires.",
        organizer_structure="Camarilla"
    )
    fut2.statut = "En préparation"
    db.session.add(fut2)
    
    db.session.commit()
    
    # Assign organizer to these new events
    print("Assigning organizers to new events...")
    # Requirement: jchodorowski (admin) ONLY for Star Wars. 
    # Use fictitious users 1-5 for others.
    
    # We need to fetch fictitious users if not already available in scope (they are in 'fictitious_users' list but scope might be lost if script ran linearly)
    # Actually, the script runs linearly. 'fictitious_users' list is available.
    if not fictitious_users or len(fictitious_users) < 5:
        # Fallback if list is empty or too short (shouldn't happen)
        fictitious_users = User.query.filter(User.email.like('user%@example.com')).limit(10).all()
        
    new_events = [past1, past2, current_evt, fut1, fut2]
    
    for i, evt in enumerate(new_events):
        # Assign a different fictitious user to each event
        org_user = fictitious_users[i % len(fictitious_users)]
        db.session.add(Participant(event_id=evt.id, user_id=org_user.id, type="organisateur", group="Organisateur", registration_status="Validé"))
    
    db.session.commit()
    print("Database seeded successfully!")
    
    # === CRÉATION DES RÔLES ===
    print("\\nCreating roles for events...")
    
    # Noms de rôles pour PJ
    pj_role_names = [
        "Commandant Kerillian", "Dame Elira", "Sire Morvan", "Capitaine Vex", 
        "Mage Theron", "Chasseur Lynx", "Prêtresse Selene", "Guerrier Drago",
        "Éclaireur Zara", "Barde Orphéo", "Voleur Shade", "Paladin Aldric",
        "Druide Rowan", "Assassin Viper", "Chevalier Gaëtan", "Sorcière Morgana",
        "Archer Silvan", "Berserker Thork", "Nécromancien Kael", "Templier Marcus",
        "Rôdeur Fenris", "Alchimiste Vera", "Gladiateur Maximus", "Oracle Pythia",
        "Inquisiteur Dante", "Corsaire Barbe-Rouge", "Shaman Totec", "Amazone Xena",
        "Moine Shen", "Pirate Sparrow", "Marchand Caravane", "Forgeron Vulcan"
    ]
    
    # Noms de rôles pour PNJ
    pnj_role_names = [
        "Garde #1", "Garde #2", "Villageois", "Tavernier", "Mendiant",
        "Messager", "Marchand ambulant", "Crieur public", "Soldat", "Serviteur"
    ]
    
    # Récupérer tous les événements
    all_events = Event.query.all()
    now = datetime(2026, 1, 18)  # Date de référence actuelle
    one_month_ahead = now + timedelta(days=30)
    
    role_index = 0
    
    for event in all_events:
        # Parser groups_config
        try:
            groups = json.loads(event.groups_config) if event.groups_config else {}
        except:
            groups = {}
        
        # Définir un groups_config par défaut si absent
        if not groups:
            groups = {
                "PJ": ["Peu importe", "Groupe A", "Groupe B"],
                "PNJ": ["Peu importe", "Figurants", "Techniciens"],
                "Organisateur": ["général", "coordinateur", "scénariste"]
            }
            event.groups_config = json.dumps(groups)
        
        # Déterminer le nombre de rôles PJ (basé sur le nombre de participants max ou défaut)
        # On prend un nombre entre 8 et 20 rôles PJ par événement
        num_pj_roles = random.randint(8, 20)
        num_pnj_roles = random.randint(3, 8)
        
        pj_groups = groups.get("PJ", ["Peu importe"])
        pnj_groups = groups.get("PNJ", ["Peu importe"])
        
        # Créer les rôles PJ
        event_roles = []
        for i in range(num_pj_roles):
            role_name = pj_role_names[(role_index + i) % len(pj_role_names)]
            role = Role(
                event_id=event.id,
                name=role_name,
                type="PJ",
                genre=random.choice(["Homme", "Femme", "Autre", None]),
                group=random.choice(pj_groups),
                comment=f"Rôle important pour l'intrigue principale." if random.random() > 0.7 else None,
                google_doc_url=f"https://docs.google.com/document/d/role_{event.id}_{i}" if random.random() > 0.5 else None,
                pdf_url=None
            )
            db.session.add(role)
            event_roles.append(role)
        
        # Créer les rôles PNJ
        for i in range(num_pnj_roles):
            role_name = pnj_role_names[i % len(pnj_role_names)]
            role = Role(
                event_id=event.id,
                name=f"{role_name} - {event.name[:10]}",
                type="PNJ",
                genre=random.choice(["Homme", "Femme", "Autre", None]),
                group=random.choice(pnj_groups),
                comment=None
            )
            db.session.add(role)
        
        role_index += num_pj_roles
        
        # === CALCUL DU TAUX DE REMPLISSAGE ===
        event_date = event.date_start
        
        # Événement passé ou en cours : 80%+ de remplissage
        if event_date and event_date <= now:
            fill_rate = random.uniform(0.80, 1.0)
        # Événement à moins d'un mois : 80%
        elif event_date and event_date <= one_month_ahead:
            fill_rate = 0.80
        # Événement à plus d'un mois : 20-80%
        else:
            fill_rate = random.uniform(0.20, 0.80)
        
        # Nombre de rôles à assigner
        num_to_assign = int(len(event_roles) * fill_rate)
        
        print(f"  {event.name}: {len(event_roles)} rôles PJ, {num_pnj_roles} rôles PNJ, remplissage {fill_rate*100:.0f}% ({num_to_assign} assignés)")
    
    db.session.commit()
    
    # Export to CSV
    export_to_csv()

