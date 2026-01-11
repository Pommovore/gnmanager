import os
from app import create_app

def main():
    app = create_app()
    
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f"Lancement de l'application sur {host}:{port}")
    app.run(host=host, port=port, debug=True)

if __name__ == "__main__":
    main()
