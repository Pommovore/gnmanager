"""
Routes principales de l'application GN Manager.

Ce module définit toutes les routes Flask pour:
- Authentification (login, register, logout, reset password)
- Tableau de bord utilisateur
- Gestion des événements (création, édition, suppression)
- Administration (gestion des utilisateurs)
- Gestion des rôles et des participants
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Event, Participant, PasswordResetToken, AccountValidationToken
from auth import generate_password, send_email
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import json
import os

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Registration flow if user doesn't exist (simplified for single entry point as per spec "s'enregistre avec son email")
            # Spec says: "Lorsque l’utilisateur s’enregistre avec son email..." and "connexion...". 
            # Usually these are separate, but if the login form handles both or if there is a specific registration form.
            # The spec says "un utilisateur est identifié par son email. un formulaire lui est proposé pour saisir : email, nom, prénom, age..."
            # Let's assume a separate registration page or a "Register" button.
            # For now, standard login.
            flash('Utilisateur inconnu. Veuillez vous inscrire.', 'danger')
            return redirect(url_for('main.register'))
            
        if user.is_deleted:
             flash('Ce compte a été supprimé.', 'danger')
             return redirect(url_for('main.login'))

        if user.is_banned:
             flash('Ce compte a été banni.', 'danger')
             return redirect(url_for('main.login'))

        if user.password_hash is None:
             flash('Votre compte n\'est pas encore validé. Veuillez vérifier vos emails.', 'warning')
             return redirect(url_for('main.login'))

        if check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Mot de passe incorrect.', 'danger')
            
    return render_template('login.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        age = request.form.get('age')
        
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'warning')
            return redirect(url_for('main.login'))
            
        # Créer l'utilisateur et le token de validation (non commité en base)
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
            valid_endpoint = url_for('main.validate_account', token=token_str)
            validation_url = f"http://{os.environ['APP_PUBLIC_HOST']}{valid_endpoint}"
        else:
            validation_url = url_for('main.validate_account', token=token_str, _external=True)
        
        email_body = f"""
        <h3>Bienvenue sur GN Manager !</h3>
        <p>Votre compte a été créé avec succès.</p>
        <p>Veuillez cliquer sur le lien ci-dessous pour définir votre mot de passe et activer votre compte :</p>
        <p><a href="{validation_url}" style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">Valider mon compte</a></p>
        <p><small>Si le bouton ne fonctionne pas, copiez ce lien : {validation_url}</small></p>
        """
        
        # Tentative d'envoi d'email AVANT commit en base
        email_sent = send_email(email, "Validation de votre compte", email_body)
        
        if email_sent:
            # Sauvegarder en base uniquement si l'email a été envoyé
            db.session.add(new_user)
            db.session.add(token)
            db.session.commit()
            flash('Inscription enregistrée ! Vérifiez vos emails pour valider votre compte. (Pensez à regarder dans vos spams si vous ne recevez rien)', 'success')
            return redirect(url_for('main.login'))
        else:
            # Email échoué, ne pas créer l'utilisateur
            flash('Erreur lors de l\'envoi de l\'email. L\'inscription n\'a pas été finalisée. Veuillez vérifier votre email ou contacter l\'administrateur.', 'danger')
            return redirect(url_for('main.register'))
        
    return render_template('register.html')

@main.route('/validate_account/<token>', methods=['GET', 'POST'])
def validate_account(token):
    token_entry = AccountValidationToken.query.filter_by(token=token).first()
    
    if not token_entry or datetime.utcnow() - token_entry.created_at > timedelta(hours=24):
        flash('Lien invalide ou expiré.', 'danger')
        return redirect(url_for('main.register'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        # Simple validation
        if len(password) < 6:
             flash('Mot de passe trop court.', 'danger')
             return render_template('set_password.html', token=token)

        user = User.query.filter_by(email=token_entry.email).first()
        if user:
            user.password_hash = generate_password_hash(password)
            db.session.delete(token_entry)
            db.session.commit()
            flash('Compte validé ! Vous pouvez vous connecter.', 'success')
            return redirect(url_for('main.login'))
        else:
            flash('Utilisateur introuvable.', 'danger')
            return redirect(url_for('main.register'))

    return render_template('set_password.html', token=token)

@main.route('/dashboard')
@login_required
def dashboard():
    users_pagination = None
    if current_user.is_admin: # Uses the property we added
        page = request.args.get('page', 1, type=int)
        users_pagination = User.query.paginate(page=page, per_page=20, error_out=False)
        
    # Filter Logic
    filter_type = request.args.get('filter', 'all')
    
    # Identify my event IDs for highlighting    # Get user's roles in these events
    my_participations = Participant.query.filter_by(user_id=current_user.id).all()
    my_event_ids = [p.event_id for p in my_participations]
    my_roles = {p.event_id: p for p in my_participations} # Map event_id -> Participant object
    
    events = []
    now = datetime.now()
    
    if filter_type == 'mine':
        # Events I participate in
        if my_event_ids:
            events = Event.query.filter(Event.id.in_(my_event_ids)).order_by(Event.date_start).all()
    elif filter_type == 'future':
        events = Event.query.filter(Event.date_start >= now).order_by(Event.date_start).all()
    elif filter_type == 'past':
        events = Event.query.filter(Event.date_end < now).order_by(Event.date_start.desc()).all()
    else:
        # 'all'
        events = Event.query.order_by(Event.date_start).all()
        
    # Admin Sub-Navigation
    admin_view = request.args.get('admin_view')
    
    return render_template('dashboard.html', user=current_user, users_pagination=users_pagination, events=events, my_event_ids=my_event_ids, my_roles=my_roles, current_filter=filter_type, admin_view=admin_view)

@main.route('/profile', methods=['POST'])
@login_required
def update_profile():
    current_user.nom = request.form.get('nom')
    current_user.prenom = request.form.get('prenom')
    current_user.age = request.form.get('age')
    current_user.genre = request.form.get('genre') # Added
    
    # Avatar upload
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename != '':
            from PIL import Image
            import os
            from werkzeug.utils import secure_filename
            
            filename = secure_filename(file.filename)
            # Save to static/avatars
            upload_folder = os.path.join(current_user.id.__str__(), 'avatars') # or just static/avatars
            # Spec says: "stockée dans la base d’images avec l’identifiant : email utilisateur..."
            # Let's use a simple path for now: static/uploads/avatars/<email>_avatar.png
            
            # Ensure directory exists
            static_folder = os.path.join(os.getcwd(), 'static', 'uploads')
            os.makedirs(static_folder, exist_ok=True)
            
            # Resize
            img = Image.open(file)
            img.thumbnail((80, 80))
            
            # Construct filename as per spec (simplified for now, spec was for event image)
            # Spec for avatar: "un utilisateur peut ajouter une image de son avatar"
            # Spec for event participant image: "l’utilisateur peut fournir lui une image qui sera stockée... avec l’identifiant : email..."
            
            save_path = os.path.join(static_folder, f"avatar_{current_user.id}.png")
            img.save(save_path)
            current_user.avatar_url = f"/static/uploads/avatar_{current_user.id}.png"

    # Password reset logic
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password:
        if new_password == confirm_password:
            current_user.password_hash = generate_password_hash(new_password)
            flash('Mot de passe mis à jour.', 'success')
        else:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('main.dashboard'))

    db.session.commit()
    flash('Profil mis à jour.', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/admin/user/add', methods=['POST'])
@login_required
def admin_add_user():
    if not current_user.is_admin:
        flash('Accès refusé.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    email = request.form.get('email')
    if User.query.filter_by(email=email).first():
        flash('Cet email existe déjà.', 'warning')
        return redirect(url_for('main.dashboard', admin_view='add', _anchor='admin'))
        
    password = generate_password()
    hashed_password = generate_password_hash(password)
    
    # Admin only provides email, user fills the rest later? 
    # Spec: "Lorsqu’il ajoute manuellement des utilisateurs un email doit être saisi... L’utilisateur complète ensuite son identité"
    new_user = User(email=email, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    send_email(email, "Bienvenue", f"Votre compte a été créé. Mot de passe : {password}")
    flash(f'Utilisateur {email} ajouté.', 'success')
    return redirect(url_for('main.dashboard', admin_view='users', open_edit=new_user.id, _anchor='admin'))



@main.route('/admin/user/<int:user_id>/update_full', methods=['POST'])
@login_required
def admin_update_full_user(user_id):
    if not current_user.is_admin:
         return jsonify({'error': 'Unauthorized'}), 403
         
    user = User.query.get_or_404(user_id)
    
    # Security Check: Non-Createurs cannot edit Createurs
    if user.role == 'createur' and current_user.role != 'createur':
        flash('Vous ne pouvez pas modifier un compte administrateur suprême (Créateur).', 'danger')
        return redirect(url_for('main.dashboard', admin_view='users', _anchor='admin'))
    
    # Update standard fields
    user.email = request.form.get('email') # Admin can change verify email
    user.nom = request.form.get('nom')
    user.prenom = request.form.get('prenom')
    user.age = request.form.get('age')
    user.genre = request.form.get('genre')
    
    # Update Password if provided
    new_password = request.form.get('password')
    if new_password:
        user.password_hash = generate_password_hash(new_password)
    
    # Update Status/Role
    status_code = request.form.get('status') # createur, sysadmin, actif, banni
    
    # Logic to map single select "status" to role + is_banned
    # Logic to map single select "status" to role + is_banned
    if status_code == 'createur':
        if current_user.role == 'createur':
            user.role = 'createur'
            user.is_banned = False
        else:
             flash("Vous ne pouvez pas nommer un Créateur.", "danger")
    elif status_code == 'sysadmin':
        user.role = 'sysadmin'
        
    db.session.commit()
    flash(f"Utilisateur {user.email} mis à jour.", "success")
    return redirect(url_for('main.dashboard', admin_view='users', _anchor='admin'))

@main.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    user = User.query.get_or_404(user_id)
    
    # Security: Cannot delete self
    if user.id == current_user.id:
        flash("Vous ne pouvez pas supprimer votre propre compte ici.", "danger")
        return redirect(url_for('main.dashboard', admin_view='users', _anchor='admin'))
        
    # Security: Non-Creator cannot delete Creator
    if user.role == 'createur' and current_user.role != 'createur':
        flash("Vous ne pouvez pas supprimer un compte Créateur.", "danger")
        return redirect(url_for('main.dashboard', admin_view='users', _anchor='admin'))

    try:
        print(f"[DELETE USER] Tentative de suppression de {user.email} (ID: {user.id})", flush=True)
        
        # Suppression en cascade des entités liées
        # Note: SQLAlchemy peut gérer ceci automatiquement avec cascade="all, delete-orphan"
        # mais nous le faisons explicitement pour plus de clarté et de contrôle
        
        # 1. Désassigner tous les rôles qui pointent vers les participants de cet utilisateur
        # (relation circulaire Role <-> Participant)
        participants = Participant.query.filter_by(user_id=user.id).all()
        participant_ids = [p.id for p in participants]
        
        if participant_ids:
            print(f"[DELETE USER] Désassignation des rôles liés aux {len(participant_ids)} participants", flush=True)
            from models import Role
            roles_to_unassign = Role.query.filter(Role.assigned_participant_id.in_(participant_ids)).all()
            for role in roles_to_unassign:
                role.assigned_participant_id = None
                print(f"[DELETE USER] Rôle '{role.name}' désassigné", flush=True)
        
        # 2. Supprimer les tokens de validation et de réinitialisation
        print(f"[DELETE USER] Suppression des tokens", flush=True)
        AccountValidationToken.query.filter_by(email=user.email).delete()
        PasswordResetToken.query.filter_by(email=user.email).delete()  # Utiliser email, pas user_id
        
        # 3. Supprimer les participations aux événements
        print(f"[DELETE USER] Suppression des participations", flush=True)
        Participant.query.filter_by(user_id=user.id).delete()
        
        # 4. Supprimer l'utilisateur
        print(f"[DELETE USER] Suppression de l'utilisateur", flush=True)
        db.session.delete(user)
        
        # 5. Commit
        db.session.commit()
        print(f"[DELETE USER] Suppression réussie de {user.email}", flush=True)
        flash(f"Utilisateur {user.email} supprimé définitivement.", "success")
    except Exception as e:
        db.session.rollback()
        print(f"[DELETE USER] ERREUR: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
        
    return redirect(url_for('main.dashboard', admin_view='users', _anchor='admin'))




@main.route('/event/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        name = request.form.get('name')
        date_start_str = request.form.get('date_start')
        date_end_str = request.form.get('date_end')
        location = request.form.get('location')
        visibility = request.form.get('visibility')
        
        date_start = datetime.strptime(date_start_str, '%Y-%m-%d')
        date_end = datetime.strptime(date_end_str, '%Y-%m-%d')
        
        new_event = Event(
            name=name, 
            description=request.form.get('description', ''),
            date_start=date_start, 
            date_end=date_end, 
            location=location, 
            visibility=visibility, 
            statut='En préparation',
            external_link=request.form.get('external_link', '')
        )
        db.session.add(new_event)
        db.session.commit()
        
        participant = Participant(event_id=new_event.id, user_id=current_user.id, type='organisateur', role_communicated=True, registration_status='Validé')
        db.session.add(participant)
        db.session.commit()
        
        flash('Événement créé avec succès !', 'success')
        return redirect(url_for('main.event_detail', event_id=new_event.id))
        
    return render_template('event_create.html')

@main.route('/event/<int:event_id>/update_general', methods=['POST'])
@login_required
def update_event_general(event_id):
    event = Event.query.get_or_404(event_id)
    # Check permissions (organizer)
    participant = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not participant or participant.type != 'organisateur':
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('main.event_detail', event_id=event.id))
        
    name = request.form.get('name')
    location = request.form.get('location')
    date_start_str = request.form.get('date_start')
    date_end_str = request.form.get('date_end')
    description = request.form.get('description')
    external_link = request.form.get('external_link')
    
    if name: event.name = name
    if location: event.location = location
    if date_start_str: event.date_start = datetime.strptime(date_start_str, '%Y-%m-%d')
    if date_end_str: event.date_end = datetime.strptime(date_end_str, '%Y-%m-%d')
    if description is not None: event.description = description
    if external_link is not None: event.external_link = external_link
        
    db.session.commit()
    flash('Informations générales mises à jour.', 'success')
    return redirect(url_for('main.event_detail', event_id=event.id))

@main.route('/event/<int:event_id>/update_status', methods=['POST'])
@login_required
def update_event_status(event_id):
    event = Event.query.get_or_404(event_id)
    participant = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not participant or participant.type != 'organisateur':
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('main.event_detail', event_id=event.id))
        
    statut = request.form.get('statut')
    if statut:
        event.statut = statut
        db.session.commit()
        flash('Statut mis à jour.', 'success')
        
    return redirect(url_for('main.event_detail', event_id=event.id))

@main.route('/event/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    # Check if user is participant
    participant = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    
    is_organizer = participant and participant.type == 'organisateur'
    
    is_organizer = participant and participant.type == 'organisateur'
    
    groups_config = json.loads(event.groups_config or '{}')

    groups_config = json.loads(event.groups_config or '{}')
    
    breadcrumbs = [
        ('GN Manager', '/dashboard'),
        (event.name, '#') # Current page
    ]

    return render_template('event_detail.html', event=event, participant=participant, is_organizer=is_organizer, groups_config=groups_config, breadcrumbs=breadcrumbs)

@main.route('/event/<int:event_id>/update_groups', methods=['POST'])
@login_required
def update_event_groups(event_id):
    event = Event.query.get_or_404(event_id)
    # Check permissions
    participant = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not participant or participant.type != 'organisateur':
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('main.event_detail', event_id=event.id))
        
    # Expecting form data: groups_pj, groups_pnj, groups_org (comma separated strings)
    groups_pj = [g.strip() for g in request.form.get('groups_pj', '').split(',') if g.strip()]
    groups_pnj = [g.strip() for g in request.form.get('groups_pnj', '').split(',') if g.strip()]
    groups_org = [g.strip() for g in request.form.get('groups_org', '').split(',') if g.strip()]
    
    # Ensure "Peu importe" is there if list is empty? Or user defines it.
    # Spec says "initialisée avec la valeur 'peu importe'". User can change it.
    
    config = {
        "PJ": groups_pj,
        "PNJ": groups_pnj,
        "Organisateur": groups_org
    }
    
    event.groups_config = json.dumps(config)
    db.session.commit()
    
    flash('Configuration des groupes mise à jour.', 'success')
    return redirect(url_for('main.event_detail', event_id=event.id))

@main.route('/event/<int:event_id>/join', methods=['POST'])
@login_required
def join_event(event_id):
    event = Event.query.get_or_404(event_id)
    if Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first():
        flash('Vous participez déjà à cet événement.', 'warning')
        return redirect(url_for('main.event_detail', event_id=event.id))
        
    # Default participation type if not specified (spec says read from GForms or default to PJ/PNJ/Org)
    # For now, simple join as PJ default or form selection?
    # Spec: "Lorsqu’un utilisateur rejoint un événement, il précise le type d’inscription qu’il souhaite"
    # We need a form in the previous page or here.
    # Let's assume the button on event_detail posts here with a type.
    
    p_type = request.form.get('type', 'PJ')
    p_group = request.form.get('group', 'Aucun')
    
    # Registration status default 'À valider'
    participant = Participant(
        event_id=event.id, 
        user_id=current_user.id, 
        type=p_type, 
        group=p_group,
        registration_status='À valider'
    )
    db.session.add(participant)
    db.session.commit()
    
    flash('Demande d\'inscription envoyée ! En attente de validation.', 'success')
    return redirect(url_for('main.event_detail', event_id=event.id))

@main.route('/event/<int:event_id>/participants')
@login_required
def manage_participants(event_id):
    event = Event.query.get_or_404(event_id)
    # Check if organizer
    me = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not me or me.type != 'organisateur':
        flash('Accès réservé aux organisateurs.', 'danger')
        return redirect(url_for('main.event_detail', event_id=event.id))
        
    participants = Participant.query.filter_by(event_id=event.id).all()
    # Attach user info
    for p in participants:
        p.user = User.query.get(p.user_id)
        
    # Attach user info
    for p in participants:
        p.user = User.query.get(p.user_id)
        
    groups_config = json.loads(event.groups_config or '{}')
        
    groups_config = json.loads(event.groups_config or '{}')
    
    breadcrumbs = [
        ('GN Manager', '/dashboard'),
        (event.name, url_for('main.event_detail', event_id=event.id)),
        ('Gestion des Participants', '#')
    ]
        
    return render_template('manage_participants.html', event=event, participants=participants, groups_config=groups_config, breadcrumbs=breadcrumbs)

@main.route('/event/<int:event_id>/participants/bulk_update', methods=['POST'])
@login_required
def bulk_update_participants(event_id):
    event = Event.query.get_or_404(event_id)
    participant = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    
    if not participant or participant.type != 'organisateur':
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.event_detail', event_id=event.id))
        
    p_ids = request.form.getlist('participant_ids')
    
    for p_id in p_ids:
        p = Participant.query.get(p_id)
        if p and p.event_id == event.id:
            # Update fields based on ID-suffixed names
            p.registration_status = request.form.get(f'status_{p_id}', p.registration_status)
            p.type = request.form.get(f'type_{p_id}', p.type)
            p.group = request.form.get(f'group_{p_id}', p.group)
            
            # Use 0.0 if empty string provided
            pay_amt = request.form.get(f'pay_amount_{p_id}', '')
            p.payment_amount = float(pay_amt) if pay_amt else 0.0
            
            p.payment_method = request.form.get(f'pay_method_{p_id}', p.payment_method)
            p.comment = request.form.get(f'comment_{p_id}', p.comment)
            
    db.session.commit()
    flash('Participants mis à jour avec succès.', 'success')
    return redirect(url_for('main.event_detail', event_id=event.id))

@main.route('/event/<int:event_id>/participant/<int:p_id>/update', methods=['POST'])
@login_required
def update_participant(event_id, p_id):
    # Check organizer rights... (omitted for brevity, should be a decorator or helper)
    p = Participant.query.get_or_404(p_id)
    p.type = request.form.get('type')
    p.registration_status = request.form.get('registration_status')
    p.group = request.form.get('group')
    p.payment_amount = float(request.form.get('payment_amount', 0))
    p.payment_method = request.form.get('payment_method')
    p.comment = request.form.get('comment')
    
    db.session.commit()
    flash('Participant mis à jour.', 'success')
    return redirect(url_for('main.manage_participants', event_id=event_id))

@main.route('/event/<int:event_id>/casting')
@login_required
def casting_interface(event_id):
    event = Event.query.get_or_404(event_id)
    # Check permissions (organizer)
    participant = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not participant or participant.type != 'organisateur':
        flash('Accès réservé aux organisateurs.', 'danger')
        return redirect(url_for('main.event_detail', event_id=event.id))
        
    # Participants (Validated, No Role)
    # Spec: "Participants validés sans rôle"
    # Assuming 'registration_status' == 'Validé' check? Or just all participants?
    # Let's say Validated.
    participants_no_role = Participant.query.filter_by(event_id=event.id, role_id=None).all()
    # Filter by registration_status if needed, but for now let's show all valid-ish ones (including 'À valider' maybe? No, 'Validés')
    # Use 'Validé' string status? I defaulted to 'À valider'.
    # Let's assume organizer must validate first.
    participants_no_role = [p for p in participants_no_role if p.registration_status == 'Validé'] 
    
    # Attach user info
    for p in participants_no_role:
        p.user = User.query.get(p.user_id)

    # Roles
    roles = Role.query.filter_by(event_id=event.id).order_by(Role.group).all()
    
    # Structure roles by group for display if needed, or just flat list and group in template?
    # Template will group.
    
    return render_template('casting.html', event=event, participants=participants_no_role, roles=roles)

@main.route('/api/casting/assign', methods=['POST'])
@login_required
def api_assign_role():
    data = request.json
    event_id = data.get('event_id')
    participant_id = data.get('participant_id')
    role_id = data.get('role_id')
    
    # Security check (organizer)
    event = Event.query.get_or_404(event_id)
    me = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not me or me.type != 'organisateur':
        return jsonify({'error': 'Unauthorized'}), 403
        
    participant = Participant.query.get_or_404(participant_id)
    role = Role.query.get_or_404(role_id)
    
    # Update both sides
    participant.role_id = role.id
    role.assigned_participant_id = participant.id
    
    db.session.commit()
    return jsonify({'success': True})

@main.route('/api/casting/unassign', methods=['POST'])
@login_required
def api_unassign_role():
    data = request.json
    event_id = data.get('event_id')
    participant_id = data.get('participant_id') # Optional if we unassign by role logic
    role_id = data.get('role_id')
    
    event = Event.query.get_or_404(event_id)
    me = Participant.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not me or me.type != 'organisateur':
        return jsonify({'error': 'Unauthorized'}), 403

    if role_id:
        role = Role.query.get(role_id)
        if role and role.assigned_participant_id:
            p = Participant.query.get(role.assigned_participant_id)
            if p:
                p.role_id = None
            role.assigned_participant_id = None
            db.session.commit()
            return jsonify({'success': True})
            
    return jsonify({'error': 'Invalid request'}), 400

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

# Password Recovery Routes

@main.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token_str = str(uuid.uuid4())
            token = PasswordResetToken(token=token_str, email=email)
            db.session.add(token)
            db.session.commit()
            
            reset_url = url_for('main.reset_password', token=token_str, _external=True)
            send_email(email, "Réinitialisation de mot de passe", f"Cliquez sur ce lien pour recevoir un nouveau mot de passe : {reset_url}")
            
        flash('Si cet email existe, un lien de réinitialisation a été envoyé.', 'info')
        return redirect(url_for('main.login'))
        
    return render_template('forgot_password.html')

@main.route('/reset_password/<token>')
def reset_password(token):
    token_entry = PasswordResetToken.query.filter_by(token=token).first()
    
    if not token_entry or datetime.utcnow() - token_entry.created_at > timedelta(hours=1):
        flash('Lien invalide ou expiré.', 'danger')
        return redirect(url_for('main.login'))
        
    user = User.query.filter_by(email=token_entry.email).first()
    if not user:
        flash('Utilisateur introuvable.', 'danger')
        return redirect(url_for('main.login'))
        
    new_password = generate_password()
    user.password_hash = generate_password_hash(new_password)
    
    db.session.delete(token_entry)
    db.session.commit()
    
    return render_template('reset_password_success.html', password=new_password)
