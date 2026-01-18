# Guide de Déploiement - GN Manager

Ce document détaille la procédure de déploiement de l'application GN Manager en utilisant le nouveau script unifié `fresh_deploy.py`.

Ce script automatise entièrement le processus :
1. Arrêt du service existant
2. Backup de l'ancienne version
3. Clone propre depuis GitHub
4. Installation des dépendances (`uv`)
5. Configuration (`.env`, `config.yaml`)
6. Création/Mise à jour de la base de données et du compte admin
7. Redémarrage du service

## 1. Prérequis

### Configuration
Assurez-vous que le fichier `config/deploy_config.yaml` est correct.

Pour un déploiement **DISTANT** (Production) :
```yaml
deploy:
  machine_name: "minimoi.mynetgear.com"  # Adresse du serveur
  port: 8880                             # Port d'écoute Flask
  app_prefix: "/gnmanager"               # IMPORTANT pour le reverse proxy
```

Pour un déploiement **LOCAL** (Test) :
```yaml
deploy:
  machine_name: "localhost"
  port: 5000
```

### Variables d'Environnement
Le script nécessite des variables d'environnement pour l'authentification (SSH et sudo).

**Linux / macOS / WSL :**
```bash
export GNMANAGER_USER=votre_user_linux  # Utilisateur sur la machine cible (ex: gnmanager)
export GNMANAGER_PWD=votre_mot_de_passe # Mot de passe (pour SSH et/ou sudo)
```

**PowerShell :**
```powershell
$env:GNMANAGER_USER="votre_user_linux"
$env:GNMANAGER_PWD="votre_mot_de_passe"
```

## 2. Utilisation du Script `fresh_deploy.py`

Le script s'exécute depuis la racine du projet local.

### Syntaxe
```bash
python fresh_deploy.py [TARGET_DIR] [OPTIONS]
```

**Arguments :**
- `TARGET_DIR` : Répertoire parent où installer l'application (ex: `/opt`). L'application sera dans `/opt/gnmanager`.

**Options :**
- `--systemd` : Gère automatiquement l'arrêt et le redémarrage du service systemd `gnmanager.service`.
- `--create-test-db` : Réinitialise la base de données et importe les données de test (ATTENTION : perte de données).
- `--kill` : Tue brutalement tout processus écoutant sur le port configuré avant de démarrer.
- `--config PATH` : Chemin vers le fichier de config (défaut : `./config/deploy_config.yaml`).

## 3. Exemples de Déploiement

### 🚀 Déploiement Production (Remote)
Mise à jour du code sur le serveur distant, sans toucher à la base de données.

```bash
# 1. Définir les credentials
export GNMANAGER_USER=gnmanager
export GNMANAGER_PWD=monSuperMotDePasse

# 2. Lancer le déploiement
# Le script détecte "remote" grâce à deploy_config.yaml
python fresh_deploy.py /opt --systemd
```

### 💥 Réinitialisation Complète (Production ou Test)
Pour réinstaller proprement et remettre des données de test (utile pour les démos ou environnements de qualif).

```bash
python fresh_deploy.py /opt --systemd --create-test-db --kill
```

### 💻 Déploiement Local (Test)
Si `deploy_config.yaml` contient `machine_name: localhost`.

```bash
python fresh_deploy.py /tmp/test_deploy --kill --create-test-db
```

## 4. Gestion du Service (Post-Déploiement)

Une fois déployé, l'application est gérée par **systemd** sur le serveur.

```bash
# Se connecter au serveur
ssh $GNMANAGER_USER@machine_cible

# Vérifier le statut
sudo systemctl status gnmanager.service

# Voir les logs en direct
journalctl -u gnmanager.service -f
```

## 5. Dépannage

- **Erreur SSH / Authentification** : Vérifiez `GNMANAGER_USER` et `GNMANAGER_PWD`.
- **Problème de Prefix URL** : Si les liens (CSS, JS, Login) ne fonctionnent pas, vérifiez que `app_prefix` est bien défini dans `deploy_config.yaml` et que `APPLICATION_ROOT` apparaît bien dans le fichier `/opt/gnmanager/.env` sur le serveur.
- **Service en échec** : 
  1. Regardez les logs : `journalctl -u gnmanager -n 50`
  2. Tentez de lancer l'app manuellement pour voir l'erreur :
     ```bash
     cd /opt/gnmanager
     source .env
     uv run python app.py
     ```
