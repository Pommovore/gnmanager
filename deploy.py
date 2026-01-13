import os
import sys
import subprocess
import shutil
import yaml
import time
import argparse

try:
    import paramiko
except ImportError:
    paramiko = None

def load_config(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    print(f"Attention: Fichier de configuration non trouvé: {path}")
    return None

def is_replit():
    return os.getenv('REPLIT_ID') is not None or os.path.exists('.replit')

def run_command_local(command, cwd=None, env=None):
    try:
        subprocess.check_call(command, shell=True, cwd=cwd, env=env)
        return True
    except subprocess.CalledProcessError:
        print(f"Erreur commande locale: {command}")
        return False

def run_command_remote(ssh, command, input_text=None):
    print(f"[EXT] {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    
    if input_text:
        stdin.write(input_text + '\n')
        stdin.flush()
        
    while True:
        line = stdout.readline()
        if not line:
            break
        print(line.strip())
    
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        # Sudo -S outputs the prompt to stderr usually, so we might see it there
        err_msg = stderr.read().decode()
        if "[sudo] password" not in err_msg: # Ignore standard password prompt in logs if possible, or just print it
             print(f"Erreur commande distante ({exit_status}): {err_msg}")
        return False
    return True

def upload_files(ssh, local_path, remote_path):
    sftp = ssh.open_sftp()
    
    try:
        sftp.stat(remote_path)
    except IOError:
        pass 
        
    print(f"Transfert de {local_path} vers {remote_path}...")
    
    for root, dirs, files in os.walk(local_path):
        if '.git' in root or '__pycache__' in root or '.venv' in root:
            continue
            
        rel_path = os.path.relpath(root, local_path)
        remote_root = os.path.join(remote_path, rel_path)
        if rel_path == '.':
            remote_root = remote_path
            
        try:
            sftp.stat(remote_root)
        except IOError:
            sftp.mkdir(remote_root)
            
        for file in files:
            if file.endswith('.pyc') or file == 'deploy_config.yaml': 
                continue
            
            local_file = os.path.join(root, file)
            remote_file = os.path.join(remote_root, file)
            sftp.put(local_file, remote_file)
            
    sftp.close()
    print("Transfert terminé.")

def deploy_remote(config, args):
    if not config or 'deploy' not in config:
        print("Erreur: Section 'deploy' manquante pour le déploiement distant.")
        return

    deploy_cfg = config['deploy']
    host = deploy_cfg.get('machine_name')
    port = deploy_cfg.get('port', 8880)
    target_dir = deploy_cfg.get('target_directory', '/tmp/gnmanager')
    
    user = os.environ.get('GNMANAGER_USER')
    pwd = os.environ.get('GNMANAGER_PWD')
    
    if not user or not pwd:
        print("Erreur: Les variables d'environnement GNMANAGER_USER et GNMANAGER_PWD doivent être définies.")
        return

    print(f"Connexion SSH vers {host}...")
    if paramiko is None:
        print("Paramiko manquant. Installez avec 'uv add paramiko'")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=user, password=pwd)
    except Exception as e:
        print(f"Erreur de connexion SSH: {e}")
        return
    # Early cleanup
    print(f"Arrêt du service et libération du port {port}...")
    # Stop systemd service
    run_command_remote(ssh, "sudo -S systemctl stop gnmanager.service", input_text=pwd)
    # Force kill port (just in case service didn't catch it or manual run)
    # Using || true to avoid error if nothing is listening
    run_command_remote(ssh, f"sudo -S fuser -k {port}/tcp || true", input_text=pwd)
    time.sleep(2)

    # 1. Create directory
    run_command_remote(ssh, f"mkdir -p {target_dir}")
    
    # 2. Upload files
    upload_files(ssh, '.', target_dir)
    
    # 3. Install dependencies (Remote)
    uv_env = "source $HOME/.local/bin/env && "
    
    check_uv = f"{uv_env}command -v uv"
    stdin, stdout, stderr = ssh.exec_command(check_uv)
    has_uv = stdout.channel.recv_exit_status() == 0
    
    if has_uv:
        print("Installation dépendances (uv)...")
        run_command_remote(ssh, f"{uv_env}cd {target_dir} && uv sync")
        py_cmd = f"{uv_env}cd {target_dir} && uv run python"
    else:
        print("Installation dépendances (pip)...")
        run_command_remote(ssh, f"cd {target_dir} && pip3 install -r requirements.txt")
        py_cmd = f"cd {target_dir} && python3"

    # 4. Data & DB Reset
    print("\n--- Configuration des données ---")
    if args.reset_db:
        reset_db = 'o'
    else:
        reset_db = input("Voulez-vous réinitialiser (SUPPRIMER) la base de données existante ? (o/n) : ").strip().lower()

    if reset_db in ['o', 'y']:
        print("Suppression de la base de données...")
        run_command_remote(ssh, f"cd {target_dir} && rm -f gnmanager.db instance/gnmanager.db")
    
    if args.import_data:
        answer = 'o'
    else:
        answer = input("Voulez-vous importer les données de test sur le serveur distant ? (o/n) : ").strip().lower()

    if answer in ['o', 'y']:
        print("\n--- Configuration du Compte Créateur ---")
        if args.admin_email:
             admin_email = args.admin_email
             print(f"Email (CLI) : {admin_email}")
        elif config and 'admin' in config and 'email' in config['admin']:
             admin_email = config['admin']['email']
             print(f"Email (Config) : {admin_email}")
        else:
             admin_email = input("Email de l'administrateur / créateur : ").strip() or "admin@gnmanager.fr"
             
        if args.admin_password:
             admin_pass = args.admin_password
             print("Mot de passe (CLI) : *****")
        elif config and 'admin' in config and 'password' in config['admin']:
             admin_pass = config['admin']['password']
             print("Mot de passe (Config) : *****")
        else:
             admin_pass = input("Mot de passe de l'administrateur : ").strip() or "admin1234"
             
        if args.admin_nom:
             admin_nom = args.admin_nom
        elif config and 'admin' in config and 'nom' in config['admin']:
             admin_nom = config['admin']['nom']
        else:
             admin_nom = input("Nom de famille : ").strip() or "Admin"
             
        if args.admin_prenom:
             admin_prenom = args.admin_prenom
        elif config and 'admin' in config and 'prenom' in config['admin']:
             admin_prenom = config['admin']['prenom']
        else:
             admin_prenom = input("Prénom : ").strip() or "System"
        
        # Escape quotes if necessary, simpler to assume basic chars for now
        gen_cmd = f"{py_cmd} generate_csvs.py --admin-email '{admin_email}' --admin-password '{admin_pass}' --admin-nom '{admin_nom}' --admin-prenom '{admin_prenom}'"
        
        run_command_remote(ssh, gen_cmd)
        run_command_remote(ssh, f"{py_cmd} import_csvs.py")

    # 5. Run App (Systemd adaptation)
    print("Mise à jour de la configuration et redémarrage du service...")
    
    # Générer le contenu du fichier .env pour le serveur distant
    env_lines = [
        f"FLASK_HOST=0.0.0.0",
        f"FLASK_PORT={port}",
        f"APP_PUBLIC_HOST={host}:{port}",
        "PYTHONUNBUFFERED=1"  # Forcer stdout non bufferisé pour la visibilité des logs
    ]
    
    # Ajouter la configuration email si disponible
    if config and 'email' in config:
        email_cfg = config['email']
        env_lines.append(f"MAIL_SERVER={email_cfg.get('server')}")
        env_lines.append(f"MAIL_PORT={email_cfg.get('port')}")
        env_lines.append(f"MAIL_USE_TLS={str(email_cfg.get('use_tls')).lower()}")
        env_lines.append(f"MAIL_USERNAME={email_cfg.get('username')}")
        mail_pwd = email_cfg.get('password')
        env_lines.append(f"MAIL_PASSWORD={mail_pwd}")
        env_lines.append(f"MAIL_DEFAULT_SENDER={email_cfg.get('default_sender')}")
        
    env_content = "\n".join(env_lines)
    
    # Write .env locally first (temp)
    with open('.env.deploy', 'w') as f:
        f.write(env_content)
        
    # Upload .env to remote
    remote_env_path = os.path.join(target_dir, '.env')
    print(f"Upload du fichier .env vers {remote_env_path}")
    sftp = ssh.open_sftp()
    sftp.put('.env.deploy', remote_env_path)
    sftp.close()
    
    # Remove local temp file
    if os.path.exists('.env.deploy'):
        os.remove('.env.deploy')
        
    # Restart Systemd Service
    # Use sudo -S to read password from stdin
    print("Redémarrage du service gnmanager.service...")
    run_command_remote(ssh, "sudo -S systemctl restart gnmanager.service", input_text=pwd)
    
    print(f"Déploiement terminé. Vérifiez le statut avec 'systemctl status gnmanager.service' sur le serveur.")
    ssh.close()

def deploy_local(config, args, mode='local'):
    # Defaults
    host = '0.0.0.0'
    port = 5000
    target_dir = './'
    
    
    print(f"Mode de déploiement: {mode}")

    # Early cleanup
    print(f"Arrêt du processus existant sur le port {port}...")
    run_command_local(f"fuser -k {port}/tcp") 
    time.sleep(1)

    # Install
    print("--- 1. Installation ---")
    if shutil.which('uv'):
        run_command_local("uv sync")
    else:
        run_command_local("pip install -r requirements.txt")
        
    # Data
    print("--- 2. Données ---")
    
    if args.reset_db:
        reset_db = 'o'
    else:
        reset_db = input("Voulez-vous réinitialiser (SUPPRIMER) la base de données existante ? (o/n) : ").strip().lower()
        
    if reset_db in ['o', 'y']:
        print("Suppression de la base de données...")
        if os.path.exists('gnmanager.db'):
            os.remove('gnmanager.db')
        if os.path.exists('instance/gnmanager.db'):
            os.remove('instance/gnmanager.db')

    if args.import_data:
        answer = 'o'
    else:
        answer = input("Voulez-vous importer les données de test ? (o/n) : ").strip().lower()
        
    if answer in ['o', 'y']:
        print("\n--- Configuration du Compte Créateur ---")
        if args.admin_email:
             admin_email = args.admin_email
             print(f"Email (CLI) : {admin_email}")
        elif config and 'admin' in config and 'email' in config['admin']:
             admin_email = config['admin']['email']
             print(f"Email (Config) : {admin_email}")
        else:
             admin_email = input("Email de l'administrateur / créateur : ").strip() or "admin@gnmanager.fr"
             
        if args.admin_password:
             admin_pass = args.admin_password
             print("Mot de passe (CLI) : *****")
        elif config and 'admin' in config and 'password' in config['admin']:
             admin_pass = config['admin']['password']
             print("Mot de passe (Config) : *****")
        else:
             admin_pass = input("Mot de passe de l'administrateur : ").strip() or "admin1234"
             
        if args.admin_nom:
             admin_nom = args.admin_nom
        elif config and 'admin' in config and 'nom' in config['admin']:
             admin_nom = config['admin']['nom']
        else:
             admin_nom = input("Nom de famille : ").strip() or "Admin"
             
        if args.admin_prenom:
             admin_prenom = args.admin_prenom
        elif config and 'admin' in config and 'prenom' in config['admin']:
             admin_prenom = config['admin']['prenom']
        else:
             admin_prenom = input("Prénom : ").strip() or "System"

        cmd_prefix = "uv run python" if shutil.which('uv') else "python"
        
        # Escape args for safety (basic)
        gen_cmd = f"{cmd_prefix} generate_csvs.py --admin-email \"{admin_email}\" --admin-password \"{admin_pass}\" --admin-nom \"{admin_nom}\" --admin-prenom \"{admin_prenom}\""
        
        run_command_local(gen_cmd)
        run_command_local(f"{cmd_prefix} import_csvs.py")

    # Run
    print("--- 3. Lancement ---")
    env = os.environ.copy()
    env['FLASK_HOST'] = str(host)
    env['FLASK_PORT'] = str(port)
    
    # Attempt to use configured machine name if available, else localhost
    public_host = "127.0.0.1:5000"
    if config and 'deploy' in config and 'machine_name' in config['deploy']:
         # Use configured machine name if explicitly testing "remote-like" locally or just consistency
         # But for local dev, usually localhost is safer.
         # Let's check: if user changes config to remote machine name but deploys local, 
         # they might want the link to point to remote? No, deploy_local runs locally.
         # Let's keep it simple: Local -> localhost:port. Remote -> machine_name:port
         pass
         
    env['APP_PUBLIC_HOST'] = f"{host}:{port}" if host != '0.0.0.0' else f"127.0.0.1:{port}"

    # Email Config (from config file)
    if config and 'email' in config:
        email_cfg = config['email']
        usr = email_cfg.get('username')
        mail_pwd = email_cfg.get('password') # Renamed to avoid shadowing SSH pwd
        snd = email_cfg.get('default_sender')
        
        env['MAIL_SERVER'] = str(email_cfg.get('server'))
        env['MAIL_PORT'] = str(email_cfg.get('port'))
        env['MAIL_USE_TLS'] = str(email_cfg.get('use_tls')).lower()
        env['MAIL_USERNAME'] = str(usr)
        env['MAIL_PASSWORD'] = str(mail_pwd)
        env['MAIL_DEFAULT_SENDER'] = str(snd)
    else:
        print("Attention: Configuration email manquante dans le fichier config.")
    
    if mode == 'Replit':
         print("Sur Replit, l'application est configurée pour 0.0.0.0:5000 par défaut.")
    
    cmd = "uv run python main.py" if shutil.which('uv') else "python main.py"
    try:
        subprocess.check_call(cmd, shell=True, env=env)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description='Script de déploiement GN Manager')
    parser.add_argument('--dpcfg', default='config/deploy_config.yaml', help='Chemin du fichier de configuration')
    parser.add_argument('--reset-db', action='store_true', help='Réinitialiser automatiquement la base de données')
    parser.add_argument('--import-data', action='store_true', help='Importer automatiquement les données de test')
    parser.add_argument('--admin-email', help="Email de l'administrateur")
    parser.add_argument('--admin-password', help="Mot de passe de l'administrateur")
    parser.add_argument('--admin-nom', help="Nom de l'administrateur")
    parser.add_argument('--admin-prenom', help="Prénom de l'administrateur")
    args = parser.parse_args()

    print(f"=== GN MANAGER DEPLOY (Config: {args.dpcfg}) ===")
    config = load_config(args.dpcfg)
    
    mode = 'local'
    if config and 'location' in config:
        mode = config['location']
    elif is_replit():
        mode = 'Replit'
        
    if mode == 'remote':
        deploy_remote(config, args)
    elif mode == 'Replit':
        deploy_local(config, args, mode='Replit')
    else:
        # local
        deploy_local(config, args, mode='local')

if __name__ == "__main__":
    main()
