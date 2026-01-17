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


def stop_systemd_service(sudo_password=None, ssh=None):
    """Arrête le service systemd."""
    print("🛑 Arrêt du service systemd...")
    try:
        run_command("sudo systemctl stop gnmanager.service", capture_output=True, sudo_password=sudo_password, ssh=ssh)
        print("✅ Service systemd arrêté")
    except Exception:
        print("⚠️  Impossible d'arrêter le service (peut-être pas installé ?)")


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


def rename_old_deployment(target_dir, ssh=None, sudo_password=None):
    """Renomme l'ancien déploiement avec extension .old_N."""
    gnmanager_path = os.path.join(target_dir, 'gnmanager')
    
    if ssh:
        exists = check_remote_dir_exists(ssh, gnmanager_path)
    else:
        exists = os.path.exists(gnmanager_path)
        
    if not exists:
        print(f"ℹ️  Aucun déploiement existant dans {target_dir}")
        return
    
    # Trouver le premier .old_N disponible
    i = 1
    while True:
        old_path = f"{gnmanager_path}.old_{i}"
        if ssh:
            if not check_remote_dir_exists(ssh, old_path):
                break
        else:
            if not os.path.exists(old_path):
                break
        i += 1
    
    old_path = f"{gnmanager_path}.old_{i}"
    print(f"📦 Renommage de l'ancien déploiement: {gnmanager_path} -> {old_path}")
    
    cmd = f"sudo mv {gnmanager_path} {old_path}"
    run_command(cmd, ssh=ssh, sudo_password=sudo_password)
    print(f"✅ Ancien déploiement sauvegardé dans {old_path}")


def clone_repository(target_dir, user, sudo_password=None, ssh=None):
    """Clone le repository GitHub."""
    print(f"📥 Clone du repository GitHub dans {target_dir}...")
    # Utiliser sudo (root) pour le clone car le dossier parent (ex: /opt) n'est peut-être pas inscriptible
    # La propriété sera corrigée juste après par setup_ownership
    run_command(
        "sudo git clone https://github.com/Pommovore/gnmanager.git",
        cwd=target_dir,
        sudo_password=sudo_password,
        ssh=ssh
    )
    print("✅ Repository cloné")


def setup_ownership(target_dir, user, sudo_password=None, ssh=None):
    """Configure la propriété des fichiers."""
    gnmanager_path = os.path.join(target_dir, 'gnmanager')
    print(f"🔑 Configuration de la propriété: {user}:{user}")
    run_command(f"sudo chown -R {user}:{user} {gnmanager_path}", sudo_password=sudo_password, ssh=ssh)
    print("✅ Propriété configurée")


def copy_config(config_path, target_dir, ssh=None):
    """Copie le fichier de configuration."""
    source = os.path.abspath(config_path)
    dest_path = os.path.join(target_dir, 'gnmanager', 'config', 'deploy_config.yaml')
    
    print(f"📋 Copie de la configuration: {source} -> {dest_path}")
    
    if ssh:
        sftp = ssh.open_sftp()
        # S'assurer que le dossier config existe
        remote_config_dir = os.path.dirname(dest_path)
        try:
            sftp.stat(remote_config_dir)
        except IOError:
            # Créer le dossier (on suppose que le clonage git l'a déjà créé, mais par sécurité)
            pass
            
        sftp.put(source, dest_path)
        sftp.close()
    else:
        shutil.copy(source, dest_path)
        
    print("✅ Configuration copiée")


def install_dependencies(target_dir, user, sudo_password=None, ssh=None):
    """Installe les dépendances avec uv."""
    gnmanager_path = os.path.join(target_dir, 'gnmanager')
    print("📦 Installation des dépendances (uv sync)...")
    
    # Prefix command to ensuring uv is in PATH
    uv_cmd = "export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv sync"
    
    # Note: On ne passe PAS 'user' pour éviter d'utiliser sudo, car on possède déjà le dossier
    # et sudo réinitialiserait le PATH, rendant 'uv' introuvable.
    run_command(uv_cmd, cwd=gnmanager_path, ssh=ssh)
    print("✅ Dépendances installées")


