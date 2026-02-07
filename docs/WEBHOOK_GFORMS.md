# 🔗 Intégration Google Forms

Ce document explique comment connecter un formulaire **Google Forms** à **GNôle** pour importer automatiquement les inscriptions et gérer les données via l'interface dédiée.

## 1. Concept 💡

L'intégration permet d'automatiser le flux suivant :
1.  Un participant remplit votre Google Form.
2.  Un script (Apps Script) hébergé sur le formulaire détecte la soumission.
3.  Le script envoie les réponses (JSON) sécurisées à votre instance GNôle via un Webhook.
4.  **GNôle** traite les données :
    *   Identifie ou crée l'**Utilisateur** (basé sur l'email).
    *   Crée une inscription **Participant** avec le statut `"À valider"`.
    *   Stocke la soumission dans une base de données structurée (`GFormsSubmission`).
5.  Les organisateurs peuvent visualiser, trier et colorer les réponses dans l'onglet **GForms** de l'événement.

## 2. Prérequis ✅

*   Votre instance GNôle doit être accessible depuis Internet (URL publique HTTPS).
*   Vous devez être **Organisateur** de l'événement concerné.
*   Vous devez avoir les droits d'édition sur le Google Form.

## 3. Configuration Initiale 🛠️

### A. Côté GNôle
1.  Allez dans l'onglet **"Généralités"** de votre événement (Gestion Organisateur).
2.  Dans la section **"Formulaire Google & Webhook"** :
    *   Cliquez sur **"Générer"** si le secret n'existe pas.
    *   Notez le **Secret Webhook** (ex: `e4f5a...`).
    *   Notez l'URL de votre instance (ex: `https://mon-gn.com/api/webhook/gform`).

### B. Côté Google Forms (Installation du Script)
1.  Ouvrez votre formulaire en modification.
2.  Allez dans **Paramètres** et activez **"Collecter les adresses e-mail"**.
3.  Cliquez sur les **3 points verticaux** (en haut à droite) → **Apps Script**.
4.  Copiez le contenu du fichier [`static/GOOGLE_APPS_SCRIPT.js`](../static/GOOGLE_APPS_SCRIPT.js).
5.  Collez-le dans l'éditeur Apps Script (remplacez tout le contenu existant).
6.  **Configurez les variables** au début du fichier :
    ```javascript
    var API_URL = "https://votre-site.com/api/webhook/gform";
    var API_SECRET = "votre_secret_copié_depuis_gnole";
    ```
7.  Sauvegardez (`Ctrl + S`).

### C. Activation du Déclencheur (Trigger) ⏰
1.  Dans Apps Script, menu de gauche : **Déclencheurs** (icône réveil).
2.  **Ajouter un déclencheur** (bouton bleu en bas à droite).
3.  Configuration :
    *   Fonction : `sendToWebapp`
    *   Source de l'événement : `Dans le formulaire`
    *   Type d'événement : `Lors de l'envoi du formulaire`
4.  **Enregistrer** et autoriser l'accès (si demandé, cliquez sur "Advanced" -> "Go to... (unsafe)").

## 4. Gestion des Données (Interface GForms) 📊

Une fois les données reçues, l'onglet **"GForms"** de votre événement (à côté de Casting, Participants...) devient votre centre de contrôle.

### A. Onglet "Formulaires"
Affiche la liste de toutes les soumissions reçues.
- **Tableau** : Voir qui a répondu et quand.
- **Détails** : Cliquez sur une ligne pour voir toutes les réponses.
- **Type d'ajout** : Indique si c'est une création de compte ("créé") ou une mise à jour ("mis à jour").

### B. Onglet "Catégories"
Permet de définir des catégories pour organiser les champs du formulaire.
- Créez des catégories (ex: "HRP", "Généralités", "Logistique").
- Assignez une **couleur** à chaque catégorie.
- Ordonnez-les par glisser-déposer (ou numéro de position).

### C. Onglet "Champs" (Settings)
C'est ici que la magie opère. GNôle détecte tous les champs uniques présents dans les soumissions reçues.
- **Mappage** : Associez chaque champ détecté (ex: "Régime alimentaire") à une **Catégorie** (ex: "Logistique").
- Une fois mappé, le champ apparaîtra coloré et trié dans l'affichage des détails d'une soumission.

## 5. Dépannage 🐛

*   **Rien n'apparaît dans GNôle ?**
    *   Vérifiez les **Exécutions** dans Apps Script (Menu de gauche).
    *   Si erreur `401` ou `403` : Vérifiez votre `API_SECRET`.
    *   Si erreur `500` : Erreur serveur GNôle (vérifiez les logs serveur).

*   **Champs non détectés ?**
    *   Les champs n'apparaissent dans "Champs" qu'une fois qu'au moins une soumission contenant ce champ a été reçue. Soumettez un formulaire de test rempli à 100%.

*   **Doublons ?**
    *   Le système utilise l'email pour dédoublonner les participants. Si un utilisateur utilise le même email, sa fiche participant est mise à jour.
