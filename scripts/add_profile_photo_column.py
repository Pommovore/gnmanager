
import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    with db.engine.connect() as connection:
        # Check if column exists to avoid error
        result = connection.execute(text("PRAGMA table_info(user)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'profile_photo_url' not in columns:
            print("Adding profile_photo_url column to user table...")
            try:
                connection.execute(text("ALTER TABLE user ADD COLUMN profile_photo_url VARCHAR(200)"))
                connection.commit()
                print("Column added successfully.")
            except Exception as e:
                print(f"Error adding column: {e}")
        else:
            print("Column profile_photo_url already exists.")
