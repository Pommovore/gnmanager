# 🔗 Intégration Google Forms (Webhook)

Ce document explique comment connecter un formulaire **Google Forms** à **GN Manager** pour importer automatiquement les inscriptions.

## 1. Concept 💡

L'intégration permet d'automatiser le flux suivant :
1.  Un participant remplit votre Google Form.
2.  Un script (Apps Script) hébergé sur le formulaire détecte la soumission.
3.  Le script envoie les réponses (JSON) sécurisées à votre instance GN Manager.
4.  **GN Manager** traite les données :
    *   Identifie ou crée l'**Utilisateur** (basé sur l'email).
    *   Crée une inscription **Participant** avec le statut `"À valider"`.
    *   Stocke toutes les réponses du formulaire dans le champ "Commentaire Global" du participant.

## 2. Prérequis ✅

*   Votre instance GN Manager doit être accessible depuis Internet (URL publique HTTPS).
*   Vous devez être **Organisateur** de l'événement concerné.
*   Vous devez avoir les droits d'édition sur le Google Form.

## 3. Configuration Côté GN Manager 🛠️

1.  Accédez à l'onglet **"Généralités"** de votre événement.
2.  Repérez la section **"Intégration Google Forms"**.
3.  Notez l'**URL du Webhook** (ex: `https://votre-gn.com/api/webhook/gform`).
4.  Cliquez sur **"Générer un Secret"** (si ce n'est pas déjà fait).
5.  Copiez ce **Secret Webhook** (une chaîne de caractères unique). 
    *   ⚠️ **Important** : Ce secret est unique pour *cet* événement. Il permet à GN Manager de savoir à quel événement rattacher les inscriptions.

## 4. Configuration Côté Google Forms 📝

### A. Paramètres du formulaire
1.  Ouvrez votre formulaire en modification.
2.  Allez dans **Paramètres**.
3.  **Activez "Collecter les adresses e-mail"** (Option "Vérifiée" ou "Saisie par le répondant").
    *   ⚠️ **Crucial** : Sans email, GN Manager ne peut pas créer de compte utilisateur.

### B. Installation du Script
1.  Cliquez sur les **3 points verticaux** (en haut à droite) → **Apps Script**.
2.  Un nouvel onglet s'ouvre (Apps Script).
3.  Copiez le contenu du fichier `static/GOOGLE_APPS_SCRIPT.js` fourni par GN Manager (ou ci-dessous).
4.  Remplacez **tout** le code existant dans l'éditeur par ce contenu.

### C. Configuration du Script
Dans le code collé, modifiez les deux premières variables :

```javascript
// URL de votre instance GN Manager
var API_URL = "https://votre-site.com/api/webhook/gform";

// Votre secret API (copié depuis GN Manager)
var API_SECRET = "votre_secret_xxx_yyy_zzz";
```

Sauvegardez avec `Ctrl + S`. Nommez le projet "Webhook GN Manager" si demandé.

### D. Activation du Déclencheur (Trigger)
1.  Dans le menu de gauche de l'éditeur, cliquez sur l'icône **Déclencheurs (Réveil)** ⏰.
2.  Cliquez sur **"Ajouter un déclencheur"** (bouton bleu en bas à droite).
3.  Configurez comme suit :
    *   **Fonction à exécuter** : `sendToWebapp`
    *   **Déploiement** : `Tête (Head)`
    *   **Source de l'événement** : `Dans le formulaire`
    *   **Type d'événement** : `Lors de l'envoi du formulaire`
4.  Cliquez sur **Enregistrer**.
5.  Google va vous demander des **autorisations**.
    *   Choisissez votre compte.
    *   Si l'écran "Application non vérifiée" apparaît : Clique sur **Advanced (Paramètres avancés)** → **Go to Webhook... (unsafe)**.
    *   Cliquez sur **Allow (Autoriser)**.

C'est prêt ! 🎉

## 5. Fonctionnement ⚙️

À chaque fois qu'un utilisateur remplit le formulaire :
1.  GN Manager reçoit les données instantanément.
2.  Si l'email est inconnu : un compte **User** est créé (mot de passe temporaire).
3.  Une inscription **Participant** est créée dans l'événement.
    *   Statut : **À valider**.
    *   Type : **PJ** (par défaut).
    *   Les réponses sont listées dans **Commentaires / Infos**.

### Mise à jour
Si un utilisateur modifie sa réponse (si autorisé dans le Form), GN Manager mettra à jour les infos et ajoutera un nouveau bloc de réponses dans les commentaires.

## 6. Dépannage 🐛

*   **Rien n'apparaît dans GN Manager ?**
    *   Vérifiez les **Exécutions** dans Apps Script (Menu de gauche → Icône Liste).
    *   Si statut "Échec" : Cliquez pour voir l'erreur.
    *   Si statut "Terminé" mais code 401/403 : Vérifiez votre `API_SECRET`.
    *   Si statut "Terminé" mais code 500 : Erreur serveur, contactez l'admin de GN Manager.

*   **"Unauthorized" ?**
    *   Vérifiez que vous avez bien copié le secret de *cet* événement précis.

*   **Pas d'email récupéré ?**
    *   Vérifiez les paramètres du Google Form (Collecte d'email activée).
