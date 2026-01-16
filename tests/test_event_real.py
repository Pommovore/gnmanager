import requests
import pytest

BASE_URL = "http://localhost:5000"

@pytest.mark.skip(reason="Integration test requires a running server")
def test_event_flow():
    session = requests.Session()
    
    # Login
    resp = session.post(f"{BASE_URL}/login", data={"email": "test@test.com", "password": "test1234"})
    assert "Connexion" not in resp.text # Should redirect
    print("Logged in")
    
    # Create Event
    event_data = {
        "name": "Super LARP",
        "date": "2027-12-31",
        "location": "Castle",
        "visibility": "public"
    }
    resp = session.post(f"{BASE_URL}/event/create", data=event_data)
    assert resp.status_code == 200
    assert "Super LARP" in resp.text
    print("Event created")

if __name__ == "__main__":
    try:
        test_event_flow()
        print("Event flow passed")
    except Exception as e:
        print(f"Failed: {e}")
        if 'resp' in locals():
            print(resp.text)