def create_env_file(target_dir, config, user, sudo_password=None, ssh=None):
    """Crée le fichier .env avec les variables d'environnement."""
    gnmanager_path = os.path.join(target_dir, 'gnmanager')
    env_path = os.path.join(gnmanager_path, '.env')
    
    print("🔐 Génération du fichier .env...")
    
    email_config = config.get('email', {})
    deploy_config = config.get('deploy', {})
    
    # Générer une SECRET_KEY
    import secrets
    secret_key = secrets.token_hex(32)
    
    host = deploy_config.get('machine_name', '0.0.0.0')
    port = deploy_config.get('port', 5000)
    
    # Si machine_name est distant, on veut quand même écouter sur 0.0.0.0
    flask_host = '0.0.0.0' 
    
    env_content = f"""# Configuration générée automatiquement par fresh_deploy.py
MAIL_SERVER={email_config.get('server', 'smtp-relay.brevo.com')}
MAIL_PORT={email_config.get('port', 587)}
MAIL_USE_TLS={str(email_config.get('use_tls', True)).lower()}
MAIL_USERNAME={email_config.get('username', '')}
MAIL_PASSWORD={email_config.get('password', '')}
MAIL_DEFAULT_SENDER={email_config.get('default_sender', '')}
FLASK_HOST={flask_host}
FLASK_PORT={port}
APP_PUBLIC_HOST={host}:{port}
SECRET_KEY={secret_key}
PYTHONUNBUFFERED=1
"""
    
    if ssh:
        # Écrire localement temporairement
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
    
    # Propriété déjà correcte (créé par l'utilisateur courant/ssh)
    print("✅ Fichier .env créé")


def create_admin_user(target_dir, config, user, sudo_password=None, ssh=None):
    """Crée le compte admin dans la base de données."""
    gnmanager_path = os.path.join(target_dir, 'gnmanager')
    admin_config = config.get('admin', {})
    
    admin_email = admin_config.get('email', 'admin@example.com')
    admin_password = admin_config.get('password', 'admin')
    admin_nom = admin_config.get('nom', 'Admin')
    admin_prenom = admin_config.get('prenom', 'Super')
    
    print(f"👤 Création du compte admin: {admin_email}")
    
    # Script Python pour créer l'admin
    # Note: On doit échapper les quotes pour la ligne de commande
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
    # Échappement pour passer le script en ligne de commande
    script_oneliner = script.replace('\n', '; ').replace('"', '\\"')
    
    # Plus simple: écrire le script dans un fichier temporaire sur la cible et l'exécuter
    script_name = "init_admin.py"
    if ssh:
        with open(script_name, 'w') as f:
            f.write(script)
        sftp = ssh.open_sftp()
        remote_script = os.path.join(gnmanager_path, script_name)
        sftp.put(script_name, remote_script)
        sftp.close()
        os.remove(script_name)
        
        run_command(f"export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv run python {script_name}", cwd=gnmanager_path, ssh=ssh)
        run_command(f"rm {script_name}", cwd=gnmanager_path, ssh=ssh)
    else:
        local_script = os.path.join(gnmanager_path, script_name)
        with open(local_script, 'w') as f:
            f.write(script)
        run_command(f"export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv run python {script_name}", cwd=gnmanager_path)
        os.remove(local_script)
        
    print("✅ Compte admin configuré")


def import_test_data(target_dir, user, sudo_password=None, ssh=None):
    """Importe les données de test depuis config/."""
    gnmanager_path = os.path.join(target_dir, 'gnmanager')
    print("📊 Import des données de test...")
    run_command(
        "export PATH=$PATH:$HOME/.local/bin:$HOME/.cargo/bin && uv run python manage_db.py import -f config/ --clean",
        cwd=gnmanager_path,
        ssh=ssh
    )
    print("✅ Données de test importées")


def start_systemd_service(sudo_password=None, ssh=None):
    """Démarre le service systemd."""
    print("🚀 Démarrage du service systemd...")
    run_command("sudo systemctl start gnmanager.service", sudo_password=sudo_password, ssh=ssh)
    print("✅ Service systemd démarré")


