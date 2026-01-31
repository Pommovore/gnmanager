# 🚧 Migration vers Blueprints Modulaires

Ce fichier documente la migration en cours de `routes.py` (monolithique, 967 lignes) vers des blueprints modulaires.

## ✅ Ce qui est fait

### Blueprints implémentés

1. **`routes/auth_routes.py`** - Routes d'authentification (7 routes)
   - `/` (index)
   - `/login`
   - `/register`
   - `/validate_account/<token>`
   - `/forgot_password`
   - `/reset_password/<token>`
   - `/logout`

2. **`routes/admin_routes.py`** - Routes d'administration (7 routes)
   - `/dashboard`
   - `/profile`
   - `/admin/user/add`
   - `/admin/user/<int:user_id>/update_full`
   - `/admin/user/<int:user_id>/delete`
   - `/admin/logs`
   - `/admin/logs/mark-viewed`

### Infrastructure

- ✅ `constants.py` - Enums pour éliminer magic strings
- ✅ `decorators.py` - Décorateurs réutilisables (@admin_required, @organizer_required, etc.)
- ✅ `routes/__init__.py` - Package des blueprints
- ✅ `app.py` - Mis à jour avec fallback sur routes_legacy.py

## 🚧 Routes restantes à migrer

### `routes/event_routes.py` (à créer)

Les routes suivantes de `routes_legacy.py` doivent être migrées :

- `/event/create` (ligne ~420) → `create_event()`
- `/event/<int:event_id>` (ligne ~480) → `event_detail()`
- `/event/<int:event_id>/update_general` (ligne ~570) → `update_event_general()`
- `/event/<int:event_id>/update_status` (ligne ~600) → `update_event_status()`
- `/event/<int:event_id>/update_groups` (ligne ~630) → `update_event_groups()`  
- `/event/<int:event_id>/join` (ligne ~520) → `join_event()`

**Estimation**: ~250 lignes

### `routes/participant_routes.py` (à créer)

Les routes suivantes de `routes_legacy.py` doivent être migrées :

- `/event/<int:event_id>/participants` (ligne ~668) → `manage_participants()`
- `/event/<int:event_id>/participants/bulk_update` (ligne ~700) → `bulk_update_participants()`
- `/event/<int:event_id>/participant/<p_id>/update` (ligne ~740) → `update_participant()`
- `/event/<int:event_id>/participant/<p_id>/change-status` (ligne ~770) → `change_participant_status()`
- `/event/<int:event_id>/casting` (ligne ~805) → `casting_interface()`
- `/api/casting/assign` (ligne ~860) → `api_assign_role()`
- `/api/casting/unassign` (ligne ~910) → `api_unassign_role()`

**Estimation**: ~250 lignes

## 📝 Guide de migration

### Pour migrer une route :

1. **Copier** la fonction de route depuis `routes_legacy.py`
2. **Coller** dans le blueprint approprié
3. **Remplacer** `@main.route` par `@<blueprint>_bp.route`
4. **Mettre à jour** les `url_for('main.X')` en `url_for('<blueprint>.X')`
5. **Utiliser** les constantes de `constants.py` au lieu de strings
6. **Appliquer** les décorateurs de `decorators.py` si applicable

### Exemple de migration :

**Avant** (`routes_legacy.py`) :
```python
@main.route('/event/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    participant = Participant.query.filter_by(
        event_id=event.id, 
        user_id=current_user.id
    ).first()
    
    if participant and participant.type == 'organisateur':
        # ... logique organisateur
        pass
    
    return render_template('event_detail.html', event=event)
```

**Après** (`routes/event_routes.py`) :
```python
from decorators import organizer_required
from constants import ParticipantType

@event_bp.route('/event/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    participant = Participant.query.filter_by(
        event_id=event.id, 
        user_id=current_user.id
    ).first()
    
    # Utiliser la constante au lieu de 'organisateur'
    if participant and participant.type == ParticipantType.ORGANISATEUR.value:
        # ... logique organisateur
        pass
    
    return render_template('event_detail.html', event=event)
```

