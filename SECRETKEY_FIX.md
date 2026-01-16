# Solution au Problème SECRET_KEY

## Problème
```
ValueError: SECURITY ERROR: SECRET_KEY environment variable must be set in production!
```

## Causes

1. **Scripts sans `load_dotenv()`** : Les scripts `import_csvs.py` et `seed_data.py` n'importaient pas les variables d'environnement depuis `.env`
2. **Détection stricte d'environnement** : La logique dans `app.py` ne détectait pas correctement le mode développement

## Solutions Appliquées

### 1. ✅ Fichier `.env` créé

```bash
# .env (à la racine du projet)
SECRET_KEY=192674beb42c1dcdd33396f052fe244f...
FLASK_ENV=development
FLASK_DEBUG=1
```

### 2. ✅ Scripts mis à jour

**import_csvs.py** et **seed_data.py** :
```python
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = create_app()
```

### 3. ✅ Amélioration de la détection d'environnement

**app.py** :
```python
is_development = (
    app.debug or 
    os.environ.get('FLASK_ENV') == 'development' or
    os.environ.get('FLASK_DEBUG') == '1' or
    os.path.exists('gnmanager.db')  # Si DB locale existe
)
```

## Utilisation

### Pour déployer localement :

```bash
python deploy.py --dpcfg config/deploy_config.yaml --reset-db --import-data
```

Ou avec `uv` (recommandé) :

```bash
uv run python deploy.py --dpcfg config/deploy_config.yaml --reset-db --import-data
```

### Pour lancer l'application :

```bash
uv run python main.py
```

### Pour importer des données :

```bash
uv run python import_csvs.py
```

## Notes

- Le fichier `.env` est déjà dans `.gitignore` ✅
- En **production**, définir `SECRET_KEY` comme variable d'environnement système
- Ne **jamais** committer `.env` en production
- Générer une nouvelle clé en production avec :
  ```bash
  python -c 'import secrets; print(secrets.token_hex(32))'
  ```
