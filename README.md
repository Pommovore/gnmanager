# GN Manager

Application web de gestion pour les événements de Grandeur Nature (GN).

## 🎯 Fonctionnalités

### Gestion des utilisateurs
- **Inscription avec validation par email** (via Brevo SMTP)
- **Système de rôles hiérarchiques** : Créateur, Admin (Sysadmin), Utilisateur
- Soft-delete et bannissement
- Reset de mot de passe par email

### Gestion des événements
- Création et édition d'événements
- Statuts manuels personnalisables
- Visibilité publique/privée
- Configuration de groupes (PJ, PNJ, Organisateur)
- Upload d'images de fond

### Gestion des rôles et inscriptions
- Création de rôles pour chaque événement
- Inscription des participants
- Validation des inscriptions
- Attribution des rôles (casting)
- Interface drag & drop (SortableJS)

### Administration
- Tableau de bord complet
- Gestion des utilisateurs (création, édition, suppression)
- Gestion des statuts et permissions
- Vue d'ensemble des événements

## 📋 Prérequis

- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)** pour la gestion des dépendances
- **SQLite** (inclus avec Python)
- **Compte Brevo** pour l'envoi d'emails (optionnel pour le développement local)

## 🚀 Installation et Déploiement

### Configuration

1. Copiez le template de configuration :
   ```bash
   cp config/deploy_config_template.yaml config/deploy_config.yaml
   ```

2. Éditez `config/deploy_config.yaml` :
   ```yaml
   location: local  # ou 'remote' pour déploiement distant

   deploy:
     machine_name: "0.0.0.0"        # Pour local, ou domaine/IP pour distant
     port: 5000
     target_directory: "./"

   email:
     server: "smtp-relay.brevo.com"
     port: 587
     use_tls: true
     username: "votre_username_smtp"
     password: "votre_password_smtp"
     default_sender: "votre@email.com"

   admin:
     email: "admin@example.com"
     password: "motdepasse"
     nom: "Nom"
     prenom: "Prenom"
   ```

### Déploiement Local

```bash
# Installation des dépendances et lancement
uv run python deploy.py --reset-db --import-data \
  --admin-email 'admin@example.com' \
  --admin-password 'password' \
  --admin-nom 'Dupont' \
  --admin-prenom 'Jean'
```

L'application sera accessible sur `http://localhost:5000`

### Déploiement Distant (via SSH et systemd)

1. Configurez `deploy_config.yaml` avec `location: remote`

2. Définissez les identifiants SSH :
   ```bash
   export GNMANAGER_USER=votre_utilisateur
   export GNMANAGER_PWD=votre_mot_de_passe
   ```

3. Lancez le déploiement :
   ```bash
   uv run python deploy.py --reset-db --import-data \
     --admin-email 'admin@example.com' \
     --admin-password 'password' \
     --admin-nom 'Dupont' \
     --admin-prenom 'Jean'
   ```

Le script va :
- Se connecter au serveur via SSH
- Arrêter le service systemd
- Transférer les fichiers via SFTP
- Installer les dépendances (`uv sync`)
- Générer le fichier `.env` avec la configuration
- Réinitialiser la base de données (si `--reset-db`)
- Importer les données de test (si `--import-data`)
- Redémarrer le service systemd

### Service systemd

Le déploiement distant utilise systemd pour gérer l'application :

```bash
# Vérifier le statut
sudo systemctl status gnmanager.service

# Redémarrer le service
sudo systemctl restart gnmanager.service

# Voir les logs
journalctl -u gnmanager.service -f

# Logs de l'application
tail -f /opt/gnmanager/app.log
```

## 📁 Structure du projet

