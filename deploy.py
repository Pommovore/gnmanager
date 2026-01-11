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

def run_command_remote(ssh, command):
    print(f"[EXT] {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    while True:
        line = stdout.readline()
        if not line:
            break
        print(line.strip())
    
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        print(f"Erreur commande distante ({exit_status}): {stderr.read().decode()}")
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

def deploy_remote(config):
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

    # 4. Data
    answer = input("Voulez-vous importer les données de test sur le serveur distant ? (o/n) : ").strip().lower()
    if answer == 'o' or answer == 'y':
        run_command_remote(ssh, f"{py_cmd} generate_csvs.py")
        run_command_remote(ssh, f"{py_cmd} import_csvs.py")

    # 5. Run App
    print("Lancement de l'application...")
    env_str = f"FLASK_HOST=0.0.0.0 FLASK_PORT={port}"
    
    # Run in background via nohup
    # Use bash -c to ensure source works with nohup if needed, though usually just chaining works if shell supports it.
    # ssh exec_command usually uses user's shell (often bash).
    # nohup command &
    run_command_remote(ssh, f"cd {target_dir} && {env_str} nohup bash -c '{uv_env}{py_cmd} main.py' > app.log 2>&1 &")
    
    print(f"Application lancée sur http://{host}:{port}")
    ssh.close()

def deploy_local(config, mode='local'):
    # Defaults
    host = '0.0.0.0'
    port = 5000
    target_dir = './'
    
    
    print(f"Mode de déploiement: {mode}")

    # Install
    print("--- 1. Installation ---")
    if shutil.which('uv'):
        run_command_local("uv sync")
    else:
        run_command_local("pip install -r requirements.txt")
        
    # Data
    print("--- 2. Données ---")
    answer = input("Voulez-vous importer les données de test ? (o/n) : ").strip().lower()
    if answer in ['o', 'y']:
        cmd_prefix = "uv run python" if shutil.which('uv') else "python"
        run_command_local(f"{cmd_prefix} generate_csvs.py")
        run_command_local(f"{cmd_prefix} import_csvs.py")

    # Run
    print("--- 3. Lancement ---")
    env = os.environ.copy()
    env['FLASK_HOST'] = str(host)
    env['FLASK_PORT'] = str(port)
    
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
    args = parser.parse_args()

    print(f"=== GN MANAGER DEPLOY (Config: {args.dpcfg}) ===")
    config = load_config(args.dpcfg)
    
    mode = 'local'
    if config and 'location' in config:
        mode = config['location']
    elif is_replit():
        mode = 'Replit'
        
    if mode == 'remote':
        deploy_remote(config)
    elif mode == 'Replit':
        deploy_local(config, mode='Replit')
    else:
        # local
        deploy_local(config, mode='local')

if __name__ == "__main__":
    main()
