#!/usr/bin/env python3
"""
Script de mise à jour rapide pour GN Manager (Production).

Ce script permet de mettre à jour le code sur le serveur distant sans redéployer
toute la base de données ni recréer l'environnement.

Actions :
1. Arrête le service systemd
2. Crée une archive locale des fichiers suivis par git
3. Upload et extrait l'archive sur le serveur
4. Redémarre le service
"""

import os
import sys
import subprocess
import argparse
import yaml
import time
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("❌ Erreur: 'paramiko' est requis. Installez-le avec: pip install paramiko")
    sys.exit(1)

def run_remote(ssh, cmd, sudo=False, password=None):
    """Exécute une commande sur le serveur distant."""
    # Afficher la commande AVANT d'ajouter le password pour ne pas le logger
    display_cmd = f"sudo {cmd}" if sudo else cmd
    print(f"🔧 [REMOTE] {display_cmd}")
    
    # Ajouter le password seulement pour l'exécution
    if sudo:
        cmd = f"echo '{password}' | sudo -S -p '' {cmd}"
    
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        err = stderr.read().decode().strip()
        print(f"❌ Erreur: {err}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Mise à jour rapide de GN Manager")
    
    # Groupe d'environnement mutuellement exclusif et OBLIGATOIRE
    env_group = parser.add_mutually_exclusive_group(required=True)
    env_group.add_argument('--prod', action='store_true', help='Environnement PRODUCTION')
    env_group.add_argument('--test', action='store_true', help='Environnement TEST')
    env_group.add_argument('--dev', action='store_true', help='Environnement DÉVELOPPEMENT')

    parser.add_argument("--key", help="Chemin vers la clé SSH privée")
    parser.add_argument("--systemd", action="store_true", help="Redémarrer le service systemd")
    parser.add_argument("--migrate", action="store_true", help="Exécuter la migration DB (migrate_to_v0_11.py)")
    args = parser.parse_args()

    # Détermination de l'environnement
    if args.prod:
        env_name = "prod"
        config_path = "config/deploy_config_prod.yaml"
        service_suffix = "" # gnole
    elif args.test:
        env_name = "test"
        config_path = "config/deploy_config_test.yaml"
        service_suffix = "_test" # gnole_test
    elif args.dev:
        env_name = "dev"
        config_path = "config/deploy_config_dev.yaml"
        service_suffix = "_dev" # gnole_dev
    
    service_name = f"gnole{service_suffix}" # systemctl prend le nom court ou long
    
    print(f"🌍 Environnement: {env_name.upper()}")
    print(f"⚙️  Config: {config_path}")
    print(f"🔧 Service: {service_name}")

    # Charger la config
    if not os.path.exists(config_path):
        # Fallback
        if os.path.exists("config/deploy_config.yaml"):
             print(f"⚠️  Config spécifique introuvable. Repli sur config/deploy_config.yaml")
             config_path = "config/deploy_config.yaml"
        else:
            print(f"❌ Config introuvable: {config_path}")
            sys.exit(1)
        
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if config.get('location') != 'remote':
        # On est laxiste ici ? Non, le script est fait pour le remote update.
        print("ℹ️  Note: config.location != 'remote'")

    deploy_conf = config.get('deploy', {})
    if not deploy_conf:
        print("❌ Section 'deploy' manquante dans la config.")
        sys.exit(1)
        
    host = deploy_conf['machine_name']
    
    # Détermination du dossier cible
    config_target_dir = deploy_conf.get('target_directory')
    if config_target_dir:
        app_dir = config_target_dir.rstrip('/')
    else:
        app_dir = f"/opt/gnmanager{service_suffix}"
    
    print(f"📂 Dossier cible: {app_dir}")

    # Credentials
    user = os.environ.get('GNMANAGER_USER', 'jack') # Default fallback
    password = os.environ.get('GNMANAGER_PWD')
    
    if not password and not args.key:
        print("❌ Erreur: Définissez GNMANAGER_PWD ou utilisez --key")
        sys.exit(1)

    # 1. Connexion SSH
    print(f"🔌 Connexion à {user}@{host}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        connect_kwargs = {'username': user}
        if args.key:
            connect_kwargs['key_filename'] = args.key
        if password:
            connect_kwargs['password'] = password
            
        ssh.connect(host, **connect_kwargs)
        print("✅ Connecté.")
    except Exception as e:
        print(f"❌ Échec connexion: {e}")
        sys.exit(1)

    # 2. Arrêt du service (Optionnel)
    if args.systemd:
        print(f"🛑 Arrêt du service {service_name}...")
        if not run_remote(ssh, f"systemctl stop {service_name}", sudo=True, password=password):
            print("⚠️  Le service n'a pas pu être arrêté (peut-être pas démarré ?)")
    else:
        print("ℹ️  Option systemd désactivée: le service ne sera pas arrêté.")

    # 3. Création archive locale
    print("📦 Création de l'archive locale (git tracked only)...")
    
    # 3.1 Générer fichier version temporaire
    version_str = "dev"
    try:
        # 0. Fetch tags
        subprocess.run(["git", "fetch", "origin", "--tags"], check=False, stderr=subprocess.DEVNULL)

        # 1. Get last commit date formatted
        ts = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y%m%d_%H%M%S"], 
            text=True
        ).strip()
        
        # 2. Get latest tag
        try:
            # Utilisation de la méthode triée par version (semver)
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
        print(f"⚠️ Erreur version: {e}")
        version_str = f"update_{int(time.time())}"
        
    print(f"🔖 Version: {version_str}")
    
    # Écrire .deploy-version
    with open(".deploy-version", "w") as f:
        f.write(version_str)
        
    archive_name = "gnmanager_update.tar.gz"
    try:
        # On archive HEAD + le fichier .deploy-version
        subprocess.run(
            f"git archive --format=tar --output=git_content.tar HEAD",
            shell=True, check=True
        )
        subprocess.run(
            f"tar -rf git_content.tar .deploy-version",
            shell=True, check=True
        )
        subprocess.run(
            f"gzip -c git_content.tar > {archive_name}",
            shell=True, check=True
        )
        
        os.remove("git_content.tar")
        os.remove(".deploy-version")
        
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de la création de l'archive.")
        if os.path.exists(".deploy-version"): os.remove(".deploy-version")
        if os.path.exists("git_content.tar"): os.remove("git_content.tar")
        ssh.close()
        sys.exit(1)

    # 4. Upload
    print(f"🚀 Transfert de {archive_name}...")
    sftp = ssh.open_sftp()
    remote_tmp = f"/tmp/{archive_name}"
    sftp.put(archive_name, remote_tmp)
    sftp.close()
    
    # 5. Extraction
    print(f"📂 Extraction dans {app_dir}...")
    
    # Vérifier si le dossier existe, sinon le créer
    check_dir_cmd = f"test -d {app_dir}"
    stdin, stdout, stderr = ssh.exec_command(check_dir_cmd)
    if stdout.channel.recv_exit_status() != 0:
        print(f"⚠️  Le dossier {app_dir} n'existe pas. Création...")
        if not run_remote(ssh, f"mkdir -p {app_dir}", sudo=True, password=password):
             print("❌ Impossible de créer le dossier destination.")
             sys.exit(1)
        
    cmd_extract = f"tar -xzf {remote_tmp} -C {app_dir} --overwrite"
    if not run_remote(ssh, cmd_extract, sudo=True, password=password):
        print("❌ Erreur lors de l'extraction.")
        ssh.close()
        sys.exit(1)
    
    # Rétablir les permissions
    run_remote(ssh, f"chown -R {user}:{user} {app_dir}", sudo=True, password=password)
        
    # Nettoyage remote
    run_remote(ssh, f"rm {remote_tmp}")

    # 5.5 Copie de la config correspondante (car git archive n'a peut-être pas la bonne config spécifique copiée sous config/deploy_config.yaml)
    # Dans une update rapide, on déploie le code, mais le fichier de config doit aussi être mis à jour si on a changé des trucs.
    # On va uploader le fichier de config local spécifique vers config/deploy_config.yaml distant.
    print(f"📋 Mise à jour de la configuration...")
    sftp = ssh.open_sftp()
    remote_config_path = os.path.join(app_dir, 'config', 'deploy_config.yaml')
    try:
        sftp.put(config_path, remote_config_path)
        print("✅ Configuration mise à jour.")
    except Exception as e:
        print(f"⚠️ Erreur mise à jour config: {e}")
    sftp.close()

    # 6. MIGRATION (Optionnel)
    if args.migrate:
        print("🏗️  Exécution de la migration de base de données...")
        migration_script = "scripts/migrate_v0_12_character_traits.py"
        # On vérifie si le script existe
        check_cmd = f"test -f {os.path.join(app_dir, migration_script)}"
        if run_remote(ssh, check_cmd, sudo=True, password=password):
             # On le lance avec uv run
             # IMPORTANT: avec sudo, $HOME devient /root, donc on force le path de l'utilisateur
             user_home = f"/home/{user}"
             migrate_cmd = f"bash -c 'cd {app_dir} && export PATH=$PATH:{user_home}/.local/bin:{user_home}/.cargo/bin && uv run python {migration_script}'"
             if run_remote(ssh, migrate_cmd, sudo=True, password=password):
                 print("✅ Migration terminée avec succès.")
             else:
                 print("❌ Erreur lors de la migration.")
        else:
            print(f"⚠️  Script de migration {migration_script} introuvable sur le serveur.")

    # 7. Relance service (Optionnel)
    if args.systemd:
        print("▶️  Redémarrage du service...")
        if run_remote(ssh, f"systemctl start {service_name}", sudo=True, password=password):
            print("✅ Service redémarré avec succès !")
        else:
            print("❌ Erreur lors du redémarrage du service.")
    else:
        print("ℹ️  Option systemd désactivée: le service ne sera pas redémarré.")

    # Nettoyage local
    os.remove(archive_name)
    ssh.close()
    print("\n✨ Mise à jour terminée !")

if __name__ == "__main__":
    main()
