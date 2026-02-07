from app import create_app
from flask import url_for
import json

app = create_app()
with app.app_context():
    # Find an event with submissions
    from models import GFormsSubmission, Event
    sub = GFormsSubmission.query.first()
    if not sub:
        print("No submissions found")
        exit()
    
    event_id = sub.event_id
    print(f"Testing API for event {event_id}")
    
    with app.test_client() as client:
        # Mock login if necessary, but organizer_required usually needs a real user session
        # For simplicity, let's just call the internal functions
        from routes.gforms_routes import get_submissions_data, get_fields
        
        # We need to simulate a request context for jsonify and args
        with app.test_request_context(f'/api/event/{event_id}/gforms/submissions?page=1'):
            try:
                resp = get_submissions_data(event_id)
                print("Submissions API: SUCCESS")
                # print(resp.get_data(as_text=True))
            except Exception as e:
                print(f"Submissions API: FAILED with {e}")
                import traceback
                traceback.print_exc()

        with app.test_request_context(f'/api/event/{event_id}/gforms/fields'):
            try:
                resp = get_fields(event_id)
                print("Fields API: SUCCESS")
            except Exception as e:
                print(f"Fields API: FAILED with {e}")
                import traceback
                traceback.print_exc()
