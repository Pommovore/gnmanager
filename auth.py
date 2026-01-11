import random
import string

def generate_password():
    """Generates a password with 4 letters followed by 5 digits."""
    letters = ''.join(random.choices(string.ascii_letters, k=4))
    digits = ''.join(random.choices(string.digits, k=5))
    return letters + digits

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to, subject, body):
    """Sends an email using Brevo SMTP."""
    smtp_server = os.environ.get('MAIL_SERVER')
    smtp_port = int(os.environ.get('MAIL_PORT', 587))
    smtp_user = os.environ.get('MAIL_USERNAME')
    smtp_password = os.environ.get('MAIL_PASSWORD')
    smtp_sender = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@gnmanager.fr')
    
    if not smtp_user or not smtp_password:
        print(f"[EMAIL ERROR] MAIL_USERNAME or MAIL_PASSWORD not set. Cannot send to {to}")
        print(f"\\n========== EMAIL (Fallback) ==========\\nTo: {to}\\nSubject: {subject}\\nBody:\\n{body}\\n====================================\\n")
        return False

    print(f"[EMAIL] Attempting to send email to {to} via Brevo. Sender: {smtp_sender}")
    
    # Construction du message
    message = MIMEMultipart()
    message["From"] = f"GN Manager <{smtp_sender}>"
    message["To"] = to
    message["Subject"] = subject
    
    # Correctly encode HTML body as UTF-8
    message.attach(MIMEText(body, "html", "utf-8"))

    try:
        # Connexion et envoi
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            # Send as bytes to avoid ASCII encoding error in smtplib
            server.sendmail(smtp_sender, to, message.as_string().encode('utf-8'))
            
        print(f"[EMAIL SUCCESS] Email sent to {to} via Brevo.")
        return True
    except Exception as e:
        print(f"[EMAIL FAILED] Error sending to {to} via Brevo: {e}")
        # Fallback log
        print(f"\\n========== EMAIL (Fallback) ==========\\nTo: {to}\\nSubject: {subject}\\nBody:\\n{body}\\n====================================\\n")
        return False