def main():
    parser = argparse.ArgumentParser(
        description='Déploiement production GN Manager (Local ou Remote)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Déploiement complet avec systemd et données de test
  export GNMANAGER_USER=gnmanager
  export GNMANAGER_PWD=secret
  python fresh_deploy.py /opt --systemd --create-test-db
        """
    )
    
    parser.add_argument(
        'target_dir',
        nargs='?',
        default='/opt',
        help='Répertoire parent d\'installation (défaut: /opt)'
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
        '--config',
        default='./config/deploy_config.yaml',
        help='Chemin vers deploy_config.yaml (défaut: ./config/deploy_config.yaml)'
    )
    
    args = parser.parse_args()
    
    # Charger la configuration
    config = load_config(args.config)
    
    # Déterminer si local ou distant
    deploy_config = config.get('deploy', {})
    machine_name = deploy_config.get('machine_name', 'localhost')
    port = deploy_config.get('port', 5000)
    
    is_remote = machine_name not in ['localhost', '127.0.0.1', '0.0.0.0']
    
    # Vérifier les variables d'environnement
    user = os.environ.get('GNMANAGER_USER')
    if not user:
        print("❌ Variable d'environnement GNMANAGER_USER non définie")
        sys.exit(1)
    
    sudo_password = os.environ.get('GNMANAGER_PWD')
    if not sudo_password:
        print("⚠️  Variable d'environnement GNMANAGER_PWD non définie")
        print("   Mode interactif pour sudo")
    
    ssh = None
    if is_remote:
        if not sudo_password:
            print("❌ Pour le déploiement distant, GNMANAGER_PWD est obligatoire (connexion SSH).")
            sys.exit(1)
        ssh = connect_ssh(machine_name, user, sudo_password)
    
    print("=" * 70)
    print("🚀 DÉPLOIEMENT PRODUCTION GN MANAGER")
    print("=" * 70)
    print(f"🎯 Mode: {'REMOTE (' + machine_name + ')' if is_remote else 'LOCAL'}")
    print(f"📁 Répertoire cible: {args.target_dir}")
    print(f"👤 Utilisateur: {user}")
    print("=" * 70)
    
    try:
        # 1. Arrêt des services
        if args.systemd:
            stop_systemd_service(sudo_password, ssh)
        
        if args.kill:
            kill_port_processes(port, sudo_password, ssh)
        
        # 2. Backup de l'ancien déploiement
        rename_old_deployment(args.target_dir, ssh, sudo_password)
        
        # 3. Clone du repository
        clone_repository(args.target_dir, user, sudo_password, ssh)
        
        # 4. Configuration de la propriété
        setup_ownership(args.target_dir, user, sudo_password, ssh)
        
        # 5. Copie de la configuration
        copy_config(args.config, args.target_dir, ssh)
        
        # 6. Installation des dépendances
        # user=None car on ne veut PAS utiliser sudo (le dossier nous appartient et on veut garder le PATH)
        install_dependencies(args.target_dir, None, sudo_password, ssh)
        
        # 7. Création du fichier .env
        create_env_file(args.target_dir, config, None, sudo_password, ssh)
        
        # 8. Création du compte admin
        create_admin_user(args.target_dir, config, None, sudo_password, ssh)
        
        # 9. Import des données de test (optionnel)
        if args.create_test_db:
            import_test_data(args.target_dir, None, sudo_password, ssh)
        
        # 10. Démarrage du service (optionnel)
        if args.systemd:
            start_systemd_service(sudo_password, ssh)
        
        print("=" * 70)
        print("✅ DÉPLOIEMENT TERMINÉ AVEC SUCCÈS!")
        print("=" * 70)
        
        if ssh:
            ssh.close()
            
    except Exception as e:
        print("=" * 70)
        print(f"❌ ERREUR LORS DU DÉPLOIEMENT: {e}")
        # import traceback
        # traceback.print_exc()
        print("=" * 70)
        if ssh:
            ssh.close()
        sys.exit(1)


if __name__ == '__main__':
    main()
