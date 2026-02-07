import json
import os
import sys
from datetime import datetime
from manage_db import serialize_model, DateTimeEncoder

def main():
    # Setup App Context
    from app import create_app
    from models import (User, Event, Participant, Role, EventLink,
                        PasswordResetToken, AccountValidationToken,
                        ActivityLog, CastingProposal, CastingAssignment, FormResponse,
                        EventNotification, GFormsCategory, GFormsFieldMapping, GFormsSubmission)
    
    app = create_app()
    with app.app_context():
        print("🔍 Recherche des événements 'Berlin 1936'...")
        target_events = Event.query.filter(Event.name.ilike('%Berlin 1936%')).all()
        
        if not target_events:
            print("❌ Aucun événement trouvé avec le nom contenant 'Berlin 1936'")
            return
            
        target_event_ids = [e.id for e in target_events]
        print(f"✅ {len(target_events)} événements trouvés: ids={target_event_ids}")
        
        # 1. Collecter les participants liés
        print("🔍 Collecte des participants...")
        participants = Participant.query.filter(Participant.event_id.in_(target_event_ids)).all()
        participant_user_ids = {p.user_id for p in participants}
        print(f"  - {len(participants)} participants trouvés")
        
        # 2. Collecter les utilisateurs (Participants + Admins)
        print("🔍 Collecte des utilisateurs...")
        # On garde les participants ET les admins pour ne pas se bloquer
        users = User.query.filter(
            (User.id.in_(participant_user_ids)) | 
            (User.role.in_(['createur', 'sysadmin']))
        ).all()
        print(f"  - {len(users)} utilisateurs (dont admins) conservés")
        
        # 3. Collecter les données liées aux événements
        print("🔍 Collecte des données liées...")
        roles = Role.query.filter(Role.event_id.in_(target_event_ids)).all()
        event_links = EventLink.query.filter(EventLink.event_id.in_(target_event_ids)).all()
        casting_proposals = CastingProposal.query.filter(CastingProposal.event_id.in_(target_event_ids)).all()
        
        # Casting assignments link to proposals/event
        casting_assignments = CastingAssignment.query.filter(CastingAssignment.event_id.in_(target_event_ids)).all()
        
        # Form responses linked to event
        form_responses = FormResponse.query.filter(FormResponse.event_id.in_(target_event_ids)).all()
        
        # GForms data linked to event
        gforms_categories = GFormsCategory.query.filter(GFormsCategory.event_id.in_(target_event_ids)).all()
        gforms_mappings = GFormsFieldMapping.query.filter(GFormsFieldMapping.event_id.in_(target_event_ids)).all()
        gforms_submissions = GFormsSubmission.query.filter(GFormsSubmission.event_id.in_(target_event_ids)).all()
        
        # Notifications linked to event
        notifications = EventNotification.query.filter(EventNotification.event_id.in_(target_event_ids)).all()

        # Construire le dictionnaire de données
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            'description': "Export partiel 'Berlin 1936'",
            'events': [serialize_model(i) for i in target_events],
            'users': [serialize_model(i) for i in users],
            'participants': [serialize_model(i) for i in participants],
            'roles': [serialize_model(i) for i in roles],
            'event_links': [serialize_model(i) for i in event_links],
            'casting_proposals': [serialize_model(i) for i in casting_proposals],
            'casting_assignments': [serialize_model(i) for i in casting_assignments],
            'form_responses': [serialize_model(i) for i in form_responses],
            'gforms_categories': [serialize_model(i) for i in gforms_categories],
            'gforms_field_mappings': [serialize_model(i) for i in gforms_mappings],
            'gforms_submissions': [serialize_model(i) for i in gforms_submissions],
            'event_notifications': [serialize_model(i) for i in notifications],
            
            # Tables vidées volontairement
            'activity_logs': [],
            'password_reset_tokens': [],
            'account_validation_tokens': []
        }
        
        output_file = 'config/seed_prod_db.json'
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, cls=DateTimeEncoder, indent=2, ensure_ascii=False)
            
        print(f"✅ Export terminé : {output_file}")

if __name__ == '__main__':
    main()
