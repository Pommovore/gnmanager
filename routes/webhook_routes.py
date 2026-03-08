import os
import json
import logging
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from models import db, FormResponse, Event, User, Participant, Role, GFormsSubmission, GFormsCategory, GFormsFieldMapping, EventNotification
from extensions import csrf
from flask_login import login_required
from decorators import organizer_required
from werkzeug.security import generate_password_hash
import secrets
from constants import RegistrationStatus, ParticipantType
from services.email_service import send_new_account_invitation

# Création du Blueprint
webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)

def verify_token():
    """
    Vérifie le token d'authentification dans le header Authorization.
    Retourne l'objet Event correspondant si valide, sinon None.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        # Compatibility/Legacy check using env var if header missing? No, enforce header.
        return None
    
    # Format attendu: "Bearer <token>"
    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return None
        
    # Vérification contre la base de données (Event.webhook_secret)
    event = Event.query.filter_by(webhook_secret=token).first()
    
    if event:
        return event
        
    # Fallback legacy (env var) si besoin, mais on passe au per-event.
    return None

@webhook_bp.route('/api/webhook/gform', methods=['POST'])
@csrf.exempt
def gform_webhook():
    """
    Endpoint pour recevoir les données de Google Forms via Apps Script.
    Attend un JSON:
    {
      "responseId": "...",
      "formId": "...", (optionnel)
      "email": "...", (optionnel)
      "timestamp": "...",
      "answers": { ... }
    }
    """
    # 1. Sécurité
    event = verify_token()
    if not event:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400
            
        response_id = data.get('responseId')
        if not response_id:
            return jsonify({"error": "Missing responseId"}), 400
            
        # 2. Upsert Logic (FormResponse - Legacy)
        form_response = FormResponse.query.filter_by(response_id=response_id).first()
        
        if form_response:
            # Update
            logger.info(f"Updating FormResponse {response_id}")
            form_response.answers = json.dumps(data.get('answers', {}))
            form_response.respondent_email = data.get('email')
            form_response.form_id = data.get('formId') # Mettre à jour le form_id au cas où
            form_response.updated_at = datetime.utcnow()
            action = "updated"
        else:
            # Insert
            logger.info(f"Creating new FormResponse {response_id}")
            form_response = FormResponse(
                response_id=response_id,
                form_id=data.get('formId'),
                event_id=event.id,
                respondent_email=data.get('email'),
                answers=json.dumps(data.get('answers', {})),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(form_response)
            action = "created"
            
        db.session.flush() # Ensure ID is available
            
        # ---------------------------------------------------------
        # Nouvelle logique : Inscription/Mise à jour du Participant
        # ---------------------------------------------------------
        email = data.get('email')
        answers = data.get('answers', {})
        
        # Tentative d'extraire l'email depuis les réponses si non fourni par Google Forms
        if not email and isinstance(answers, dict):
            for k, v in answers.items():
                k_lower = k.lower().strip()
                if 'e-mail' in k_lower or 'email' in k_lower or 'courriel' in k_lower:
                    if isinstance(v, str) and '@' in v:
                        email = v.strip()
                        break
                        
        if not email:
            email = ""
            
        user = None
        participant = None
        type_ajout = "anonyme"
        
        if email:
            logger.info(f"Processing email: {email}") # DEBUG LOG
            # 1. Identifier ou Créer l'Utilisateur
            user = User.query.filter_by(email=email).first()
            if not user:
                logger.info(f"Creating new User for email {email}")
                type_ajout = "créé"
                # Mot de passe aléatoire (l'utilisateur devra le reset)
                temp_password = secrets.token_urlsafe(12)
                user = User(
                    email=email,
                    nom="Utilisateur", # Placeholder
                    prenom="GForm",    # Placeholder
                    password_hash=generate_password_hash(temp_password),
                    role='user',
                    is_banned=False,
                    is_deleted=False
                )
                db.session.add(user)
                db.session.flush() # Pour avoir l'ID
            else:
                 logger.info(f"Found existing User ID: {user.id}") # DEBUG LOG
                 type_ajout = "ajouté" # Par défaut si user existe
            
            # 2. Identifier ou Créer le Participant
            participant = Participant.query.filter_by(user_id=user.id, event_id=event.id).first()
            if not participant:
                logger.info(f"Registering User {user.id} to Event {event.id}")
                participant = Participant(
                    user_id=user.id,
                    event_id=event.id,
                    type=ParticipantType.PJ.value, # Défaut
                    registration_status=RegistrationStatus.TO_VALIDATE.value, # "À valider"
                    role_communicated=False,
                    role_received=False
                )
                db.session.add(participant)
                db.session.flush()
            else:
                 logger.info(f"Found existing Participant ID: {participant.id}") # DEBUG LOG
                 type_ajout = "mis à jour" # Si participant existe déjà
            
            # 3. Traitement de l'identité (Nom/Prénom)
            nom_form = None
            prenom_form = None

            # Chercher dans les réponses
            if isinstance(answers, dict):
                for key, val in answers.items():
                    key_lower = key.lower().strip()
                    if key_lower in ['nom', 'nom de famille', 'family name', 'lastname', 'last name']:
                        nom_form = str(val).strip()
                    elif key_lower in ['prénom', 'prenom', 'first name', 'firstname']:
                        prenom_form = str(val).strip()
            
            # Heuristique si non trouvé
            if not nom_form or not prenom_form:
                email_part = email.split('@')[0]
                if '.' in email_part:
                    parts = email_part.split('.')
                    if not prenom_form: prenom_form = parts[0].capitalize()
                    if not nom_form: nom_form = " ".join(parts[1:]).capitalize()
                else:
                    if not prenom_form: prenom_form = email_part.capitalize()
                    if not nom_form: nom_form = "Utilisateur"

            # Mise à jour de l'utilisateur
            if prenom_form: user.prenom = prenom_form
            if nom_form: user.nom = nom_form
            
            # 4. Création d'une Notification (uniquement pour les nouveaux ou ajouts)
            if type_ajout in ["créé", "ajouté"]:
                notif = EventNotification(
                    event_id=event.id,
                    user_id=user.id,
                    action_type="participant_join_request", # Utilisation d'un type existant pour compatibilité
                    description=f"Nouvelle inscription via Google Form: {user.prenom} {user.nom} ({email})",
                    created_at=datetime.utcnow(),
                    is_read=False
                )
                db.session.add(notif)
                
                # Envoi email d'invitation si activé
                if type_ajout == "créé" and event.auto_invite_email:
                    # On doit committer l'utilisateur avant d'envoyer l'email car le token a besoin de l'user_id ?
                    # Non, token a juste besoin de l'email.
                    # Mais s'il clique sur le lien, il faut que l'user soit en base.
                    # On flush de nouveau pour être sûr.
                    db.session.flush()
                    
                    # On ne veut pas bloquer le webhook si l'email échoue, donc on log juste l'erreur dans le service
                    # Idéalement faudrait faire ça en async/background, mais ici on fait synchrone pour l'instant
                    try:
                        send_new_account_invitation(user, event)
                    except Exception as e:
                        logger.error(f"Failed to send invitation email: {e}")

        # ---------------------------------------------------------
        # Nouvelle logique : GFormsSubmission & Field Mappings
        # ---------------------------------------------------------
        
        # 1. Créer/Mettre à jour GFormsSubmission
        g_submission = GFormsSubmission.query.filter_by(form_response_id=form_response.id).first()
        if not g_submission and email:
            g_submission = GFormsSubmission.query.filter_by(event_id=event.id, email=email).first()
            
        if not g_submission:
             g_submission = GFormsSubmission(
                event_id=event.id,
                user_id=user.id if user else None,
                email=email,
                timestamp=datetime.utcnow(),
                type_ajout=type_ajout,
                form_response_id=form_response.id,
                raw_data=json.dumps(answers)
            )
             db.session.add(g_submission)
        else:
            # Merge logic: replace only if new data is not empty
            try:
                current_data = json.loads(g_submission.raw_data) if g_submission.raw_data else {}
            except:
                current_data = {}
            
            if isinstance(answers, dict):
                for key, val in answers.items():
                    # We only ignore None. We must allow empty strings and empty lists
                    # because a user might delete an answer when updating their form.
                    if val is not None:
                        current_data[key] = val
                        
            g_submission.raw_data = json.dumps(current_data)
            g_submission.type_ajout = type_ajout
            g_submission.timestamp = datetime.utcnow()
            g_submission.form_response_id = form_response.id # Lier à la dernière réponse
            if not g_submission.user_id and user:
                g_submission.user_id = user.id
            if email and not g_submission.email:
                g_submission.email = email
        
        # 2. Auto-detect fields and create mappings
        if isinstance(answers, dict):
            # Récupérer la catégorie par défaut (insensible à la casse)
            default_cat = GFormsCategory.query.filter(
                GFormsCategory.event_id == event.id,
                db.func.lower(GFormsCategory.name) == 'généralités'
            ).first()
            if not default_cat:
                # Default creation should use nice capitalization
                default_cat = GFormsCategory(event_id=event.id, name='Généralités', color='neutral', position=0)
                db.session.add(default_cat)
                db.session.flush()
            
            existing_mappings = {m.field_name for m in GFormsFieldMapping.query.filter_by(event_id=event.id).all()}
            
            for field_name in answers.keys():
                if field_name not in existing_mappings:
                    new_mapping = GFormsFieldMapping(
                        event_id=event.id,
                        field_name=field_name,
                        category_id=default_cat.id
                    )
                    db.session.add(new_mapping)
                    existing_mappings.add(field_name) # Avoid duplicates in same transaction

        db.session.commit()
        logger.info("Transaction committed successfully")

        # ---------------------------------------------------------
        # Notification Discord
        # ---------------------------------------------------------
        if event.discord_webhook_url: 
             try:
                from services.discord_service import send_discord_notification
                
                # Préparer les champs pour Discord
                discord_fields = []
                # Limiter le nombre de champs pour éviter les limites Discord
                if isinstance(answers, dict):
                    for i, (q, a) in enumerate(answers.items()):
                        if i >= 20: break
                        val_str = str(a) if a is not None else ""
                        if len(val_str) > 1024:
                            val_str = val_str[:1021] + "..."
                        
                        discord_fields.append({
                            "name": q[:256],
                            "value": val_str,
                            "inline": False 
                        })
                
                user_data = {
                    'nom': user.nom if user else "Inconnu",
                    'prenom': user.prenom if user else "GForm Anonyme",
                    'email': email if email else "anonyme@gform.com"
                }
                
                send_discord_notification(
                    webhook_url=event.discord_webhook_url,
                    event_name=event.name,
                    user_data=user_data,
                    registration_type="Inscription via Google Form",
                    extra_fields=discord_fields
                )
             except Exception as e_discord:
                 logger.error(f"Failed to send Discord notification: {e_discord}")

        return jsonify({
            "status": "success", 
            "action": action, 
            "id": form_response.id,
            "user_processed": bool(email)
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Webhooks et routes pour l'analyse des traits de caractère
# ============================================================================

def _find_role_by_id_texte(id_texte):
    """
    Retrouve un rôle à partir de son id_texte (format hyphen-separated).
    Format attendu : "NomSanitisé-RoleID-EventID-AppRoot"
    """
    parts = id_texte.split('-')
    if len(parts) >= 2:
        # Comme NomSanitisé ne contient pas de '-' (via _sanitize_id_texte),
        # parts[1] est le RoleID.
        try:
            role_id = int(parts[1])
            return Role.query.get(role_id)
        except (ValueError, IndexError):
            pass

    return None


@webhook_bp.route('/webhook/pdf2txt', methods=['POST'])
@csrf.exempt
def webhook_pdf2txt():
    """
    Callback du service pdf2txt.
    Reçoit le résultat de l'extraction PDF → texte.
    En cas de succès, lance automatiquement l'analyse des traits de caractère.
    """
    try:
        # Log brut de la requête entrante
        # Masquer les headers sensibles dans les logs
        safe_headers = {k: ('***' if k.lower() in ('authorization', 'token', 'cookie') else v)
                        for k, v in request.headers}

        logger.info(f"📥 ═══ WEBHOOK PDF2TXT REÇU ═══")
        logger.info(f"   Method:       {request.method}")
        logger.info(f"   Content-Type: {request.content_type}")
        logger.info(f"   Headers:      {dict(safe_headers)}")
        logger.info(f"   Raw Body:     {request.get_data(as_text=True)[:1000]}")

        data = request.get_json(force=True)
        if not data:
            logger.error("❌ Webhook pdf2txt: aucun payload JSON reçu")
            return jsonify({"error": "No JSON payload"}), 400

        logger.info(f"   Parsed JSON:  {json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")

        etat = data.get('etat', '')
        id_texte = data.get('id_texte', '')

        logger.info(f"   etat='{etat}', id_texte='{id_texte}'")
        logger.info(f"   Clés reçues:  {list(data.keys())}")

        # Retrouver le rôle correspondant
        role = _find_role_by_id_texte(id_texte)
        if not role:
            logger.warning(f"⚠️  Aucun rôle trouvé pour id_texte='{id_texte}'")
            return jsonify({"error": f"Rôle introuvable pour id_texte={id_texte}"}), 404

        logger.info(f"   Rôle trouvé:  '{role.name}' (id={role.id}, event_id={role.event_id})")

        # Ignorer si l'analyse a été annulée
        if role.character_traits_status == 'cancelled':
            logger.info(f"⏭️  Webhook pdf2txt ignoré pour '{role.name}': analyse annulée")
            return jsonify({"status": "ignored", "reason": "cancelled"}), 200

        if etat == 'succès':
            text_url = data.get('url', '')
            extrait = data.get('extrait', '')
            logger.info(f"✅ Extraction PDF réussie pour '{role.name}'")
            logger.info(f"   URL texte:    {text_url}")
            logger.info(f"   Extrait:      {extrait[:200]}")

            # Passer en statut 'pending_character' (icône bleue)
            role.character_traits_status = 'pending_character'
            db.session.commit()

            # Lancer l'étape 2 : analyse des traits de caractère
            from services.character_service import request_character_analysis
            success, message = request_character_analysis(text_url, id_texte)

            if not success:
                role.character_traits_status = 'error'
                role.character_traits_data = json.dumps({
                    'error': f"Échec du lancement de l'analyse des traits: {message}"
                })
                db.session.commit()
                logger.error(f"❌ Échec du lancement de l'analyse character pour '{role.name}': {message}")

        elif etat == 'échec':
            erreur = data.get('erreur', 'Erreur inconnue')
            role.character_traits_status = 'error'
            role.character_traits_data = json.dumps({
                'error': f"Échec de l'extraction PDF: {erreur}"
            })
            db.session.commit()
            logger.error(f"❌ Extraction PDF échouée pour '{role.name}': {erreur}")

        else:
            logger.warning(f"⚠️  Webhook pdf2txt: état inconnu '{etat}' pour '{role.name}'")
            logger.warning(f"   Payload complet: {json.dumps(data, ensure_ascii=False)}")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"❌ Erreur webhook pdf2txt: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@webhook_bp.route('/webhook/character', methods=['POST'])
@csrf.exempt
def webhook_character():
    """
    Callback du service character.
    Reçoit le résultat de l'analyse des traits de caractère.
    Télécharge le JSON des traits depuis result_url en cas de succès.
    """
    try:
        # Log brut de la requête entrante
        # Masquer les headers sensibles dans les logs
        safe_headers = {k: ('***' if k.lower() in ('authorization', 'token', 'cookie') else v)
                        for k, v in request.headers}

        logger.info(f"📥 ═══ WEBHOOK CHARACTER REÇU ═══")
        logger.info(f"   Method:       {request.method}")
        logger.info(f"   Content-Type: {request.content_type}")
        logger.info(f"   Headers:      {dict(safe_headers)}")
        logger.info(f"   Raw Body:     {request.get_data(as_text=True)[:1000]}")

        data = request.get_json(force=True)
        if not data:
            logger.error("❌ Webhook character: aucun payload JSON reçu")
            return jsonify({"error": "No JSON payload"}), 400

        logger.info(f"   Parsed JSON:  {json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")

        status = data.get('status', '')
        request_id = data.get('request_id', '')

        logger.info(f"   status='{status}', request_id='{request_id}'")
        logger.info(f"   Clés reçues:  {list(data.keys())}")

        # Retrouver le rôle correspondant
        role = _find_role_by_id_texte(request_id)
        if not role:
            logger.warning(f"⚠️  Aucun rôle trouvé pour request_id='{request_id}'")
            return jsonify({"error": f"Rôle introuvable pour request_id={request_id}"}), 404

        logger.info(f"   Rôle trouvé:  '{role.name}' (id={role.id}, event_id={role.event_id})")

        # Ignorer si l'analyse a été annulée
        if role.character_traits_status == 'cancelled':
            logger.info(f"⏭️  Webhook character ignoré pour '{role.name}': analyse annulée")
            return jsonify({"status": "ignored", "reason": "cancelled"}), 200

        if status == 'completed':
            result_url = data.get('result_url', '')
            logger.info(f"✅ Analyse character réussie pour '{role.name}'")
            logger.info(f"   Result URL:   {result_url}")

            # Télécharger le JSON des traits depuis result_url
            try:
                import requests as http_requests
                logger.info(f"   ─── TÉLÉCHARGEMENT RESULT_URL ───")
                logger.info(f"   GET {result_url}")
                resp = http_requests.get(result_url, timeout=15)
                logger.info(f"   Status:       {resp.status_code}")
                logger.info(f"   Body:         {resp.text[:1000]}")

                if resp.status_code == 200:
                    traits_data = resp.json()
                    role.character_traits_status = 'success'
                    role.character_traits_data = json.dumps(traits_data)
                    db.session.commit()
                    logger.info(f"✅ Traits sauvegardés pour '{role.name}': "
                                f"{json.dumps(traits_data, ensure_ascii=False)[:500]}")
                else:
                    error_msg = f"Erreur téléchargement traits: HTTP {resp.status_code}"
                    role.character_traits_status = 'error'
                    role.character_traits_data = json.dumps({'error': error_msg})
                    db.session.commit()
                    logger.error(f"❌ {error_msg} pour '{role.name}'")
            except Exception as e_download:
                role.character_traits_status = 'error'
                role.character_traits_data = json.dumps({
                    'error': f"Erreur téléchargement résultat: {str(e_download)}"
                })
                db.session.commit()
                logger.error(f"❌ Erreur téléchargement traits pour '{role.name}': {e_download}",
                             exc_info=True)

        elif status == 'failed':
            error_msg = data.get('error', 'Erreur inconnue')
            role.character_traits_status = 'error'
            role.character_traits_data = json.dumps({'error': error_msg})
            db.session.commit()
            logger.error(f"❌ Analyse character échouée pour '{role.name}': {error_msg}")

        else:
            logger.warning(f"⚠️  Webhook character: statut inconnu '{status}' pour '{role.name}'")
            logger.warning(f"   Payload complet: {json.dumps(data, ensure_ascii=False)}")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"❌ Erreur webhook character: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Routes de déclenchement et statut de l'analyse
# ============================================================================

@webhook_bp.route('/event/<int:event_id>/role/<int:role_id>/analyze_traits', methods=['POST'])
@login_required
@organizer_required
@csrf.exempt
def analyze_traits(event_id, role_id):
    """
    Déclenche l'analyse des traits de caractère pour un rôle.
    Vérifie que le rôle a un pdf_url, puis lance l'extraction PDF.
    Accès réservé aux organisateurs.
    """
    role = Role.query.filter_by(id=role_id, event_id=event_id).first()
    if not role:
        return jsonify({"error": "Rôle introuvable"}), 404

    if not role.pdf_url:
        return jsonify({"error": "Aucun PDF associé à ce rôle"}), 400

    # Vérifier qu'une analyse n'est pas déjà en cours
    if role.character_traits_status in ('pending_pdf', 'pending_character'):
        return jsonify({"error": "Une analyse est déjà en cours pour ce rôle"}), 409

    # Mettre le statut à pending_pdf AVANT l'appel API pour éviter la race condition
    role.character_traits_status = 'pending_pdf'
    role.character_traits_data = None
    db.session.commit()

    # Lancer l'extraction PDF (étape 1)
    from services.character_service import request_pdf_extraction
    success, message = request_pdf_extraction(role)

    if success:
        logger.info(f"🚀 Analyse des traits lancée pour '{role.name}' (event_id={event_id})")
        return jsonify({"success": True, "message": message}), 200
    else:
        # Rollback du statut en cas d'échec de l'appel API
        role.character_traits_status = 'error'
        role.character_traits_data = json.dumps({'error': message})
        db.session.commit()
        logger.error(f"❌ Échec du lancement de l'analyse pour '{role.name}': {message}")
        return jsonify({"error": message}), 500



@webhook_bp.route('/event/<int:event_id>/role/<int:role_id>/cancel_traits', methods=['POST'])
@login_required
@organizer_required
@csrf.exempt
def cancel_traits(event_id, role_id):
    """
    Annule l'analyse des traits de caractère en cours pour un rôle.
    Met le statut à 'cancelled' pour que les webhooks futurs soient ignorés.
    """
    role = Role.query.filter_by(id=role_id, event_id=event_id).first()
    if not role:
        return jsonify({"error": "Rôle introuvable"}), 404

    if role.character_traits_status not in ('pending_pdf', 'pending_character'):
        return jsonify({"error": "Aucune analyse en cours pour ce rôle"}), 409

    previous_status = role.character_traits_status
    role.character_traits_status = 'cancelled'
    role.character_traits_data = None
    db.session.commit()

    logger.info(f"🛑 Analyse annulée pour '{role.name}' "
                f"(event_id={event_id}, ancien statut={previous_status})")
    return jsonify({"success": True, "message": "Analyse annulée"}), 200

