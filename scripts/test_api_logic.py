from app import create_app
from models import Event, GFormsSubmission, GFormsFieldMapping
import json

app = create_app()
with app.app_context():
    event = Event.query.first()
    if not event:
        print("No event found")
        exit()
    
    print(f"Testing for event {event.id} ({event.name})")
    
    # Simulate get_fields logic
    submissions = GFormsSubmission.query.filter_by(event_id=event.id).all()
    detected_fields = set(['timestamp', 'type_ajout'])
    for sub in submissions:
        raw_data = json.loads(sub.raw_data) if sub.raw_data else {}
        detected_fields.update(raw_data.keys())
    
    mappings = GFormsFieldMapping.query.filter_by(event_id=event.id).all()
    mapping_dict = {m.field_name: m for m in mappings}
    
    print(f"Detected {len(detected_fields)} fields")
    for field_name in sorted(detected_fields):
        mapping = mapping_dict.get(field_name)
        alias = mapping.field_alias if mapping else "N/A (No mapping)"
        print(f" - {field_name}: alias={alias}")
