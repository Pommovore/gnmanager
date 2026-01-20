# Guide de Déploiement - GN Manager

Ce document détaille les scripts de déploiement de l'application GN Manager.

## Scripts Disponibles

| Script | Usage |
|--------|-------|
| `fresh_deploy.py` | Premier déploiement complet (clone, install, config) |
| `update_deploy.py` | Mise à jour rapide du code (sans toucher à la BDD) |
| `manage_db.py` | Export/Import de la base de données |

---

## 1. Prérequis

### Configuration
Assurez-vous que le fichier `config/deploy_config.yaml` est correct.

Pour un déploiement **DISTANT** (Production) :
```yaml
location: remote

deploy:
  machine_name: "minimoi.mynetgear.com"  # Adresse du serveur
  port: 8880                             # Port d'écoute Flask
  target_directory: "/opt/gnmanager"
```

Pour un déploiement **LOCAL** (Test) :
```yaml
location: local

deploy:
  machine_name: "localhost"
  port: 5000
```

### Variables d'Environnement
Les scripts nécessitent des variables pour l'authentification SSH.

**Linux / macOS / WSL :**
```bash
export GNMANAGER_USER=votre_user_linux  # Utilisateur sur la machine cible
export GNMANAGER_PWD=votre_mot_de_passe # Mot de passe SSH/sudo
```

**PowerShell :**
```powershell
$env:GNMANAGER_USER="votre_user_linux"
$env:GNMANAGER_PWD="votre_mot_de_passe"
```

---

## 2. fresh_deploy.py - Premier Déploiement

Script de déploiement complet qui automatise :
1. Arrêt du service existant
2. Backup de l'ancienne version
3. Transfert des fichiers depuis le dépôt local
4. Installation des dépendances (`uv sync`)
5. Configuration (`.env`, `config.yaml`)
6. Création du compte admin
7. Redémarrage du service

### Syntaxe
```bash
uv run python fresh_deploy.py [OPTIONS]
```

**Options :**
- `--config PATH` : Chemin vers le fichier de config (défaut : `config/deploy_config.yaml`)

### Exemples

**Déploiement Production :**
```bash
export GNMANAGER_USER=gnmanager
export GNMANAGER_PWD=monSuperMotDePasse
uv run python fresh_deploy.py
```

**Déploiement Local :**
```bash
uv run python fresh_deploy.py
```

---

## 3. update_deploy.py - Mise à Jour Rapide

Script de mise à jour du **code uniquement**, sans toucher à la base de données.
Idéal pour déployer des corrections ou nouvelles fonctionnalités.

### Fonctionnement
1. Arrête le service systemd
2. Crée une archive locale des fichiers suivis par Git
3. Upload et extrait l'archive sur le serveur
4. Redémarre le service

### Syntaxe
```bash
uv run python update_deploy.py [OPTIONS]
```

**Options :**
- `--config PATH` : Fichier de configuration (défaut : `config/deploy_config.yaml`)
- `--key PATH` : Chemin vers la clé SSH privée (alternative au mot de passe)

### Exemple
```bash
export GNMANAGER_USER=gnmanager
export GNMANAGER_PWD=monSuperMotDePasse
uv run python update_deploy.py
```

---

## 4. manage_db.py - Gestion de la Base de Données

Script d'export et import de données en **JSON** ou **CSV**.

### Export
```bash
# Export vers dossier CSV
uv run python manage_db.py export -f config/

# Export vers JSON
uv run python manage_db.py export -f backup.json
```

### Import
```bash
# Import depuis CSV (avec réinitialisation)
uv run python manage_db.py import -f config/ --clean

# Import depuis JSON
uv run python manage_db.py import -f backup.json
```

**Option `--clean`** : Supprime toutes les données existantes avant l'import.

### Tables exportées/importées
- `User` : Utilisateurs
- `Event` : Événements (inclut `is_casting_validated`)
- `Role` : Rôles des personnages
- `Participant` : Inscriptions
- `CastingProposal` : Propositions de casting
- `CastingAssignment` : Attributions (inclut `score`)
- `PasswordResetToken` : Tokens de reset
- `AccountValidationToken` : Tokens de validation
- `ActivityLog` : Logs d'activité

---

## 5. Migrations de Base de Données (Flask-Migrate)

Après une mise à jour du code qui modifie les modèles SQLAlchemy, les migrations doivent être appliquées.

### Appliquer les migrations en production
```bash
ssh $GNMANAGER_USER@machine_cible
cd /opt/gnmanager
source .venv/bin/activate
uv run flask db upgrade
```

### Créer une nouvelle migration (développement)
```bash
# Après modification de models.py
uv run flask db migrate -m "Description de la modification"

# Vérifier le fichier généré dans migrations/versions/
# Puis appliquer
uv run flask db upgrade
```

### Migrations existantes
| Révision | Description |
|----------|-------------|
| `250207c201b0` | Ajout de `google_form_active` à Event |
| `2f8a1c3b4d5e` | Ajout de `is_casting_validated` (Event) et `score` (CastingAssignment) |

### En cas de problème de migration
Si la base de données est déjà à jour mais la table `alembic_version` n'est pas synchronisée :
```bash
# Marquer la base comme à jour sans exécuter les migrations
uv run flask db stamp head

# Ou manuellement
sqlite3 instance/gnmanager.db "DELETE FROM alembic_version; INSERT INTO alembic_version (version_num) VALUES ('2f8a1c3b4d5e');"
```

---

## 6. Gestion du Service (Post-Déploiement)

L'application est gérée par **systemd** sur le serveur.

```bash
# Se connecter au serveur
ssh $GNMANAGER_USER@machine_cible

# Vérifier le statut
sudo systemctl status gnmanager.service

# Voir les logs en direct
journalctl -u gnmanager.service -f

# Redémarrer manuellement
sudo systemctl restart gnmanager.service
```

---

## 7. Dépannage

| Problème | Solution |
|----------|----------|
| Erreur SSH / Authentification | Vérifiez `GNMANAGER_USER` et `GNMANAGER_PWD` |
| Liens (CSS, JS) cassés | Vérifiez `app_prefix` dans `deploy_config.yaml` |
| Service en échec | Consultez les logs : `journalctl -u gnmanager -n 50` |

**Test manuel du service :**
```bash
cd /opt/gnmanager
source .venv/bin/activate
uv run python main.py
```
