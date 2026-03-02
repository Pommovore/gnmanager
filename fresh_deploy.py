#!/usr/bin/env python3
"""
Script de déploiement production pour GN Manager.

Ce script automatise le déploiement de GN Manager depuis GitHub :
- Supporte le déploiement local ou distant (SSH) selon la configuration
- Clone le repository officiel
- Gère les backups des anciennes versions
- Configure systemd (optionnel)
- Crée le compte admin
- Importe les données de test (optionnel)

Usage:
    python fresh_deploy.py [TARGET_DIR] [OPTIONS]

Exemples:
    # Déploiement complet avec systemd
    export GNMANAGER_USER=gnmanager
    export GNMANAGER_PWD=secret
    python fresh_deploy.py /opt --systemd --create-test-db
"""

import os
import sys
import shutil
import subprocess
import argparse

import yaml
import time
import json
from pathlib import Path

try:
    import paramiko
except ImportError:
    paramiko = None


def run_command(cmd, user=None, cwd=None, capture_output=False, sudo_password=None, ssh=None):
    """Exécute une commande shell locale ou distante avec gestion d'erreurs."""
    if ssh:
        return run_command_remote(ssh, cmd, user, cwd, capture_output, sudo_password)
    else:
        return run_command_local(cmd, user, cwd, capture_output, sudo_password)


def run_command_local(cmd, user=None, cwd=None, capture_output=False, sudo_password=None):
    """Exécute une commande localement."""
    if user:
        cmd = f"sudo -u {user} {cmd}"
    
    # Si la commande contient sudo et qu'un mot de passe est fourni, utiliser sudo -S
    if 'sudo' in cmd and sudo_password:
        cmd = cmd.replace('sudo', 'sudo -S', 1)
    
    print(f"🔧 [LOCAL] Exécution: {cmd}")
    
    try:
        if capture_output:
            result = subprocess.run(
                cmd, 
                shell=True, 
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
                input=f"{sudo_password}\n" if sudo_password and 'sudo -S' in cmd else None
            )
            return result.stdout
        else:
            subprocess.run(
                cmd, 
                shell=True, 
                cwd=cwd, 
                check=True,
                input=f"{sudo_password}\n" if sudo_password and 'sudo -S' in cmd else None,
                text=True if sudo_password else False
            )
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'exécution locale de: {cmd}")
        print(f"   Code de sortie: {e.returncode}")
        if capture_output and e.stderr:
            print(f"   Stderr: {e.stderr}")
        sys.exit(1)


def sync_database(target_dir, user, sudo_password=None, ssh=None):
    """Synchronise la base de données locale vers le distant."""
    gnmanager_path = os.path.join(target_dir, 'gnmanager')
    print("🔄 Synchronisation de la base de données...")
    
    # 1. Export local
    local_export_file = "deploy_temp.json"
    print(f"  - Export local vers {local_export_file}...")
    try:
        # On utilise uv run pour s'assurer d'avoir les dépendances
        export_cmd = f"uv run python manage_db.py export --file {local_export_file}"
        run_command_local(export_cmd, capture_output=True)
    except Exception as e:
        print(f"❌ Erreur export local: {e}")
        sys.exit(1)
        
    # 2. Transfert
    print(f"  - Transfert vers le serveur...")
    remote_export_file = os.path.join(gnmanager_path, local_export_file)
    try:
        sftp = ssh.open_sftp()
        sftp.put(local_export_file, remote_export_file)
        sftp.close()
    except Exception as e:
        print(f"❌ Erreur transfert fichier: {e}")
        try:
            os.remove(local_export_file)
        except:
            pass
        sys.exit(1)
        
    # 3. Import distant
    print(f"  - Import sur le serveur (avec nettoyage)...")
    try:
        # Commande d'import sur le serveur
        import_cmd = f"export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv run python manage_db.py import --file {local_export_file} --clean"
        run_command_remote(ssh, import_cmd, cwd=gnmanager_path)
    except Exception as e:
         print(f"❌ Erreur import distant: {e}")
         sys.exit(1)
    finally:
        # 4. Nettoyage
        print("  - Nettoyage des fichiers temporaires...")
        try:
            os.remove(local_export_file)  # Local
            run_command_remote(ssh, f"rm {remote_export_file}") # Distant
        except:
            pass
            
    print("✅ Base de données synchronisée")



