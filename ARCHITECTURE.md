# Architecture et Organisation du Code - GNôle

## Vue d'ensemble

GNôle est une application Flask pour la gestion d'événements de Grandeur Nature (GN). L'application suit une architecture MVC (Model-View-Controller) classique.

## Structure des fichiers

### Fichiers principaux

- **`main.py`** : Point d'entrée de l'application
- **`app.py`** : Factory Flask, configuration de l'application
- **`routes.py`** : Définition de toutes les routes (Controller)
- **`models.py`** : Modèles de données SQLAlchemy (Model)
- **`auth.py`** : Utilitaires d'authentification et d'email
- **`extensions.py`** : Extensions Flask (db, login_manager)

### Routes par Domaine (routes/)
- `auth_routes.py` : Connexion, Inscription
- `event_routes.py` : Gestion événement, Casting, Participants
- `gforms_routes.py` : Intégration Google Forms (Webhook & UI)
- `admin_routes.py` : Administration globale
- `webhook_routes.py` : Point d'entrée des webhooks

### Scripts utilitaires

- **`fresh_deploy.py`** : Premier déploiement complet (remote via SSH uniquement)
- **`update_deploy.py`** : Mise à jour rapide du code (sans toucher à la BDD)
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
  - `event_detail.html` : Page détail d'un événement
  - `casting.html` : Page casting standalone (non utilisée actuellement)
  - **`partials/`** : Templates partiels inclus dans d'autres templates
    - `event_info.html` : Infos participant avec affichage conditionnel du rôle assigné
    - `event_organizer_tabs.html` : Onglets organisateur (Généralités, Groupes, Rôles, Casting, Participants)

### Statiques

- **`static/`** : Assets CSS, JS, images
  - `js/casting.js` : Logique de l'interface de casting (externalisé)
  - `js/event_organizer.js` : Gestion des onglets organisateur

## Modèles de données

### User
- Gestion des utilisateurs avec système de rôles (createur, sysadmin, user)
- Support du soft-delete (is_deleted) et du bannissement (is_banned)
- Authentification par email + mot de passe hashé

