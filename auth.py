import random
import string

def generate_password():
    """Generates a password with 4 letters followed by 4 digits."""
    letters = ''.join(random.choices(string.ascii_letters, k=4))
    digits = ''.join(random.choices(string.digits, k=4))
    return letters + digits

from flask_mail import Message
from extensions import mail

def send_email(to, subject, body):
    """Sends an email using Flask-Mail."""
    try:
        msg = Message(subject, recipients=[to])
        msg.body = body
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")
        # Fallback to console for dev/test without SMTP
        print(f"\\n========== EMAIL (Fallback) ==========\\nTo: {to}\\nSubject: {subject}\\nBody:\\n{body}\\n====================================\\n")
