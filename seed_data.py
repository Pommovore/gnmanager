import logging

# Configuration du logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# [rest of imports]

def export_db_to_seed():
    logger.info(f"Exportation de la base de données vers {OUTPUT_FILE}...")
    
    app = create_app()
    with app.app_context():
        data = {
            'timestamp': datetime.now().isoformat(),
            'users': [serialize_model(i) for i in User.query.all()],
            'events': [serialize_model(i) for i in Event.query.all()],
            'event_links': [serialize_model(i) for i in EventLink.query.all()],
            'roles': [serialize_model(i) for i in Role.query.all()],
            'participants': [serialize_model(i) for i in Participant.query.all()],
            'password_reset_tokens': [serialize_model(i) for i in PasswordResetToken.query.all()],
            'account_validation_tokens': [serialize_model(i) for i in AccountValidationToken.query.all()],
            'activity_logs': [serialize_model(i) for i in ActivityLog.query.all()],
            'casting_proposals': [serialize_model(i) for i in CastingProposal.query.all()],
            'casting_assignments': [serialize_model(i) for i in CastingAssignment.query.all()],
            'form_responses': [serialize_model(i) for i in FormResponse.query.all()],
            'event_notifications': [serialize_model(i) for i in EventNotification.query.all()],
            'gforms_categories': [serialize_model(i) for i in GFormsCategory.query.all()],
            'gforms_field_mappings': [serialize_model(i) for i in GFormsFieldMapping.query.all()],
            'gforms_submissions': [serialize_model(i) for i in GFormsSubmission.query.all()]
        }
        
        # S'assurer que le dossier config existe
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, cls=DateTimeEncoder, indent=2, ensure_ascii=False)
            
    logger.info(f"✓ Terminé ! {len(data['users'])} utilisateurs, {len(data['events'])} événements exportés.")

if __name__ == '__main__':
    try:
        export_db_to_seed()
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exportation : {e}")
        sys.exit(1)
