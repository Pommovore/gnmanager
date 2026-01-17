L'application requiert des identifiants pour l'authentification Google :

```
GOOGLE_CLIENT_ID=votre_client_id
GOOGLE_CLIENT_SECRET=votre_client_secret
```

Pour obtenir ces identifiants, vous devez enregistrer votre application sur la **Google Cloud Console**. C'est l'étape indispensable pour permettre à votre application d'interagir avec l'API Google Docs de manière sécurisée.

Voici la procédure pas à pas :

### 1. Créer un projet sur Google Cloud

1. Rendez-vous sur la [Google Cloud Console](https://console.cloud.google.com/).
2. Connectez-vous avec votre compte Google.
3. Cliquez sur la liste déroulante des projets en haut à gauche et sélectionnez **"Nouveau projet"**.
4. Donnez-lui un nom (ex: "Mon App Export Docs") et validez.

### 2. Activer l'API Google Docs et Google Drive

Pour que votre application puisse créer des documents, elle a besoin d'autorisations spécifiques :

1. Dans la barre de recherche en haut, tapez **"Google Docs API"** et cliquez sur le résultat.
2. Cliquez sur le bouton **Activer**.
3. Faites la même chose pour l'**"API Google Drive"** (souvent nécessaire pour gérer l'export de fichiers).

### 3. Configurer l'écran de consentement OAuth

Avant de générer les clés, Google doit savoir ce que l'utilisateur verra lors de sa connexion :

1. Allez dans l'onglet **"Écran de consentement OAuth"** (menu latéral gauche).
2. Choisissez le type d'utilisateur **"Externe"** (si vous voulez que n'importe quel compte Google puisse l'utiliser).
3. Remplissez les informations obligatoires (Nom de l'application, email de support).
4. À l'étape des **Scopes** (Champs d'application), ajoutez :
* `https://www.googleapis.com/auth/documents`
* `https://www.googleapis.com/auth/drive.file`



---

### 4. Créer les identifiants (Client ID et Secret)

C'est ici que vous récupérez vos fameuses clés :

1. Cliquez sur l'onglet **"Identifiants"** dans le menu de gauche.
2. Cliquez sur **"+ Créer des identifiants"** en haut, puis choisissez **"ID de client OAuth"**.
3. Sélectionnez le **Type d'application** :
* S'il s'agit d'un site web, choisissez **"Application Web"**.


4. **Important :** Dans la section **"Origines JavaScript autorisées"**, ajoutez l'URL de votre site (ex: `http://localhost:3000` ou `https://votre-site.com`).
5. Dans **"URI de redirection autorisés"**, ajoutez l'URL exacte où Google doit renvoyer l'utilisateur après la connexion (souvent fourni dans la documentation de votre webapp).
6. Cliquez sur **Créer**.

---

### Résultat

Une fenêtre contextuelle s'affichera avec :

* **Votre ID de client** (`GOOGLE_CLIENT_ID`)
* **Votre code secret du client** (`GOOGLE_CLIENT_SECRET`)

### Quelques conseils de sécurité :

* **Ne partagez jamais** votre `CLIENT_SECRET` sur un dépôt public (GitHub, etc.). Utilisez un fichier `.env`.
* Tant que votre application est en mode "Test" dans la console Google, seuls les utilisateurs ajoutés manuellement dans la section "Utilisateurs de test" pourront se connecter.