```
gnmanager/
├── app.py                  # Factory Flask
├── main.py                # Point d'entrée
├── routes.py              # Routes et contrôleurs
├── models.py              # Modèles SQLAlchemy
├── auth.py                # Authentification et emails
├── extensions.py          # Extensions Flask
├── deploy.py              # Script de déploiement
├── generate_csvs.py       # Génération de données de test
├── import_csvs.py         # Import de données depuis CSV
├── pyproject.toml         # Dépendances Python (uv)
├── config/
│   ├── deploy_config.yaml          # Configuration de déploiement
│   └── deploy_config_template.yaml # Template de config
├── templates/             # Templates Jinja2
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   └── ...
├── static/                # CSS, JS, Assets
├── ARCHITECTURE.md        # Documentation technique détaillée
└── README.md             # Ce fichier
```

## 📖 Documentation

Consultez [ARCHITECTURE.md](ARCHITECTURE.md) pour :
- Architecture détaillée de l'application
- Flux d'authentification
- Système de rôles (RBAC)
- Guide de déploiement avancé
- Bonnes pratiques de développement

## 🧪 Données de Test

Le script `generate_csvs.py` crée automatiquement :
- 15 utilisateurs avec différents rôles
- 5 événements variés
- 30 rôles
- 21 participations

Utilisation manuelle :
```bash
uv run python generate_csvs.py
uv run python import_csvs.py
```

## 🔒 Sécurité

### Système de rôles

- **Créateur** : Accès total, peut gérer tous les utilisateurs
- **Sysadmin** : Accès admin, ne peut pas modifier/supprimer les créateurs
- **User** : Utilisateur standard

### Règles de sécurité

- Les mots de passe sont hashés avec Werkzeug (bcrypt)
- Un utilisateur ne peut pas se supprimer lui-même
- Un sysadmin ne peut pas promouvoir quelqu'un en créateur
- Validation par email obligatoire pour activer un compte
- Tokens de validation et de reset de mot de passe expirent (24h et 1h)

## 📧 Configuration Email (Brevo)

L'application utilise Brevo (anciennement Sendinblue) pour l'envoi d'emails.

### Obtenir vos identifiants Brevo

1. Créez un compte sur [Brevo](https://www.brevo.com)
2. Allez dans **Settings** → **SMTP & API**
3. Créez une clé SMTP
4. Utilisez les identifiants dans `deploy_config.yaml`

### Variables d'environnement

Le fichier `.env` (généré automatiquement par `deploy.py`) contient :
```env
MAIL_SERVER=smtp-relay.brevo.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=votre_username
MAIL_PASSWORD=votre_password
MAIL_DEFAULT_SENDER=votre@email.com
```

## 🛠️ Développement

### Installation des dépendances

```bash
# Avec uv (recommandé)
uv sync

# Ou avec pip
pip install -r requirements.txt
```

### Lancement en mode développement

```bash
uv run python main.py
```

### Reset de la base de données

```bash
rm gnmanager.db instance/gnmanager.db
uv run python deploy.py --reset-db --import-data
```

## 🐛 Dépannage

### L'email ne part pas

1. Vérifiez que toutes les variables `MAIL_*` sont définies dans `.env`
2. Vérifiez les logs : `[EMAIL ERROR]` pour les détails
3. Testez vos identifiants Brevo dans leur interface

### Le service systemd ne démarre pas

```bash
# Voir les logs système
journalctl -u gnmanager.service -e

# Vérifier le fichier .env
cat /opt/gnmanager/.env

# Tester manuellement
cd /opt/gnmanager
source .venv/bin/activate
python main.py
```

### Erreur de connexion SSH

1. Vérifiez que les variables `GNMANAGER_USER` et `GNMANAGER_PWD` sont définies
2. Testez la connexion manuellement : `ssh user@host`
3. Vérifiez que l'utilisateur a les droits `sudo`

## 📝 Licence

Ce projet est développé pour la gestion interne des événements GN.

## 🤝 Contribution

Pour contribuer :
1. Créez une branche depuis `main`
2. Faites vos modifications
3. Testez localement avec `uv run python deploy.py --reset-db --import-data`
4. Committez avec des messages clairs
5. Créez une Pull Request

## 📞 Support

Pour toute question ou problème :
- Consultez [ARCHITECTURE.md](ARCHITECTURE.md) pour la documentation technique
- Vérifiez les logs de l'application
- Contactez l'administrateur système
