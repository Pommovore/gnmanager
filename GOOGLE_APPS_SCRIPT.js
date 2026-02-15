/**
 * Google Apps Script pour envoyer les réponses Google Forms vers le Webhook GN Manager.
 * 
 * INSTRUCTIONS:
 * 1. Ouvrez votre Google Form.
 * 2. Cliquez sur les 3 points verticaux (menu) -> Éditeur de scripts.
 * 3. Collez ce code en remplaçant tout le contenu existant.
 * 4. Configurez les variables API_URL et API_SECRET ci-dessous.
 * 5. Sauvegardez (Ctrl+S).
 * 6. Ajoutez un déclencheur (Icône Réveil à gauche) :
 *    - Fonction : sendToWebapp
 *    - Événement : Lors de l'envoi du formulaire
 */

// ==========================================
// CONFIGURATION
// ==========================================

// URL de votre instance GN Manager (ex: https://mon-gn.com/api/webhook/gform)
// var API_URL = "https://VOTRE_DOMAINE/api/webhook/gform";
var API_URL = "https://minimoi.mynetgear.com/api/webhook/gform";


// Votre secret API (trouvable dans le fichier .env sur le serveur : API_SECRET)
var API_SECRET = "REMPLACEZ_PAR_VOTRE_API_SECRET";

// ==========================================
// CODE (NE PAS TOUCHER)
// ==========================================

function sendToWebapp(e) {
    var response = e.response;
    var itemResponses = response.getItemResponses();

    // 1. Construction de l'objet de données
    var payload = {
        // L'ID unique est CRUCIAL pour gérer les modifications
        "responseId": response.getId(),
        "formId": FormApp.getActiveForm().getId(),
        "timestamp": response.getTimestamp().toISOString(),
        "email": response.getRespondentEmail(), // Collecté automatiquement si activé
        "answers": {}
    };

    // 2. Remplissage des réponses
    for (var i = 0; i < itemResponses.length; i++) {
        var itemResponse = itemResponses[i];
        var question = itemResponse.getItem().getTitle();
        var answer = itemResponse.getResponse();
        payload.answers[question] = answer;
    }

    // 3. Configuration de la requête
    var options = {
        'method': 'post',
        'contentType': 'application/json',
        'headers': {
            'Authorization': 'Bearer ' + API_SECRET
        },
        'payload': JSON.stringify(payload),
        'muteHttpExceptions': true
    };

    // 4. Envoi
    try {
        Logger.log("Envoi du payload : " + JSON.stringify(payload));
        var result = UrlFetchApp.fetch(API_URL, options);
        var responseCode = result.getResponseCode();
        var responseBody = result.getContentText();

        Logger.log("Code retour : " + responseCode);
        Logger.log("Réponse serveur : " + responseBody);

        if (responseCode !== 200) {
            // Gestion d'erreur simple
            if (MailApp.getRemainingDailyQuota() > 0) {
                MailApp.sendEmail(Session.getActiveUser().getEmail(), "Erreur Webhook GN Manager",
                    "Erreur lors de l'envoi au webhook : " + responseCode + "\n" + responseBody);
            }
        }
    } catch (error) {
        Logger.log("ERREUR CRITIQUE : " + error.toString());
        if (MailApp.getRemainingDailyQuota() > 0) {
            MailApp.sendEmail(Session.getActiveUser().getEmail(), "Erreur Critique Webhook GN Manager", error.toString());
        }
    }
}
