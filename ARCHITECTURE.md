# Architecture et Organisation du Code - GN Manager

## Vue d'ensemble

GN Manager est une application Flask pour la gestion d'événements de Grandeur Nature (GN). L'application suit une architecture MVC (Model-View-Controller) classique.

## Structure des fichiers

### Fichiers principaux

- **`main.py`** : Point d'entrée de l'application
- **`app.py`** : Factory Flask, configuration de l'application
- **`routes.py`** : Définition de toutes les routes (Controller)
- **`models.py`** : Modèles de données SQLAlchemy (Model)
- **`auth.py`** : Utilitaires d'authentification et d'email
- **`extensions.py`** : Extensions Flask (db, login_manager)

### Scripts utilitaires

- **`deploy.py`** : Script de déploiement (local et distant via SSH)
- **`manage_db.py`** : Import/Export de données (JSON et CSV)
- **`seed_data.py`** : Génération de données de test complet avec export CSV auto

### Configuration

- **`pyproject.toml`** : Dépendances Python (géré par `uv`)
- **`config/deploy_config.yaml`** : Configuration de déploiement
- **`.env`** : Variables d'environnement (généré par deploy.py)

### Templates

- **`templates/`** : Templates Jinja2 (View)
  - `base.html` : Template de base
  - `login.html`, `register.html`, `set_password.html` : Authentification
  - `dashboard.html` : Tableau de bord principal
  - Autres templates pour les événements, rôles, etc.

### Statiques

- **`static/`** : Assets CSS, JS, images

## Modèles de données

### User
- Gestion des utilisateurs avec système de rôles (createur, sysadmin, user)
- Support du soft-delete (is_deleted) et du bannissement (is_banned)
- Authentification par email + mot de passe hashé

