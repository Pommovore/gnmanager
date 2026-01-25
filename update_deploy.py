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
    parser.add_argument("--config", default="config/deploy_config.yaml", help="Fichier de configuration")
    parser.add_argument("--key", help="Chemin vers la clé SSH privée")
    parser.add_argument("--systemd", action="store_true", help="Redémarrer le service systemd")
    args = parser.parse_args()

    # Charger la config
    if not os.path.exists(args.config):
        print(f"❌ Config introuvable: {args.config}")
        sys.exit(1)
        
    with open(args.config) as f:
        config = yaml.safe_load(f)

    if config.get('location') != 'remote':
        print("❌ Ce script est conçu pour le déploiement 'remote' uniquement.")
        sys.exit(1)

    deploy_conf = config['deploy']
    host = deploy_conf['machine_name']
    target_dir = deploy_conf.get('target_directory', '/opt/gnmanager')
    app_dir = target_dir # Correction: Déploiement direct dans le dossier cible, pas de sous-dossier gnmanager

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
        print("🛑 Arrêt du service gnmanager...")
        if not run_remote(ssh, "systemctl stop gnmanager", sudo=True, password=password):
            print("⚠️  Le service n'a pas pu être arrêté (peut-être pas démarré ?)")
    else:
        print("ℹ️  Option systemd désactivée: le service ne sera pas arrêté.")

    # 3. Création archive locale
    print("📦 Création de l'archive locale (git tracked only)...")
    
    # 3.1 Générer fichier version temporaire
    # 3.1 Générer fichier version temporaire
    version_str = "dev"
    try:
        # 1. Get last commit date formatted
        ts = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y%m%d_%H%M%S"], 
            text=True
        ).strip()
        
        # 2. Get latest tag
        try:
            tag = subprocess.check_output(
                ["git", "describe", "--tags", "--abbrev=0"], 
                text=True, 
                stderr=subprocess.DEVNULL
            ).strip()
        except subprocess.CalledProcessError:
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
        # On archive HEAD + le fichier .deploy-version manuellement
        # git archive ne prend que ce qui est commité.
        # Astuce: on utilise tar pour combiner le résultat de git archive + le fichier version
        
        # 1. Archive git
        subprocess.run(
            f"git archive --format=tar --output=git_content.tar HEAD",
            shell=True, check=True
        )
        
        # 2. Ajouter le fichier version (append)
        subprocess.run(
            f"tar -rf git_content.tar .deploy-version",
            shell=True, check=True
        )
        
        # 3. Gzip
        subprocess.run(
            f"gzip -c git_content.tar > {archive_name}",
            shell=True, check=True
        )
        
        # Clean temp tar and version file
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
        # On s'assure que le dossier appartient à l'utilisateur qui va écrire (ou root via sudo)
        # Ici on extrait avec sudo, donc root, mais pour l'appli on voudra peut-etre chown après
        
    # On utilise tar pour extraire par dessus l'existant
    # --no-same-owner pour éviter les problèmes de permissions si on n'est pas root
    cmd_extract = f"tar -xzf {remote_tmp} -C {app_dir} --overwrite"
    if not run_remote(ssh, cmd_extract, sudo=True, password=password):
        print("❌ Erreur lors de l'extraction.")
        ssh.close()
        # os.remove(archive_name) # Keep for debug if needed? Nah
        sys.exit(1)
    
    # Rétablir les permissions (au cas où on a créé le dossier ou écrasé des fichiers)
    # On suppose que l'utilisateur du service est le même que le user SSH pour simplifier, 
    # ou on chown vers le user spécifié dans la config s'il y en avait un.
    # Dans le doute, on chown vers le user SSH connecté (souvent 'gnmanager' ou 'jack')
    # Pour être propre, on devrait chown vers le user du service systemd, mais on ne le connait pas ici facilement.
    # On va chown vers le user SSH pour garantir qu'on peut y retoucher plus tard.
    run_remote(ssh, f"chown -R {user}:{user} {app_dir}", sudo=True, password=password)
        
    # Nettoyage remote
    run_remote(ssh, f"rm {remote_tmp}")

    # 6. Relance service (Optionnel)
    if args.systemd:
        print("▶️  Redémarrage du service...")
        if run_remote(ssh, "systemctl start gnmanager", sudo=True, password=password):
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
