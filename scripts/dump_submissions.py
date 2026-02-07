from app import create_app
from models import GFormsSubmission
import json

app = create_app()
with app.app_context():
    subs = GFormsSubmission.query.all()
    print(f"Total submissions: {len(subs)}")
    for s in subs:
        print(f"ID: {s.id}, Event: {s.event_id}, Email: {s.email}, Timestamp: {s.timestamp}, Type: {s.type_ajout}")
        try:
             data = json.loads(s.raw_data) if s.raw_data else {}
             print(f"  Data keys: {list(data.keys())}")
        except Exception as e:
             print(f"  INVALID JSON: {e}")
