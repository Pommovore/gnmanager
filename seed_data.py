from app import create_app
from models import db, User, Event, Role, Participant
from werkzeug.security import generate_password_hash
from datetime import datetime, time, timedelta
import random

app = create_app()

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
    
    # Other users
    user_gwen = User(email='gwengm@gmail.com', nom='GARRIOUX-MORIEN', prenom='Gwenaëlle', age=35, role='user') # Normal user (potentially org for some events)
    user_gwen.password_hash = generate_password_hash('gwgm1234')
    db.session.add(user_gwen)
    
    user_sylvain = User(email='slytherogue@gmail.com', nom='Michaud', prenom='Sylvain', age=35, role='user')
    user_sylvain.password_hash = generate_password_hash('slym0000')
    db.session.add(user_sylvain)
    
    # Fictitious Users (for testing pagination/roles)
    for i in range(1, 25): # Enough for pagination test (>20)
        u = User(email=f'user{i}@example.com', nom=f'Nom{i}', prenom=f'Prenom{i}', role='user')
        u.password_hash = generate_password_hash('test1234')
        db.session.add(u)
        
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
        # status="En préparation", # Use default or set later if kwarg fails
        organizer_structure="Rebel Alliance"
    )
    event_sw.statut = "En préparation"
    db.session.add(event_sw)
    
    # Event 2: Cthulhu
    cthulhu_date = datetime(2026, 9, 30, 9, 0)
    event_cthulhu = Event(
        name="Cthulhu - ca me gratte dans la tentacule",
        date_start=cthulhu_date,
        date_end=datetime(2026, 9, 30, 23, 0),
        location="Arkham",
        description="Une enquête horrifique.",
        # status="En préparation",
        organizer_structure="Miskatonic U"
    )
    event_cthulhu.statut = "En préparation"
    db.session.add(event_cthulhu)
    db.session.commit()

    print("Assigning Organizers...")
    # Jacques -> Star Wars
    p_jacques = Participant(event_id=event_sw.id, user_id=jacques.id, type="organisateur", group="Organisateur", registration_status="Validé")
    db.session.add(p_jacques)
    
    # Gwen -> Cthulhu
    p_gwen = Participant(event_id=event_cthulhu.id, user_id=gwen.id, type="organisateur", group="Organisateur", registration_status="Validé")
    db.session.add(p_gwen)
    
    # Sylvain -> Cthulhu
    p_sylvain = Participant(event_id=event_cthulhu.id, user_id=sylvain.id, type="organisateur", group="Organisateur", registration_status="Validé")
    db.session.add(p_sylvain)
    
    print("Assigning Fictitious Participants...")
    
    # Star Wars: 4 PJ, 5 PNJ from fictitious (indices 0-8)
    sw_pj = fictitious_users[0:4]
    sw_pnj = fictitious_users[4:9]
    
    for u in sw_pj:
        db.session.add(Participant(event_id=event_sw.id, user_id=u.id, type="PJ", group="Peu importe", registration_status="Validé"))
    for u in sw_pnj:
        db.session.add(Participant(event_id=event_sw.id, user_id=u.id, type="PNJ", group="Peu importe", registration_status="Validé"))

    # Cthulhu: 16 PJ, 13 PNJ from fictitious (indices 9-37)
    # 9 + 16 = 25
    ct_pj = fictitious_users[9:25]
    # 25 + 13 = 38
    ct_pnj = fictitious_users[25:38]
    
    for u in ct_pj:
        db.session.add(Participant(event_id=event_cthulhu.id, user_id=u.id, type="PJ", group="Peu importe", registration_status="Validé"))
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
