from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Create test user
    if not User.query.filter_by(email="test@test.com").first():
        user = User(email="test@test.com", nom="Test", prenom="User", age=25)
        user.password_hash = generate_password_hash("test1234")
        db.session.add(user)
        db.session.commit()
        print("Test user created: test@test.com / test1234")
    else:
        print("Test user already exists")