### Event
- Événements GN avec dates, description, lieu
- Statut manuel (pas d'automatisation)
- Configuration des groupes (PJ, PNJ, Organisateur) en JSON
- **`is_casting_validated`** : Boolean pour indiquer si le casting est validé (défaut: False)
- **`organizing_association`** : Nom de l'association organisatrice (String)
- **`display_organizers`** : Boolean pour afficher/masquer la liste des orgas (défaut: True)

### Role
- Rôles dans un événement
- **Type** : Organisateur, PJ ou PNJ
- Genre : Homme, Femme, Autre
- Groupe : lié au type (depuis la config des groupes de l'événement)
- Assignation à un participant (relation optionnelle)
- Support de documents Google Docs et PDF
- Commentaires internes (affichés en tooltip)

### Participant
- Liaison User ↔ Event
- Type (Organisateur, PJ, PNJ) et groupe
- Statut d'inscription (À valider, En attente, Validé, Rejeté)
- Informations de paiement

### CastingProposal
- Proposition de casting pour un événement
- **`name`** : Nom de la proposition
- **`position`** : Ordre d'affichage des colonnes
- Relation avec Event

### CastingAssignment
- Attribution d'un rôle à un participant dans une proposition
- **`proposal_id`** : Référence à CastingProposal
- **`role_id`** : Référence au rôle
- **`participant_id`** : Référence au participant assigné
- **`event_id`** : Référence à l'événement
- **`score`** : Note de 0 à 10 (optionnel)

### AccountValidationToken
- Tokens pour la validation des nouveaux comptes
- Expire après 24h

### PasswordResetToken
- Tokens pour la réinitialisation de mot de passe
- Expire après 1h

### GForms Integration
Modèles dédiés au stockage structuré des réponses Google Forms.

#### GFormsCategory
- Catégories pour trier les champs (ex: "HRP", "Généralités")
- **`color`** : Code couleur pour l'affichage (blue, red, green...)
- **`position`** : Ordre de tri

#### GFormsFieldMapping
- Association entre un champ du formulaire (nom exact) et une catégorie
- Permet l'auto-catégorisation des nouvelles soumissions

#### GFormsSubmission
- Stockage d'une soumission complète
- **`raw_data`** : JSON complet des réponses
- **`type_ajout`** : "créé" (nouveau user), "ajouté" (participant seul), "mis à jour"
- Relation vers `FormResponse` (stockage brut historique)

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

## Système de Casting

### Fonctionnalités
- **Attribution principale** : Colonne par défaut pour attribuer les participants aux rôles
- **Propositions** : Colonnes additionnelles pour différentes versions de casting
- **Scores (0-10)** : Note attribuée à chaque assignation dans les propositions
- **Validation** : Switch "Validé/Non-validé" persistant en base
- **Attribution Automatique** : Utilise l'algorithme Hongrois (Kuhn-Munkres) pour maximiser le score global des attributions.

### Routes API (event_routes.py)
| Route | Méthode | Description |
|-------|---------|-------------|
| `/event/<id>/casting_data` | GET | Données de casting (participants, propositions, assignations) |
| `/event/<id>/casting/assign` | POST | Assigner un participant à un rôle |
| `/event/<id>/casting/add_proposal` | POST | Créer une nouvelle proposition |
| `/event/<id>/casting/delete_proposal` | POST | Supprimer une proposition |
| `/event/<id>/casting/toggle_validation` | POST | Basculer l'état de validation du casting |
| `/event/<id>/casting/update_score` | POST | Mettre à jour le score d'une assignation |

### Affichage conditionnel (event_info.html)
Quand `is_casting_validated` est `True` :
- Le nom du personnage assigné est affiché sous forme de badge noir
- Un lien vers la fiche PDF du rôle est affiché (ou "bientôt disponible...")

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

### Scripts disponibles

| Script | Usage |
|--------|-------|
| `fresh_deploy.py` | Premier déploiement complet |
| `update_deploy.py` | Mise à jour rapide du code |
| `manage_db.py` | Gestion de la base de données (import/export/reset) |

### Premier déploiement (fresh_deploy.py)
```bash
export GNMANAGER_USER=utilisateur
export GNMANAGER_PWD=motdepasse
uv run python fresh_deploy.py
```

Nouvelles options :
- `--copy-db` : Synchronise la base de données locale vers le distant
- `--systemd` : Gère le service systemd

### Mise à jour du code (update_deploy.py)
```bash
uv run python update_deploy.py
```

Le script :
1. Se connecte via SSH au serveur
2. Arrête le service systemd
3. Crée et upload une archive des fichiers Git
4. Extrait l'archive sur le serveur
5. Redémarre le service systemd

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
- **NumPy & SciPy** : Calculs matriciels pour l'algorithme d'optimisation de casting

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
# Supprimer et réimporter depuis les CSV de test
rm instance/gnmanager.db
uv run python manage_db.py import -f config/ --clean

# Ou réinitialiser la base en gardant un admin spécifique
uv run python manage_db.py reset --keep-email ton-email@gmail.com

# Ou avec seed_data.py pour générer de nouvelles données
uv run python seed_data.py
```

### Migrations de base de données (Flask-Migrate/Alembic)

Le projet utilise Flask-Migrate pour gérer les évolutions de schéma.

```bash
# Appliquer les migrations en attente
uv run flask db upgrade

# Créer une nouvelle migration après modification de models.py
uv run flask db migrate -m "Description de la migration"

# Voir l'historique des migrations
uv run flask db history

# Rétrograder à la version précédente
uv run flask db downgrade
```

**Migrations existantes :**
- `7f2f95249844` : Migration initiale (Nettoyage Schema & Initialisation)

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