### Event
- Événements GN avec dates, description, lieu
- Statut manuel (pas d'automatisation)
- Configuration des groupes (PJ, PNJ, Organisateur) en JSON

### Role
- Rôles dans un événement
- Assignation à un participant (relation optionnelle)
- Support de documents Google Docs et PDF

### Participant
- Liaison User ↔ Event
- Type (Organisateur, PJ, PNJ) et groupe
- Statut d'inscription (À valider, En attente, Validé, Rejeté)
- Informations de paiement

### AccountValidationToken
- Tokens pour la validation des nouveaux comptes
- Expire après 24h

### PasswordResetToken
- Tokens pour la réinitialisation de mot de passe
- Expire après 1h

## Flux d'authentification

### Inscription (Register)
1. Utilisateur remplit le formulaire
2. Vérification que l'email n'existe pas déjà
3. Création du user (sans password_hash) et du token
4. **Envoi d'email AVANT commit en base**
5. Si email OK → commit et redirection vers login
6. Si email KO → annulation (pas de commit)

### Validation de compte
1. Utilisateur clique sur le lien dans l'email
2. Vérification du token (validité + expiration)
3. Définition du mot de passe
4. Activation du compte (password_hash défini)
5. Suppression du token

### Connexion (Login)
1. Vérification de l'existence de l'utilisateur
2. Vérification que le compte n'est pas deleted/banned
3. Vérification que le compte est validé (password_hash != None)
4. Vérification du mot de passe
5. Connexion via Flask-Login

## Système de rôles (RBAC)

### Rôles disponibles
- **createur** : Accès total, peut promouvoir/rétrograder n'importe qui
- **sysadmin** : Accès admin, ne peut pas toucher aux créateurs
- **user** : Utilisateur standard

### Règles de sécurité
- Un sysadmin ne peut pas promouvoir quelqu'un en createur
- Un sysadmin ne peut pas supprimer/modifier un createur
- Un utilisateur ne peut pas se supprimer lui-même

## Envoi d'email

### Configuration
Variables d'environnement requises (dans `.env`) :
- `MAIL_SERVER` : smtp-relay.brevo.com
- `MAIL_PORT` : 587
- `MAIL_USERNAME` : Identifiant SMTP
- `MAIL_PASSWORD` : Mot de passe SMTP
- `MAIL_DEFAULT_SENDER` : Email expéditeur
- `MAIL_USE_TLS` : true

### Utilisation
```python
from auth import send_email

success = send_email(
    to="user@example.com",
    subject="Sujet",
    body="<p>Corps HTML</p>"
)
```

La fonction retourne `True` si l'envoi a réussi, `False` sinon.

## Déploiement

### Local
```bash
uv run python deploy.py --reset-db --import-data
```

### Distant (via SSH)
```bash
uv run python deploy.py --reset-db --import-data \
  --admin-email 'admin@example.com' \
  --admin-password 'password' \
  --admin-nom 'Nom' \
  --admin-prenom 'Prenom'
```

Le script :
1. Se connecte via SSH au serveur
2. Arrête le service systemd
3. Upload les fichiers
4. Exécute `uv sync` pour installer les dépendances
5. Génère et upload le fichier `.env`
6. Optionnellement reset la DB et import les données
7. Redémarre le service systemd

### Service systemd
Fichier : `/etc/systemd/system/gnmanager.service`

Le service :
- Utilise `EnvironmentFile=/opt/gnmanager/.env`
- Lance l'app via `.venv/bin/python main.py`
- Logs dans `/opt/gnmanager/app.log`
- Redémarrage automatique en cas de crash

## Bonnes pratiques

### Commits de base de données
- Toujours utiliser `try/except` avec `db.session.commit()`
- Faire `db.session.rollback()` en cas d'erreur
- Pour les opérations critiques (email), commit APRÈS vérification

### Sécurité
- Ne jamais exposer les mots de passe en clair dans les logs
- Utiliser `generate_password_hash` de Werkzeug
- Vérifier les permissions avant toute action admin
- Valider les entrées utilisateur

### Logs
- Utiliser `print(..., flush=True)` pour forcer l'écriture immédiate
- Messages clairs et préfixés : `[EMAIL]`, `[ERROR]`, etc.
- Éviter les logs de debug en production (nettoyés ici)

### URLs publiques
Pour les développements locaux et distants, utiliser :
```python
if os.environ.get('APP_PUBLIC_HOST'):
    url = f"http://{os.environ['APP_PUBLIC_HOST']}{endpoint}"
else:
    url = url_for('route', _external=True)
```

## Dépendances principales

- **Flask** : Framework web
- **Flask-Login** : Gestion des sessions
- **Flask-SQLAlchemy** : ORM
- **Werkzeug** : Hashage de mots de passe
- **python-dotenv** : Chargement des variables d'environnement
- **Paramiko** : Connexions SSH pour le déploiement
- **PyYAML** : Parsing de la config de déploiement

## Variables d'environnement

### Application
- `FLASK_HOST` : Hôte (défaut: 0.0.0.0)
- `FLASK_PORT` : Port (défaut: 5000)
- `APP_PUBLIC_HOST` : Host public pour les URLs externes

### Email
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`
- `MAIL_DEFAULT_SENDER`, `MAIL_USE_TLS`

### Système
- `PYTHONUNBUFFERED=1` : Forcer stdout non bufferisé

## Tests

Pour tester l'envoi d'email en local :
1. Configurer `.env` avec vos credentials Brevo
2. Lancer l'app : `uv run python main.py`
3. S'inscrire via `/register`
4. Vérifier la réception de l'email

## Maintenance

### Reset de la base de données
```bash
# Réinitialisation via le script de déploiement (recommandé)
uv run python deploy.py --create-test-db

# Ou manuellement via manage_db.py
rm instance/gnmanager.db
uv run python manage_db.py import -f config/ --clean
```

### Consultation des logs (serveur distant)
```bash
# Logs du service
journalctl -u gnmanager.service -f

# Logs de l'application
cat /opt/gnmanager/app.log
tail -f /opt/gnmanager/app.log
```

### Redémarrage du service
```bash
sudo systemctl restart gnmanager.service
sudo systemctl status gnmanager.service
```
