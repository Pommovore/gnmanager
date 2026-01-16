# Guide de Déploiement - GN Manager

Ce document détaille la procédure pour déployer l'application sur le serveur distant **minimoi.mynetgear.com**.

## 1. Préparation de la Configuration

Vérifiez que le fichier `config/deploy_config.yaml` est correctement configuré pour la cible distante :

```yaml
location: remote

deploy:
  machine_name: "minimoi.mynetgear.com"
  port: 8880
  target_directory: "/opt/gnmanager/"

# ... le reste de la configuration (email, admin, etc.) doit être valide
```

## 2. Authentification SSH

Le script de déploiement utilise `paramiko` pour se connecter via SSH. Vous devez définir les identifiants dans votre environnement avant de lancer le script.

### Sous WSL / Bash
```bash
export GNMANAGER_USER=votre_user_ssh
export GNMANAGER_PWD=votre_mot_de_passe_ssh
```

### Sous PowerShell
```powershell
$env:GNMANAGER_USER="votre_user_ssh"
$env:GNMANAGER_PWD="votre_mot_de_passe_ssh"
```

## 3. Commandes de Déploiement

Le déploiement s'effectue via le script `deploy.py` exécuté avec `uv`.

### Cas A : Mise à jour du code (Standard)
Utilisez cette commande pour déployer les dernières modifications du code **sans toucher à la base de données**.

```bash
uv run python deploy.py --dpcfg config/deploy_config.yaml
```

### Cas B : Installation Complète / Reset (Attention !)
Utilisez cette commande pour une première installation ou pour **réinitialiser complètement** l'application (toutes les données seront effacées).

```bash
uv run python deploy.py --dpcfg config/deploy_config.yaml --reset-db --import-data \
  --admin-email 'jchodorowski@gmail.com' \
  --admin-password 'votre_password_admin' \
  --admin-nom 'Chodorowski' \
  --admin-prenom 'Jacques'
```

## 4. Vérification et Maintenance

Une fois déployé, vous pouvez interagir avec le serveur distant pour vérifier le bon fonctionnement.

### Connexion au serveur
```bash
ssh $GNMANAGER_USER@minimoi.mynetgear.com
```

### Gestion du Service
L'application tourne comme un service systemd nommé `gnmanager`.

```bash
# Vérifier le statut
sudo systemctl status gnmanager.service

# Redémarrer le service
sudo systemctl restart gnmanager.service

# Arrêter le service
sudo systemctl stop gnmanager.service
```

### Logs
```bash
# Logs du service systemd
journalctl -u gnmanager.service -f

# Logs de l'application (événements, erreurs applicatives)
tail -f /opt/gnmanager/app.log
```

## 5. Dépannage Courant

- **Erreur SSH** : Vérifiez que `GNMANAGER_USER` et `GNMANAGER_PWD` sont bien définis et que vous pouvez vous connecter manuellement via `ssh`.
- **Erreur Base de Données** : Si vous changez le schéma de la base (nouveaux modèles), vous devrez peut-être faire un reset DB ou gérer une migration manuelle (Alembic non configuré pour auto-migrate en prod pour l'instant).
- **Service ne démarre pas** : Vérifiez les logs avec `journalctl` pour voir si ce n'est pas un problème de variables d'environnement (`.env` mal généré) ou de port déjà utilisé.
- **Erreur SECURITY ERROR: SECRET_KEY** : Si les logs affichent cette erreur, c'est que la clé secrète manque dans le fichier `.env` sur le serveur.
  1. Connectez-vous au serveur : `ssh $GNMANAGER_USER@minimoi.mynetgear.com`
  2. Générez une clé : `python3 -c 'import secrets; print(secrets.token_hex(32))'`
  3. Ajoutez-la au fichier `.env` :
     ```bash
     echo "SECRET_KEY=votre_cle_generee" >> /opt/gnmanager/.env
     ```
  4. Redémarrez le service : `sudo systemctl restart gnmanager.service`
