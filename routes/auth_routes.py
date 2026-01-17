"""
Routes d'authentification pour GN Manager.

Ce module gère:
- Connexion / Déconnexion
- Inscription et validation de compte
- Réinitialisation de mot de passe
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, AccountValidationToken, PasswordResetToken, ActivityLog
from auth import generate_password, send_email
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from extensions import limiter, oauth
from flask import session
from constants import ActivityLogType, DefaultValues
import uuid
import json
import os

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """
    Page d'accueil - redirige vers le dashboard si connecté, sinon vers login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", error_message="Trop de tentatives de connexion. Veuillez réessayer dans 1 minute.")
def login():
    """
    Page de connexion utilisateur.
    
    Méthodes:
        GET: Affiche le formulaire de connexion
        POST: Traite la tentative de connexion
        
    Returns:
        Template login.html ou redirection vers dashboard si succès
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Vérifier si l'utilisateur existe
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Utilisateur inconnu. Veuillez vous inscrire.', 'danger')
            return redirect(url_for('auth.register'))
            
        if user.is_deleted:
            flash('Ce compte a été supprimé.', 'danger')
            return redirect(url_for('auth.login'))

        if user.is_banned:
            flash('Ce compte a été banni.', 'danger')
            return redirect(url_for('auth.login'))

        if user.password_hash is None:
            flash('Votre compte n\'est pas encore validé. Veuillez vérifier vos emails.', 'warning')
            return redirect(url_for('auth.login'))

        if check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Mot de passe incorrect.', 'danger')
            
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per hour", error_message="Trop de créations de compte. Veuillez réessayer plus tard.")
def register():
    """
    Page d'inscription d'un nouvel utilisateur.
    
    Processus:
    1. L'utilisateur saisit ses informations (email, nom, prénom, âge, genre)
    2. Un token de validation est créé
    3. Un email de confirmation est envoyé
    4. L'utilisateur valide son compte via le lien dans l'email
    
    Returns:
        Template register.html ou redirection selon le résultat
    """
    if request.method == 'POST':
        email = request.form.get('email')
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        age = request.form.get('age')
        
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'warning')
            return redirect(url_for('auth.login'))
            
        # Créer l'utilisateur et le token de validation
        new_user = User(
            email=email, 
            nom=nom, 
            prenom=prenom, 
            age=int(age) if age else None,
            genre=request.form.get('genre'),
            is_banned=False
        )
        
        token_str = str(uuid.uuid4())
        token = AccountValidationToken(token=token_str, email=email)
        
        # Générer l'URL de validation
        if os.environ.get('APP_PUBLIC_HOST'):
            valid_endpoint = url_for('auth.validate_account', token=token_str)
            validation_url = f"http://{os.environ['APP_PUBLIC_HOST']}{valid_endpoint}"
        else:
            validation_url = url_for('auth.validate_account', token=token_str, _external=True)
        
        email_body = f"""
        <h3>Bienvenue sur GN Manager !</h3>
        <p>Votre compte a été créé avec succès.</p>
        <p>Veuillez cliquer sur le lien ci-dessous pour définir votre mot de passe et activer votre compte :</p>
        <p><a href="{validation_url}" style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">Valider mon compte</a></p>
        <p><small>Si le bouton ne fonctionne pas, copiez ce lien : {validation_url}</small></p>
        """
        
        # Tentative d'envoi d'email AVANT commit en base
        email_sent = send_email(email, "Validation de votre compte", email_body)
        
        # En mode test, créer l'utilisateur même si l'email échoue
        from flask import current_app
        if email_sent or current_app.config.get('TESTING', False):
            # Sauvegarder en base uniquement si l'email a été envoyé
            db.session.add(new_user)
            db.session.add(token)
            db.session.commit()
            
            # Logger l'inscription
            log = ActivityLog(
                action_type=ActivityLogType.USER_REGISTRATION.value,
                user_id=new_user.id,
                details=json.dumps({
                    'email': email,
                    'nom': nom,
                    'prenom': prenom,
                    'genre': request.form.get('genre')
                })
            )
            db.session.add(log)
            db.session.commit()
            
            flash('Inscription enregistrée ! Vérifiez vos emails pour valider votre compte. (Pensez à regarder dans vos spams si vous ne recevez rien)', 'success')
            return redirect(url_for('auth.login'))
        else:
            # Email échoué, ne pas créer l'utilisateur
            flash('Erreur lors de l\'envoi de l\'email. L\'inscription n\'a pas été finalisée. Veuillez vérifier votre email ou contacter l\'administrateur.', 'danger')
            return redirect(url_for('auth.register'))
        
    return render_template('register.html')


@auth_bp.route('/validate_account/<token>', methods=['GET', 'POST'])
def validate_account(token):
    """Validation d'un nouveau compte utilisateur."""
    token_entry = AccountValidationToken.query.filter_by(token=token).first()
    
    if not token_entry or datetime.utcnow() - token_entry.created_at > timedelta(hours=DefaultValues.ACCOUNT_VALIDATION_TOKEN_EXPIRY_HOURS):
        flash('Lien invalide ou expiré.', 'danger')
        return redirect(url_for('auth.register'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        
        # Validation
        if len(password) < DefaultValues.PASSWORD_MIN_LENGTH:
            flash('Mot de passe trop court.', 'danger')
            return render_template('set_password.html', token=token)

        user = User.query.filter_by(email=token_entry.email).first()
        if user:
            user.password_hash = generate_password_hash(password)
            db.session.delete(token_entry)
            db.session.commit()
            flash('Compte validé ! Vous pouvez vous connecter.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Utilisateur introuvable.', 'danger')
            return redirect(url_for('auth.register'))

    return render_template('set_password.html', token=token)


@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
@limiter.limit("3 per hour", error_message="Trop de demandes de réinitialisation. Veuillez réessayer plus tard.")
def forgot_password():
    """Demande de réinitialisation de mot de passe."""
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token_str = str(uuid.uuid4())
            token = PasswordResetToken(token=token_str, email=email)
            db.session.add(token)
            db.session.commit()
            
            reset_url = url_for('auth.reset_password', token=token_str, _external=True)
            send_email(email, "Réinitialisation de mot de passe", f"Cliquez sur ce lien pour recevoir un nouveau mot de passe : {reset_url}")
            
        flash('Si cet email existe, un lien de réinitialisation a été envoyé.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html')


@auth_bp.route('/reset_password/<token>')
def reset_password(token):
    """Réinitialisation du mot de passe via token."""
    token_entry = PasswordResetToken.query.filter_by(token=token).first()
    
    if not token_entry or datetime.utcnow() - token_entry.created_at > timedelta(hours=DefaultValues.PASSWORD_RESET_TOKEN_EXPIRY_HOURS):
        flash('Lien invalide ou expiré.', 'danger')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(email=token_entry.email).first()
    if not user:
        flash('Utilisateur introuvable.', 'danger')
        return redirect(url_for('auth.login'))
        
    new_password = generate_password()
    user.password_hash = generate_password_hash(new_password)
    
    db.session.delete(token_entry)
    db.session.commit()
    
    return render_template('reset_password_success.html', password=new_password)


@auth_bp.route('/logout')
@login_required
def logout():
    """Déconnexion de l'utilisateur."""
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/login/google')
def login_google():
    """Redirige vers la page de connexion Google."""
    google = oauth.create_client('google')
    if not google:
        flash("L'authentification Google n'est pas configurée (identifiants manquants).", 'danger')
        return redirect(url_for('auth.login'))
        
    redirect_uri = url_for('auth.authorize_google', _external=True)
    return google.authorize_redirect(redirect_uri)


@auth_bp.route('/auth/google/callback')
def authorize_google():
    """Callback de retour de Google."""
    google = oauth.create_client('google')
    if not google:
        flash("Erreur de configuration Google.", 'danger')
        return redirect(url_for('auth.login'))
        
    try:
        # Récupération du token
        token = google.authorize_access_token()
        session['google_token'] = token
        
        # On pourrait aussi connecter l'utilisateur ici s'il n'est pas loggué
        # resp = google.get('userinfo')
        # user_info = resp.json()
        # ... logique de login ...
        
        flash('Connexion Google réussie ! Vous pouvez maintenant utiliser l\'export Sheets.', 'success')
        
        # Rediriger vers la page d'où l'on vient si stockée, sinon dashboard
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        flash(f'Erreur d\'authentification Google : {str(e)}', 'danger')
        return redirect(url_for('auth.login'))
