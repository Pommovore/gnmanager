![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)
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
- Création de rôles pour chaque événement (type, genre, groupe)
- Inscription des participants avec statuts (À valider, En attente, Validé, Rejeté)
- Attribution des rôles (casting)

### Système de Casting avancé
- Matrice dynamique Rôles/Participants
- Algorithme d'attribution automatique optimal (Hongrois/Kuhn-Munkres)
- Gestion des conflits et validations
- **Attribution principale** : Colonne par défaut pour assigner les participants
- **Propositions** : Colonnes additionnelles pour tester différentes versions de casting
- **Scores (0-10)** : Note attribuée à chaque assignation dans les propositions
- **Validation** : Switch "Validé/Non-validé" persistant
- **Affichage conditionnel** : Les participants voient leur rôle assigné uniquement quand le casting est validé
- Lien vers la fiche PDF du personnage (ou "bientôt disponible...")

### Administration
- Tableau de bord complet
- Gestion des utilisateurs (création, édition, suppression)
- Gestion des statuts et permissions
- Vue d'ensemble des événements

## 📋 Prérequis

- **Python 3.11+**
- **uv** (gestionnaire de paquets)
- **Numpy & Scipy** (pour l'algorithme d'attribution de casting)
- **Node.js & npm** (optionnel, pour développement frontend avancé)
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

### Déploiement Local (Développement)

Pour le développement local, il n'est pas nécessaire d'utiliser `fresh_deploy.py`.
Utilisez simplement :
```bash
uv sync
uv run python main.py
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
   uv run python fresh_deploy.py
   ```

Le script `fresh_deploy.py` va :
- Se connecter au serveur via SSH
- Arrêter le service systemd
- Transférer les fichiers via SFTP (ou cloner depuis GitHub)
- Installer les dépendances (`uv sync`)
- Générer le fichier `.env` avec la configuration
- Créer le compte administrateur
- Redémarrer le service systemd

### Mise à jour rapide (sans toucher à la BDD)

Pour déployer uniquement le code sans réinitialiser la base de données :
```bash
uv run python update_deploy.py
```

Ce script :
- Arrête le service
- Crée une archive locale des fichiers Git
- Upload et extrait l'archive sur le serveur
- Redémarre le service

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
├── main.py                 # Point d'entrée
├── models.py               # Modèles SQLAlchemy
├── auth.py                 # Authentification et emails
├── extensions.py           # Extensions Flask
├── constants.py            # Constantes (statuts, types, etc.)
├── manage_db.py            # Gestion de la BDD (export/import JSON/CSV)
├── seed_data.py            # Génération de données de test
├── fresh_deploy.py         # Premier déploiement
├── update_deploy.py        # Mise à jour rapide
├── pyproject.toml          # Dépendances Python (uv)
├── routes/                 # Routes organisées par domaine
│   ├── admin_routes.py
│   ├── auth_routes.py
│   └── event_routes.py     # Inclut les routes de casting
├── config/
│   ├── deploy_config.yaml
│   └── db_test_*.csv       # Données de test exportées
├── migrations/             # Migrations Alembic (Flask-Migrate)
│   └── versions/
├── templates/
│   ├── base.html
│   ├── event_detail.html
│   └── partials/
│       ├── event_info.html
│       └── event_organizer_tabs.html
├── static/                 # CSS, JS, Assets
├── instance/               # Base de données SQLite
├── ARCHITECTURE.md         # Documentation technique
└── README.md               # Ce fichier
```

## 📖 Documentation

Consultez [ARCHITECTURE.md](ARCHITECTURE.md) pour :
- Architecture détaillée de l'application
- Flux d'authentification
- Système de rôles (RBAC)
- Guide de déploiement avancé
- Bonnes pratiques de développement

## 🧪 Données de Test

### Génération automatique (Recommandé)
Le script `seed_data.py` crée une base de données complète et exporte automatiquement les données en CSV dans `config/` :
```bash
uv run python seed_data.py
```

### Export / Import manuel (manage_db.py)
Utilisez `manage_db.py` pour sauvegarder ou restaurer des données. Le script détecte automatiquement le format (JSON ou dossier CSV).

```bash
# Export vers un seul fichier JSON
uv run python manage_db.py export -f backup.json

# Export vers un dossier de fichiers CSV
uv run python manage_db.py export -f config/

# Import (avec --clean pour réinitialiser les tables avant)
uv run python manage_db.py import -f config/ --clean
```

L'option `--clean` réinitialise les tables avant import :
```bash
uv run python manage_db.py import -f config/ --clean
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
uv run python manage_db.py import -f config/ --clean
```

### Migrations de base de données (Flask-Migrate)

Pour gérer les évolutions de schéma lors des mises à jour :

```bash
# Appliquer les migrations en attente
uv run flask db upgrade

# Créer une nouvelle migration après modification de models.py
uv run flask db migrate -m "Description de la migration"

# Voir l'historique
uv run flask db history

# Rétrograder
uv run flask db downgrade
```

## 🚀 Scripts de Déploiement

### fresh_deploy.py
Script de **premier déploiement** complet. Transfère tous les fichiers, installe les dépendances, configure l'environnement et crée le compte admin.

```bash
uv run python fresh_deploy.py
```

**Options principales :**
- `--config` : Chemin du fichier de configuration (défaut: `config/deploy_config.yaml`)

### update_deploy.py
Script de **mise à jour rapide** du code sans toucher à la base de données. Idéal pour déployer des corrections ou nouvelles fonctionnalités.

```bash
uv run python update_deploy.py
```

**Prérequis :** Variables d'environnement `GNMANAGER_USER` et `GNMANAGER_PWD` définies.

### manage_db.py
Script de **gestion de la base de données** : export/import en JSON ou CSV.

```bash
# Export vers dossier CSV
uv run python manage_db.py export -f config/

# Export vers JSON
uv run python manage_db.py export -f backup.json

# Import depuis dossier CSV (avec reset)
uv run python manage_db.py import -f config/ --clean

# Import depuis JSON
uv run python manage_db.py import -f backup.json
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

## ⚖️ Licence

Ce projet est sous licence **GNU Affero General Public License v3.0 (AGPL-3.0)**.

Cela signifie que :
- ✅ **Vous pouvez** utiliser, modifier et distribuer ce logiciel.
- 🔗 **Effet copyleft** : Si vous modifiez ce code et le distribuez (ou l'hébergez sur un serveur pour que d'autres l'utilisent), vous **devez** publier vos modifications sous la même licence AGPL.
- 🔓 **Accès au code** : Les utilisateurs de votre version doivent pouvoir télécharger votre code source.

Voir le fichier [LICENSE](./LICENSE.md) pour le texte complet.

## 🤝 Contribution

Les sources sont disponibles sur [GitHub](https://github.com/pommovore/gnmanager).

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