def run_command_remote(ssh, cmd, user=None, cwd=None, capture_output=False, sudo_password=None):
    """Exécute une commande sur le serveur distant via SSH."""
    if user:
        cmd = f"sudo -u {user} {cmd}"
    
    if 'sudo' in cmd and sudo_password:
        cmd = cmd.replace('sudo', 'sudo -S', 1)
        
    if cwd:
        cmd = f"cd {cwd} && {cmd}"
        
    print(f"🔧 [REMOTE] Exécution: {cmd}")
    
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    if sudo_password and 'sudo -S' in cmd:
        stdin.write(f"{sudo_password}\n")
        stdin.flush()
    # Important: fermer stdin pour signaler la fin de l'entrée (sinon certaines commandes attendent)
    stdin.close()
    
    exit_status = stdout.channel.recv_exit_status()
    out_data = stdout.read().decode().strip()
    err_data = stderr.read().decode().strip()
    
    if exit_status != 0:
        # Ignorer l'erreur standard si c'est juste le prompt sudo
        if "[sudo] password" in err_data and len(err_data.splitlines()) == 1:
            pass
        else:
            print(f"❌ Erreur lors de l'exécution distante de: {cmd}")
            print(f"   Code de sortie: {exit_status}")
            if err_data:
                print(f"   Stderr: {err_data}")
            sys.exit(1)
            
    if capture_output:
        return out_data
    elif out_data:
        print(out_data)


