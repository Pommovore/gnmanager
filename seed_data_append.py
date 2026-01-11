
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
    past1.status = "Terminé"
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
    past2.status = "Terminé"
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
    current_evt.status = "Evènement en cours"
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
    fut1.status = "En préparation"
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
    fut2.status = "En préparation"
    db.session.add(fut2)
    
    db.session.commit()
    
    # Assign organizer to these new events
    print("Assigning organizer to new events...")
    new_events = [past1, past2, current_evt, fut1, fut2]
    for evt in new_events:
        db.session.add(Participant(event_id=evt.id, user_id=admin.id, type="organisateur", group="Organisateur", registration_status="Validé"))
    
    db.session.commit()
