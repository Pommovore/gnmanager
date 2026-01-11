# GN Manager

Application web de gestion pour les événements de Grandeur Nature (GN).

## Fonctionnalités
- Gestion des utilisateurs (admin, organisateurs, joueurs)
- Gestion des événements (création, visibilité, statuts)
- Gestion des rôles et inscriptions
- Système de paiement et suivi

## Prérequis
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommandé) pour la gestion des dépendances

## Installation et Déploiement

Le projet inclut un script de déploiement `deploy.py` qui gère l'installation des dépendances, la base de données et le lancement de l'application.

### Configuration

Le fichier `config/deploy_config.yaml` permet de configurer le déploiement :

```yaml
deploy:
  machine_name: "0.0.0.0"       # "0.0.0.0" pour local, ou nom de domaine/IP pour distant
  port: 5000                    # Port d'écoute
  target_directory: "./"        # Répertoire cible
```

### 1. Déploiement Local

Pour lancer l'application sur votre machine (ou sur Replit) :

1.  Assurez-vous que `machine_name` est configuré sur `localhost` ou `0.0.0.0`.
2.  Lancez le script :
    ```bash
    uv run python deploy.py
    ```
    *Le script installera les dépendances et proposera de générer des données de test.*

### 2. Déploiement Distant (SSH)

Pour déployer sur un serveur distant (ex: `minimoi.mynetgear.com`) :

1.  Modifiez `config/deploy_config.yaml` :
    ```yaml
    deploy:
      machine_name: "minimoi.mynetgear.com"
      port: 8880
      target_directory: "/opt/gnmanager/"
    ```

2.  Définissez les identifiants SSH via des variables d'environnement :
    ```bash
    export GNMANAGER_USER=votre_utilisateur
    export GNMANAGER_PWD=votre_mot_de_passe
    ```

3.  Lancez le déploiement depuis votre machine locale :
    ```bash
    uv run python deploy.py
    ```

Le script effectuera les actions suivantes :
- Connexion SSH au serveur distant.
- Transfert des fichiers via SFTP vers le répertoire cible.
- Installation des dépendances sur le serveur.
- (Optionnel) Génération et import des données de test.
- Lancement de l'application en arrière-plan (`nohup`).

## Données de Test

Le déploiement propose automatiquement de générer un jeu de données fictives :
- **Utilisateurs** : via `generate_csvs.py`
- **Import** : via `import_csvs.py`

Vous pouvez aussi lancer ces scripts manuellement :
```bash
uv run python generate_csvs.py
uv run python import_csvs.py
```
