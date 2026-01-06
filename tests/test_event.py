import requests
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:5000"

def test_event_creation():
    session = requests.Session()
    
    # Login (assuming user from previous test exists, or register new one)
    # Let's register a new one to be safe
    email = "organizer@example.com"
    data = {
        "email": email,
        "nom": "Org",
        "prenom": "Anizer",
        "age": 40
    }
    session.post(f"{BASE_URL}/register", data=data)
    
    # We need to login. But we don't know the password.
    # In a real scenario, we'd mock the email sender or database.
    # Since we are running locally, we can cheat by querying the DB directly in a separate script or just assume the previous test user works if we hardcode credentials?
    # No, passwords are random.
    # Let's make a helper route in app.py for testing ONLY? No, that's bad practice.
    # Let's use the 'admin' user created in a seed script? We don't have one.
    
    # Alternative: The 'register' route prints the password to stdout.
    # We can't read stdout here easily.
    
    # Let's just create a user directly in the DB using python script, with known password.
    pass

if __name__ == "__main__":
    # We will run this logic in a separate script that imports app
    pass