def load_config(config_path):
    """Charge la configuration depuis deploy_config.yaml."""
    print(f"📖 Lecture de la configuration: {config_path}")
    
    if not os.path.exists(config_path):
        print(f"❌ Fichier de configuration non trouvé: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print(f"✅ Configuration chargée")
    return config


def connect_ssh(host, user, password):
    """Établit une connexion SSH."""
    if not paramiko:
        print("❌ Paramiko n'est pas installé. Lancez 'uv add paramiko' ou 'pip install paramiko'")
        sys.exit(1)
        
    print(f"🔌 Connexion SSH vers {host} (user: {user})...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(host, username=user, password=password)
        print("✅ Connecté avec succès")
        return client
    except Exception as e:
        print(f"❌ Erreur de connexion SSH: {e}")
        sys.exit(1)



# Ajout de l'argument pour le nom du service
def stop_systemd_service(service_name, sudo_password=None, ssh=None):
    """Arrête le service systemd."""
    print(f"🛑 Arrêt du service systemd ({service_name})...")
    try:
        run_command(f"sudo systemctl stop {service_name}", capture_output=True, sudo_password=sudo_password, ssh=ssh)
        print(f"✅ Service {service_name} arrêté")
    except Exception:
        print(f"⚠️  Impossible d'arrêter le service {service_name} (peut-être pas installé ?)")


def kill_port_processes(port, sudo_password=None, ssh=None):
    """Tue les processus sur le port spécifié."""
    print(f"🛑 Arrêt des processus sur le port {port}...")
    cmd = f"sudo -S fuser -k {port}/tcp" if sudo_password else f"sudo fuser -k {port}/tcp"
    
    # fuser retourne souvent 1 si rien n'est trouvé, on ne veut pas exit(1) dans ce cas
    # On gère l'exception manuellement ici
    try:
        if ssh:
            # Pour remote, on utilise exec_command directement pour gérer le code de retour
            ssh_cmd = cmd
            if sudo_password:
                ssh_cmd = cmd.replace('sudo', 'sudo -S', 1)
            
            stdin, stdout, stderr = ssh.exec_command(ssh_cmd)
            if sudo_password:
                stdin.write(f"{sudo_password}\n")
                stdin.flush()
            stdin.close()
            
            status = stdout.channel.recv_exit_status()
            if status == 0:
                print(f"✅ Processus sur le port {port} arrêtés")
            else:
                 print(f"ℹ️  Aucun processus trouvé sur le port {port}")
        else:
            # Local
            subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                input=f"{sudo_password}\n" if sudo_password else None,
                text=True if sudo_password else False
            )
            print(f"ℹ️  Vérification port {port} terminée")
            
    except Exception as e:
        print(f"ℹ️  Erreur non critique lors du kill port: {e}")


def check_remote_dir_exists(ssh, path):
    """Vérifie si un dossier existe sur le serveur distant."""
    cmd = f"test -d {path} && echo 'yes' || echo 'no'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode().strip() == 'yes'


def rename_old_deployment(deployment_path, ssh=None, sudo_password=None):
    """Renomme l'ancien déploiement avec extension .old_N."""
    # deployment_path est le chemin complet (ex: /opt/gnmanager ou /opt/gnmanager_dev)
    
    if ssh:
        exists = check_remote_dir_exists(ssh, deployment_path)
    else:
        exists = os.path.exists(deployment_path)
        
    if not exists:
        print(f"ℹ️  Aucun déploiement existant dans {deployment_path}")
        return
    
    # Trouver le premier .old_N disponible
    i = 1
    while True:
        old_path = f"{deployment_path}.old_{i}"
        if ssh:
            if not check_remote_dir_exists(ssh, old_path):
                break
        else:
            if not os.path.exists(old_path):
                break
        i += 1
    
    old_path = f"{deployment_path}.old_{i}"
    print(f"📦 Renommage de l'ancien déploiement: {deployment_path} -> {old_path}")
    
    cmd = f"sudo mv {deployment_path} {old_path}"
    run_command(cmd, ssh=ssh, sudo_password=sudo_password)
    print(f"✅ Ancien déploiement sauvegardé dans {old_path}")



def transfer_files(deployment_path, user, sudo_password=None, ssh=None):
    """Transfère les fichiers suivis par git vers la cible (au lieu de cloner)."""
    # deployment_path est déjà le chemin complet (ex: /opt/gnmanager_dev)
    print(f"📂 Transfert des fichiers locaux vers {deployment_path}...")
    
    # 1. Lister les fichiers suivis par git
    try:
        files = subprocess.check_output(['git', 'ls-files'], text=True).strip().splitlines()
    except Exception as e:
        print(f"❌ Erreur git ls-files: {e}")
        sys.exit(1)
        
    # Ajouter config/deploy_config.yaml et google_credentials.json s'ils ne sont pas suivis
    extras = ['config/deploy_config.yaml', 'config/google_credentials.json']
    # Ajouter aussi les configs spécifiques pour référence
    extras.extend(['config/deploy_config_prod.yaml', 'config/deploy_config_dev.yaml', 'config/deploy_config_test.yaml'])

    for extra in extras:
        if os.path.exists(extra):
            files.append(extra)
            
    # Créer le dossier racine (si n'existe pas)
    run_command(f"sudo mkdir -p {deployment_path}", sudo_password=sudo_password, ssh=ssh)
    # Donner la propriété temporaire pour pouvoir écrire
    current_user_cmd = "whoami"
    if ssh:
        stdin, stdout, stderr = ssh.exec_command(current_user_cmd)
        current_user = stdout.read().decode().strip()
    else:
        current_user = subprocess.check_output(current_user_cmd, shell=True, text=True).strip()
        
    run_command(f"sudo chown -R {current_user} {deployment_path}", sudo_password=sudo_password, ssh=ssh)
    
    if ssh:
        sftp = ssh.open_sftp()
        created_dirs = set()
        for f in files:
            local_path = f
            remote_path = os.path.join(deployment_path, f).replace("\\", "/") 
            remote_dir = os.path.dirname(remote_path)
            
            if remote_dir not in created_dirs:
                try:
                    cmd = f"mkdir -p {remote_dir}"
                    ssh.exec_command(cmd)
                    created_dirs.add(remote_dir)
                except Exception as e:
                    print(f"⚠️ Erreur création dossier {remote_dir}: {e}")
            
            try:
                sftp.put(local_path, remote_path)
            except Exception as e:
                print(f"⚠️ Erreur copie {f}: {e}")

        sftp.close()
    else:
        # Local copy
        for f in files:
            src = os.path.abspath(f)
            dst = os.path.join(deployment_path, f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            
    print(f"✅ {len(files)} fichiers transférés")



def setup_ownership(deployment_path, user, sudo_password=None, ssh=None):
    """Configure la propriété des fichiers."""
    print(f"🔑 Configuration de la propriété: {user}:{user}")
    run_command(f"sudo chown -R {user}:{user} {deployment_path}", sudo_password=sudo_password, ssh=ssh)
    print("✅ Propriété configurée")


def copy_config(config_source_path, deployment_path, ssh=None):
    """Copie le fichier de configuration."""
    source = os.path.abspath(config_source_path)
    # On renomme toujours en deploy_config.yaml sur la cible pour que l'app s'y retrouve par défaut
    dest_path = os.path.join(deployment_path, 'config', 'deploy_config.yaml')
    
    print(f"📋 Copie de la configuration: {source} -> {dest_path}")
    
    if ssh:
        sftp = ssh.open_sftp()
        # S'assurer que le dossier config existe
        remote_config_dir = os.path.dirname(dest_path)
        try:
            sftp.stat(remote_config_dir)
        except IOError:
            pass
            
        sftp.put(source, dest_path)
        sftp.close()
    else:
        shutil.copy(source, dest_path)
        
    print("✅ Configuration copiée")


def install_dependencies(deployment_path, user, sudo_password=None, ssh=None):
    """Installe les dépendances avec uv."""
    print("📦 Installation des dépendances (uv sync)...")
    
    # Prefix command to ensuring uv is in PATH
    uv_cmd = "export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv sync"
    
    run_command(uv_cmd, cwd=deployment_path, ssh=ssh)
    print("✅ Dépendances installées")


def create_version_file(deployment_path, user, sudo_password=None, ssh=None):
    """Génère le fichier .deploy-version."""
    print("🔖 Génération du fichier de version...")
    
    version_str = "dev"
    try:
        # 0. Fetch tags to ensure we have the latest
        subprocess.run(["git", "fetch", "origin", "--tags"], check=False, stderr=subprocess.DEVNULL)

        # 1. Get last commit date formatted
        ts = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y%m%d_%H%M%S"], 
            text=True
        ).strip()
        
        # 2. Get latest tag
        try:
            # Utilisation de la méthode triée par version (semver) pour avoir la version la plus élevée
            # creatordate peut être trompeur si une vieille version a été taggée récemment
            tag_cmd = "git tag --sort=-version:refname | head -n 1"
            tag = subprocess.check_output(tag_cmd, shell=True, text=True).strip()
            if not tag:
                tag = "dev"
        except Exception:
            try:
                tag = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
            except:
                tag = "dev"
                
        version_str = f"{tag}_{ts}"
    except Exception as e:
        print(f"⚠️ Impossible de déterminer la version git locale: {e}")
        version_str = f"dev_{int(time.time())}"
        
    print(f"ℹ️  Version détectée: {version_str}")
    
    version_file = ".deploy-version"
    
    if ssh:
        with open('temp_version', 'w') as f:
            f.write(version_str)
        try:
            sftp = ssh.open_sftp()
            remote_path = os.path.join(deployment_path, version_file)
            sftp.put('temp_version', remote_path)
            sftp.close()
            os.remove('temp_version')
            
            run_command(f"chown {user}:{user} {remote_path}" if user else f"chmod 644 {remote_path}", 
                       sudo_password=sudo_password, ssh=ssh)
        except Exception as e:
             print(f"❌ Erreur envoi fichier version: {e}")
    else:
        target_file = os.path.join(deployment_path, version_file)
        with open(target_file, 'w') as f:
            f.write(version_str)
            
    print("✅ Fichier .deploy-version créé")


# 2. Update definition
def create_env_file(deployment_path, config, user, env_name="prod", sudo_password=None, ssh=None, force_local=False):
    """Crée le fichier .env avec les variables d'environnement."""
    env_path = os.path.join(deployment_path, '.env')
    
    print("🔐 Génération du fichier .env...")
    
    email_config = config.get('email', {})
    deploy_config = config.get('deploy', {})
    
    # Générer une SECRET_KEY
    import secrets
    secret_key = secrets.token_hex(32)
    api_secret = secrets.token_hex(16) 
    
    host = deploy_config.get('machine_name', '0.0.0.0')
    port = deploy_config.get('port', 5000)
    app_prefix = deploy_config.get('app_prefix')
    flask_host = '0.0.0.0' 
    
    # Détermination de l'hôte public (pour les liens emails)
    # En local, on garde le port (ex: localhost:5000)
    # En remote, on suppose qu'un reverse proxy gère ça (ex: domaine.com/prefixe) et on enlève le port interne
    if force_local:
        public_host = f"{host}:{port}"
    else:
        public_host = host

    env_content = f"""# Configuration générée automatiquement par fresh_deploy.py
MAIL_SERVER={email_config.get('server', 'smtp-relay.brevo.com')}
MAIL_PORT={email_config.get('port', 587)}
MAIL_USE_TLS={str(email_config.get('use_tls', True)).lower()}
MAIL_USERNAME={email_config.get('username', '')}
MAIL_PASSWORD={email_config.get('password', '')}
MAIL_DEFAULT_SENDER={email_config.get('default_sender', '')}
FLASK_HOST={flask_host}
FLASK_PORT={port}
APP_PUBLIC_HOST={public_host}
SECRET_KEY={secret_key}
API_SECRET={api_secret}
PYTHONUNBUFFERED=1
GN_ENVIRONMENT={env_name}
"""
    if app_prefix and not force_local:
        env_content += f"APPLICATION_ROOT={app_prefix}\n"

    # Services externes (webhooks d'analyse des traits de caractère)
    pdf2txt_config = config.get('pdf2txt', {})
    character_config = config.get('character', {})

    if pdf2txt_config.get('api_url'):
        env_content += f"WEBHOOK_PDF2TXT_API_URL={pdf2txt_config['api_url']}\n"
    if pdf2txt_config.get('token'):
        env_content += f"WEBHOOK_PDF2TXT_API_TOKEN={pdf2txt_config['token']}\n"
    if character_config.get('api_url'):
        env_content += f"WEBHOOK_CHARACTER_API_URL={character_config['api_url']}\n"
    if character_config.get('token'):
        env_content += f"WEBHOOK_CHARACTER_API_TOKEN={character_config['token']}\n"

    # Google Credentials
    google_creds_path = './config/google_credentials.json'
    if not os.path.exists(google_creds_path):
         google_creds_path = os.path.join(os.path.dirname(__file__), 'config', 'google_credentials.json')

    if os.path.exists(google_creds_path):
        try:
            with open(google_creds_path, 'r') as f:
                creds = json.load(f)
                web_config = creds.get('web', creds)
                client_id = web_config.get('client_id')
                client_secret = web_config.get('client_secret')
                if client_id and client_secret:
                    print(f"🔑 Ajout des credentials Google depuis {google_creds_path}")
                    env_content += f"GOOGLE_CLIENT_ID={client_id}\n"
                    env_content += f"GOOGLE_CLIENT_SECRET={client_secret}\n"
        except Exception as e:
            print(f"⚠️ Erreur lecture google_credentials.json: {e}")

    if ssh:
        temp_env = '.env.tmp'
        with open(temp_env, 'w', encoding='utf-8') as f:
            f.write(env_content)
        sftp = ssh.open_sftp()
        sftp.put(temp_env, env_path)
        sftp.close()
        os.remove(temp_env)
    else:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
    
    print("✅ Fichier .env créé")


def create_admin_user(deployment_path, config, user, sudo_password=None, ssh=None):
    """Crée le compte admin dans la base de données."""
    admin_config = config.get('admin', {})
    
    admin_email = admin_config.get('email', 'admin@example.com')
    admin_password = admin_config.get('password', 'admin')
    admin_nom = admin_config.get('nom', 'Admin')
    admin_prenom = admin_config.get('prenom', 'Super')
    
    print(f"👤 Création du compte admin: {admin_email}")
    
    script = f"""
from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import sys
import os

try:
    load_dotenv()
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(email='{admin_email}').first()
        if admin:
            print('Admin existe déjà, mise à jour...')
            admin.password_hash = generate_password_hash('{admin_password}')
            admin.nom = '{admin_nom}'
            admin.prenom = '{admin_prenom}'
            admin.role = 'createur'
        else:
            print('Création du compte admin...')
            admin = User(
                email='{admin_email}',
                password_hash=generate_password_hash('{admin_password}'),
                nom='{admin_nom}',
                prenom='{admin_prenom}',
                role='createur'
            )
            db.session.add(admin)
        
        db.session.commit()
        print('✅ Compte admin créé/mis à jour')
except Exception as e:
    print(f'ERREUR: {{e}}')
    sys.exit(1)
"""
    script_name = "init_admin.py"
    if ssh:
        with open(script_name, 'w') as f:
            f.write(script)
        sftp = ssh.open_sftp()
        remote_script = os.path.join(deployment_path, script_name)
        sftp.put(script_name, remote_script)
        sftp.close()
        os.remove(script_name)
        
        run_command(f"export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv run python {script_name}", cwd=deployment_path, ssh=ssh)
        run_command(f"rm {script_name}", cwd=deployment_path, ssh=ssh)
    else:
        local_script = os.path.join(deployment_path, script_name)
        with open(local_script, 'w') as f:
            f.write(script)
        run_command(f"export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv run python {script_name}", cwd=deployment_path)
        os.remove(local_script)
        
    print("✅ Compte admin configuré")


def import_test_data(deployment_path, user, sudo_password=None, ssh=None):
    """Importe les données de test depuis config/."""
    print("📊 Import des données de test...")
    run_command(
        "export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv run python manage_db.py import -f config/ --clean",
        cwd=deployment_path,
        ssh=ssh
    )
    print("✅ Données de test importées")


def start_systemd_service(service_name, sudo_password=None, ssh=None):
    """Démarre le service systemd."""
    print(f"🚀 Démarrage du service systemd ({service_name})...")
    run_command(f"sudo systemctl start {service_name}", sudo_password=sudo_password, ssh=ssh)
    print("✅ Service systemd démarré")


def sync_database(deployment_path, user, sudo_password=None, ssh=None):
    """Synchronise la base de données locale vers le distant."""
    print("🔄 Synchronisation de la base de données...")
    
    # 1. Export local
    local_export_file = "deploy_temp.json"
    print(f"  - Export local vers {local_export_file}...")
    try:
        # On utilise uv run pour s'assurer d'avoir les dépendances
        export_cmd = f"uv run python manage_db.py export --file {local_export_file}"
        run_command_local(export_cmd, capture_output=True)
    except Exception as e:
        print(f"❌ Erreur export local: {e}")
        sys.exit(1)
        
    # 2. Transfert
    print(f"  - Transfert vers le serveur...")
    remote_export_file = os.path.join(deployment_path, local_export_file)
    try:
        sftp = ssh.open_sftp()
        sftp.put(local_export_file, remote_export_file)
        sftp.close()
    except Exception as e:
        print(f"❌ Erreur transfert fichier: {e}")
        try: os.remove(local_export_file)
        except: pass
        sys.exit(1)
        
    # 3. Import distant
    print(f"  - Import sur le serveur (avec nettoyage)...")
    try:
        # Commande d'import sur le serveur
        import_cmd = f"export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv run python manage_db.py import --file {local_export_file} --clean"
        run_command_remote(ssh, import_cmd, cwd=deployment_path)
    except Exception as e:
         print(f"❌ Erreur import distant: {e}")
         sys.exit(1)
    finally:
        # 4. Nettoyage
        print("  - Nettoyage des fichiers temporaires...")
        try:
            os.remove(local_export_file)  # Local
            run_command_remote(ssh, f"rm {remote_export_file}") # Distant
        except:
            pass
            
    print("✅ Base de données synchronisée")


def main():
    parser = argparse.ArgumentParser(
        description='Déploiement production GN Manager (Local ou Remote)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemple:
    python fresh_deploy.py --prod --systemd --create-test-db
    python fresh_deploy.py --dev --systemd
        """
    )
    
    # Groupe d'environnement mutuellement exclusif et OBLIGATOIRE
    env_group = parser.add_mutually_exclusive_group(required=True)
    env_group.add_argument('--prod', action='store_true', help='Environnement PRODUCTION')
    env_group.add_argument('--test', action='store_true', help='Environnement TEST')
    env_group.add_argument('--dev', action='store_true', help='Environnement DÉVELOPPEMENT')

    parser.add_argument(
        '--target-dir',
        default=None, # On déduira du fichier de config ou par défaut /opt
        help='Répertoire parent (Optionnel, surcharge la config)'
    )
    parser.add_argument(
        '--kill',
        action='store_true',
        help='Arrêter les processus sur le port avant déploiement'
    )
    parser.add_argument(
        '--systemd',
        action='store_true',
        help='Gérer le service systemd (stop/start)'
    )
    parser.add_argument(
        '--create-test-db',
        action='store_true',
        help='Importer les données de test après installation'
    )
    parser.add_argument(
        '--copy-db',
        action='store_true',
        help='Copier la base de données locale vers le serveur distant (écrase la base distante)'
    )
    parser.add_argument(
        '--keep-dev-db',
        action='store_true',
        help='Déployer la base de données de développement en l\'état courant (Alias de --copy-db)'
    )
    
    args = parser.parse_args()
    
    # Détermination de l'environnement
    if args.prod:
        env_name = "prod"
        config_path = "./config/deploy_config_prod.yaml"
        service_suffix = "" # gnole
    elif args.test:
        env_name = "test"
        config_path = "./config/deploy_config_test.yaml"
        service_suffix = "_test" # gnole_test
    elif args.dev:
        env_name = "dev"
        config_path = "./config/deploy_config_dev.yaml"
        service_suffix = "_dev" # gnole_dev
    
    service_name = f"gnole{service_suffix}.service"

    print(f"🌍 Environnement sélectionné: {env_name.upper()}")
    print(f"⚙️  Fichier config: {config_path}")
    print(f"🔧 Service Systemd: {service_name}")

    if not os.path.exists(config_path):
        # Fallback si le fichier spécifique n'existe pas (compatibilité)
        print(f"⚠️  Config {config_path} introuvable. Tentative avec deploy_config.yaml...")
        config_path = "./config/deploy_config.yaml"

    # Charger la configuration
    config = load_config(config_path)
    
    deploy_config = config.get('deploy', {})
    machine_name = deploy_config.get('machine_name')
    port = deploy_config.get('port', 5000)
    
    # Détermination du dossier cible (deployment_path)
    # Priorité: 1. Argument CLI --target-dir 2. Config YAML 'target_directory' 3. Défaut '/opt/gnmanager...'
    
    config_target_dir = deploy_config.get('target_directory')
    
    if args.target_dir:
        # Si passé en argument, on suppose que c'est le parent (comme avant)
        # OU on décide que c'est le path complet?
        # Pour compatibilité, disons que si l'user force un dir, c'est le parent.
        # MAIS avec les nouveaux envs, c'est flou.
        # On va dire: si force target-dir, on append gnmanager{suffix}
        deployment_path = os.path.join(args.target_dir, f"gnmanager{service_suffix}".replace('.service', ''))
    elif config_target_dir:
        # Chemin complet depuis la config
        deployment_path = config_target_dir.rstrip('/')
    else:
        # Défaut absolu
        deployment_path = f"/opt/gnmanager{service_suffix}".replace('.service', '')

    print(f"📂 Chemin de déploiement: {deployment_path}")

    # Validation obligatoire pour le mode distant
    if not machine_name or machine_name in ['localhost', '127.0.0.1', '0.0.0.0']:
        print("❌ Erreur: Ce script est conçu pour le déploiement distant uniquement.")
        print("   Veuillez configurer 'machine_name' dans le fichier yaml.")
        sys.exit(1)
        
    user = os.environ.get('GNMANAGER_USER')
    if not user:
        print("❌ Variable d'environnement GNMANAGER_USER non définie")
        sys.exit(1)
    
    sudo_password = os.environ.get('GNMANAGER_PWD')
    if not sudo_password:
        print("❌ Pour le déploiement distant, GNMANAGER_PWD est obligatoire (connexion SSH).")
        sys.exit(1)
        
    ssh = connect_ssh(machine_name, user, sudo_password)

    print("=" * 70)
    print(f"🚀 DÉPLOIEMENT {env_name.upper()} GN MANAGER")
    print("=" * 70)
    print(f"🎯 Serveur: {machine_name}")
    print(f"👤 Utilisateur: {user}")
    print("=" * 70)
    
    try:
        # 1. Arrêt des services
        if args.systemd:
            stop_systemd_service(service_name, sudo_password, ssh)
        
        if args.kill:
            kill_port_processes(port, sudo_password, ssh)
        
        # 2. Backup de l'ancien déploiement
        rename_old_deployment(deployment_path, ssh, sudo_password)
        
        # 3. Transfert des fichiers
        transfer_files(deployment_path, user, sudo_password, ssh)
        
        # 4. Configuration de la propriété
        setup_ownership(deployment_path, user, sudo_password, ssh)
        
        # 5. Copie de la configuration
        copy_config(config_path, deployment_path, ssh)
        
        # 6. Installation des dépendances
        install_dependencies(deployment_path, None, sudo_password, ssh)

        # 6.5 Création fichier version
        create_version_file(deployment_path, user, sudo_password, ssh)

        # 7. Création du fichier .env
        create_env_file(deployment_path, config, user, env_name=env_name, ssh=ssh)
        
        # 8. Création du compte admin
        create_admin_user(deployment_path, config, None, sudo_password, ssh)
        
        # 9. Sync DB (Optionnel)
        if args.copy_db or args.keep_dev_db:
             sync_database(deployment_path, user, sudo_password, ssh)
        
        # 10. Import des données de test
        if args.create_test_db:
            import_test_data(deployment_path, None, sudo_password, ssh)

        # 10. Démarrage du service (optionnel)
        if args.systemd:
            start_systemd_service(service_name, sudo_password, ssh)
        
        print("=" * 70)
        print("✅ DÉPLOIEMENT TERMINÉ AVEC SUCCÈS!")
        print("=" * 70)
        
        if ssh:
            ssh.close()
            
    except Exception as e:
        print("=" * 70)
        print(f"❌ ERREUR LORS DU DÉPLOIEMENT: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 70)
        if ssh:
            ssh.close()
        sys.exit(1)


if __name__ == '__main__':
    main()
