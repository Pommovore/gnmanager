import requests
import time

BASE_URL = "http://localhost:5000"
EMAIL = "test@test.com"

def test_qr_flow():
    session_desktop = requests.Session()
    session_phone = requests.Session()
    
    # 1. Desktop requests QR
    print("1. Requesting QR...")
    resp = session_desktop.post(f"{BASE_URL}/auth/qr/generate", json={"email": EMAIL})
    if resp.status_code != 200:
        print(f"Failed to generate QR: {resp.text}")
        return
        
    data = resp.json()
    token = data['token']
    verify_url = data['verify_url']
    print(f"   Token: {token}")
    print(f"   Verify URL: {verify_url}")
    
    # 2. Desktop polls (should be waiting)
    print("2. Polling status (should be waiting)...")
    resp = session_desktop.get(f"{BASE_URL}/auth/qr/check/{token}")
    print(f"   Status: {resp.json()['status']}")
    assert resp.json()['status'] == 'waiting'
    
    # 3. Phone visits verify page
    print("3. Phone visits verify page...")
    resp = session_phone.get(verify_url)
    assert resp.status_code == 200
    
    # 4. Phone confirms
    print("4. Phone confirms...")
    resp = session_phone.post(verify_url)
    assert resp.status_code == 200
    assert "Connexion validée" in resp.text
    
    # 5. Desktop polls (should be validated)
    print("5. Polling status (should be validated)...")
    resp = session_desktop.get(f"{BASE_URL}/auth/qr/check/{token}")
    print(f"   Status: {resp.json()['status']}")
    assert resp.json()['status'] == 'validated'
    
    # 6. Desktop logs in
    print("6. Desktop performs login...")
    resp = session_desktop.get(f"{BASE_URL}/auth/qr/login/{token}")
    assert resp.status_code == 200
    # Check if redirected to dashboard or if content contains dashboard info
    if "Mes Événements" in resp.text:
        print("   Login Successful! Dashboard loaded.")
    else:
        print("   Login Failed?")
        print(resp.text[:500])

if __name__ == "__main__":
    try:
        test_qr_flow()
    except Exception as e:
        print(f"Test failed: {e}")