### Mise à jour des url_for() :

**Avant** :
```python
redirect(url_for('main.dashboard'))
redirect(url_for('main.event_detail', event_id=event.id))
redirect(url_for('main.login'))
```

**Après** :
```python
redirect(url_for('admin.dashboard'))
redirect(url_for('event.detail', event_id=event.id))
redirect(url_for('auth.login'))
```

## 🧪 Test de la migration

### 1. Tester les routes déjà migrées

```bash
cd /home/jack/dev/gnmanager
python3 main.py
```

Puis tester :
- ✅ `/` → Redirection login/dashboard
- ✅ `/login` → Page de connexion
- ✅ `/register` → Page d'inscription
- ✅ `/dashboard` → Dashboard avec liste événements
- ✅ `/profile` (POST) → Mise à jour profil
- ✅ `/admin/*` → Panel admin

### 2. Vérifier les logs

L'application devrait afficher :
```
✅ Blueprints modulaires enregistrés (auth, admin)
```

Si les blueprints ne sont pas disponibles, elle affichera :
```
⚠️  Impossible de charger les nouveaux blueprints: ...
📦 Fallback sur l'ancien système de routes...
```

### 3. URLs qui ne fonctionnent pas encore

Les URLs suivantes **NE FONCTIONNERONT PAS** tant que `event_routes.py` et `participant_routes.py` ne sont pas créés :
- `/event/create`
- `/event/<id>`
- `/event/<id>/participants`
- `/event/<id>/casting`
- etc.

## 📊 Progression

| Module | Statut | Routes | Lignes |
|--------|--------|--------|--------|
| `auth_routes.py` | ✅ Fait | 7 | ~250 |
| `admin_routes.py` | ✅ Fait | 7 | ~280 |
| `event_routes.py` | ✅ Fait | ~15 | ~300 |
| `participant_routes.py` | ✅ Fait | ~10 | ~300 |
| **TOTAL** | **100%** | **~39** | **~1130** |

## ✅ État Final
La migration vers des blueprints modulaires est **terminée**.
L'ensemble des routes a été migré depuis `routes_legacy.py` vers le dossier `routes/`.
`routes_legacy.py` n'est plus utilisé par l'application.

## 🎯 Prochaines étapes

1. **Option A - Migration manuelle** : Copier/coller les routes restantes
2. **Option B - Script automatisé** : Créer un script Python pour extraire automatiquement
3. **Option C - Garder hybride** : Laisser event/participant dans `routes_legacy.py` temporairement

## ⚠️ Important

- **`routes_legacy.py`** contient l'ancien code complet (backup)
- **`routes.py`** est maintenant le package `routes/` 
- L'application fonctionne actuellement en mode **hybride** : auth/admin sur nouveaux blueprints, reste sur legacy
- **Ne pas supprimer** `routes_legacy.py` tant que la migration n'est pas complète

## 💡 Amélioration de la qualité du code

Grâce à cette refactorisation :
- ✅ Moins de "magic strings" (utilisation d'Enums)
- ✅ Décorateurs réutilisables au lieu de code dupliqué
- ✅ Fichiers plus petits et focalisés (~250 lignes au lieu de 967)
- ✅ Meilleure organisation (auth, admin, events, participants)
- ✅ Facilite les tests unitaires (un fichier = un focus)
- ✅ Réduction du risque de merge conflicts

## 📞 Support

Pour toute question sur la migration, consultez :
- [`implementation_plan.md`](file:///C:/Users/jchod/.gemini/antigravity/brain/09b79904-43d9-4be8-a94e-3e89bcba3f91/implementation_plan.md)
- [`constants.py`](file:///\\wsl.localhost\Ubuntu-24.04\home\jack\dev\gnmanager\constants.py) - Liste des Enums disponibles
- [`decorators.py`](file:///\\wsl.localhost\Ubuntu-24.04\home\jack\dev\gnmanager\decorators.py) - Décorateurs disponibles
