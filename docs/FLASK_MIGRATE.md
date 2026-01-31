# Flask-Migrate - Gestion des Migrations de Base de Données

## Installation

Flask-Migrate est déjà installé et configuré dans `app.py`.

```bash
# Vérifier l'installation
uv run flask db --help
```

## Commandes Essentielles

### Initialisation (déjà fait)

```bash
# Initialiser le système de migrations (une seule fois)
uv run flask db init
```

### Créer une Migration

Après avoir modifié les modèles dans `models.py` :

```bash
# Générer automatiquement une migration
uv run flask db migrate -m "Description des changements"

# Exemple :
uv run flask db migrate -m "Add user avatar field"
```

**Important** : Toujours vérifier le fichier généré dans `migrations/versions/` avant de l'appliquer !

### Appliquer les Migrations

```bash
# Appliquer toutes les migrations en attente
uv run flask db upgrade

# Appliquer jusqu'à une révision spécifique
uv run flask db upgrade <revision_id>
```

### Annuler une Migration

```bash
# Revenir à la migration précédente
uv run flask db downgrade

# Revenir à une révision spécifique
uv run flask db downgrade <revision_id>
```

### Gestion de l'Historique

```bash
# Voir l'historique complet des migrations
uv run flask db history

# Voir la migration actuelle
uv run flask db current

# Voir les migrations en attente
uv run flask db heads
```

## Workflow de Développement

### 1. Modifier les Modèles

Modifiez vos models dans `models.py` :

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    # Nouveau champ
    bio = db.Column(db.Text)
```

### 2. Générer la Migration

```bash
uv run flask db migrate -m "Add bio field to User model"
```

### 3. Vérifier la Migration

Ouvrez le fichier dans `migrations/versions/XXXXX_add_bio_field_to_user_model.py` et vérifiez :
- Les colonnes ajoutées/modifiées sont correctes
- Les valeurs par défaut sont appropriées
- Pas de perte de données

### 4. Appliquer la Migration

```bash
# En développement
uv run flask db upgrade

# En production (avec backup d'abord !)
cp instance/gnmanager.db instance/gnmanager.db.backup
uv run flask db upgrade
```

### 5. Tester

Vérifiez que votre application fonctionne correctement avec le nouveau schéma.

## Déploiement en Production

### Checklist Pré-Déploiement

1. ✅ **Backup de la base de données**
   ```bash
   cp instance/gnmanager.db instance/gnmanager.db.backup-$(date +%Y%m%d_%H%M%S)
   ```

2. ✅ **Vérifier les migrations en attente**
   ```bash
   uv run flask db current
   uv run flask db heads
   ```

3. ✅ **Tester sur une copie**
   ```bash
   cp instance/gnmanager.db instance/test.db
   SQLALCHEMY_DATABASE_URI=sqlite:///instance/test.db uv run flask db upgrade
   ```

4. ✅ **Appliquer en production**
   ```bash
   uv run flask db upgrade
   ```

5. ✅ **Vérifier l'application**
   - Redémarrer l'application
   - Tester les fonctionnalités affectées
   - Vérifier les logs

### En cas de Problème

```bash
# Revenir en arrière
uv run flask db downgrade

# Restaurer le backup
rm instance/gnmanager.db
cp instance/gnmanager.db.backup instance/gnmanager.db
```

## Bonnes Pratiques

### ✅ À Faire

- 🔐 **Toujours faire un backup** avant `upgrade` en production
- 📝 **Écrire des messages de commit descriptifs** pour les migrations
- 🔍 **Vérifier manuellement** chaque migration générée
- ✅ **Tester sur une copie** avant la production
- 📊 **Committer les migrations** avec le code

### ❌ À Éviter

- ❌ Modifier manuellement la BDD sans créer de migration
- ❌ Supprimer des migrations déjà appliquées
- ❌ Modifier une migration après qu'elle ait été partagée/déployée
- ❌ Oublier de committer les fichiers de migration
- ❌ Appliquer des migrations non testées en production

## Commandes Avancées

### Marquer une Base Comme Migrée (Stamp)

Utilisé pour marquer une base existante comme étant à jour sans appliquer les migrations :

```bash
# Marquer la BDD actuelle comme étant à jour
uv run flask db stamp head

# Marquer à une révision spécifique
uv run flask db stamp <revision_id>
```

**Cas d'usage** : Base de données existante que vous voulez mettre sous contrôle de Flask-Migrate.

### Fusionner des Branches de Migrations

Si plusieurs développeurs créent des migrations simultanément :

```bash
# Créer une migration de fusion
uv run flask db merge -m "Merge migrations" <revision1> <revision2>
```

### Créer une Migration Vide

Pour des modifications personnalisées :

```bash
uv run flask db revision -m "Custom data migration"
```

Éditez ensuite le fichier généré pour ajouter votre logique personnalisée dans `upgrade()` et `downgrade()`.

## Dépannage

### La Migration Ne Détecte Pas Mes Changements

1. Vérifiez que vos modèles héritent de `db.Model`
2. Vérifiez que tous les modèles sont importés dans `models.py`
3. Essayez `uv run flask db migrate --autogenerate`

### Erreur "Can't locate revision identified by 'XXXXX'"

La base de données et les migrations sont désynchronisées :

```bash
# Voir l'état actuel
uv run flask db current
uv run flask db history

# Résoudre en stampant à la bonne révision
uv run flask db stamp <good_revision>
```

### Base de Données Verrouillée (SQLite)

```bash
# Vérifier les processus qui utilisent la DB
lsof instance/gnmanager.db

# Arrêter l'application
# Puis réessayer la migration
```

## Références

- [Documentation officielle Flask-Migrate](https://flask-migrate.readthedocs.io/)
- [Documentation Alembic](https://alembic.sqlalchemy.org/)
- [Tutoriels Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
