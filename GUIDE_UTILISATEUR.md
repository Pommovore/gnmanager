# Guide Utilisateur - GNôle

## 1. But de l'application
**GNôle** est une plateforme web conçue pour faciliter l'organisation et la gestion de jeux de rôles grandeur nature (GN). Elle permet de centraliser :

- La gestion des événements (dates, lieux, descriptions).
- L'inscription des participants (PJ, PNJ, Organisateurs).
- Le casting et l'attribution des rôles.
- Le suivi administratif (paiements PAF, validation des inscriptions).
- La communication des documents de jeu (fiches de personnages, PDF).

---

## 2. Mode Opératoire : Participant
Le parcours typique d'un utilisateur souhaitant participer à un événement se déroule comme suit :

1.  **Création de compte** : L'utilisateur s'inscrit sur la plateforme via la page d'inscription.
2.  **Connexion** : Il se connecte avec ses identifiants.
3.  **Lister les événements** : Il consulte la liste des événéments disponibles via "Tous les événements".
4.  **Inscription/Intérêt** : 
    *   Si les inscriptions sont ouvertes, il clique sur **"Rejoindre l'événement"**.
    *   Si l'événement est en préparation, il peut cliquer sur **"J'aimerais participer"** pour signaler son intérêt.
    *   Il remplit un formulaire précisant son type de participation souhaité (PJ, PNJ, Organisateur) et ses préférences de groupe ou de repas.
5.  **Suivi** : Depuis son tableau de bord ("Mes événements"), il suit l'état de sa demande (En attente, Validée, Rejetée) et de son paiement (PAF).
6.  **Jeu** : Une fois le casting réalisé par les organisateurs, il accède à sa fiche de rôle (PDF/GDoc) directement depuis la page de l'événement.

---

## 3. Écrans et Fonctions Accessibles à l'Utilisateur
Tout utilisateur connecté a accès aux menus suivants :

### A. Barre de Navigation (Haut de page)

- **GNôle (Logo)** : Retour à l'accueil / Tableau de bord.
- **Switch Thème** (🌙/☀️) : Permet de basculer entre le mode clair et le mode sombre.
- **Mon Profil** (via le nom/avatar) : Ouvre une fenêtre modale pour :
    - Modifier ses informations personnelles (Nom, Prénom, Age, Genre).
    - Changer son mot de passe.
    - Changer son avatar.

### B. Tableau de Bord (Accueil)
C'est la page principale après connexion. Elle affiche **"Mes Événements"**, regroupant tous les jeux auxquels l'utilisateur est inscrit ou intéressé. Chaque carte d'événement résume :

- Le nom et les dates.
- Le statut de l'inscription (badge couleur).
- Le rôle attribué (si disponible).
- Un bouton "Voir détails" pour accéder à la page de l'événement.

### C. Détail d'un Événement
Cette page est le cœur de l'information pour un jeu donné. Elle est divisée en onglets (certains ne sont visibles que pour les organisateurs) :

#### Onglet "Informations" (Pour tous)

- **En-tête** : Titre, dates, lieu, description générale.
- **Statut** : État d'avancement (Inscriptions ouvertes, Casting en cours, etc.).
- **Liens** : Liens externes (site web, Google Forms).
- **Bloc "Ma Participation"** (si inscrit) :
    - Récapitulatif du rôle (Type, Groupe).
    - **Fiche de personnage** : Lien de téléchargement PDF si le rôle a été distribué.
    - Statut PAF (Participation Aux Frais) et Validation.

#### Onglets Organisateurs (Visible uniquement si Organisateur de l'événement)
Si vous êtes désigné comme **Organisateur** sur cet événement, vous voyez des onglets supplémentaires :

- **Infos Générales (modif)** : Pour éditer la description, les jauges, les liens, les dates et changer le statut de l'événement.
    - **Association Organisatrice** : Permet de définir le nom de l'entité qui organise (défaut: "une entité mystérieuse...").
    - **Affichage des organisateurs** : Case à cocher pour masquer ou afficher la liste des organisateurs aux participants.
    - **Webhook Discord** : URL configurable pour envoyer des notifications automatiques sur un canal Discord.
- **Groupes** : Pour configurer les noms des groupes (factions) disponibles par type.
- **Participants** : Page dédiée de gestion des inscrits :
    - Tableau avec filtres avancés (statut, type, groupe, genre, photo).
    - **Colonne Photo** : Indicateur visuel du statut photo de chaque participant (OK, Profil, KO).
    - **Liste E-mails** : Bouton pour générer la liste des emails des participants filtrés, formatée en `Nom <email>,` avec bouton Copier.
    - **Export CSV** : Export des données filtrées au format CSV/Excel.
    - Gestion individuelle : Validation, PAF, upload de photo personnalisée.
- **GForms Import** : Bouton "Importer" pour charger massivement des données depuis un CSV Google Forms.
- **Rôles** : Création et édition de la liste des rôles (Nom, Type, Genre, Groupe, Liens GDoc/PDF, Commentaire).
- **Casting** : Interface d'attribution des rôles.
    - Tableau matriciel croisant Rôles et Participants.
    - Système de **Scoring** (0 à 10) pour noter l'adéquation d'un joueur à un rôle.
    - **Algorithme d'attribution auto** : Bouton "Casting pondéré" pour proposer une répartition optimale basée sur les scores.
    - **Propositions** : Colonnes additionnelles pour tester différentes versions de casting.
- **Trombinoscope** : Vue d'ensemble visuelle de tous les rôles avec les photos des joueurs assignés.
    - **Indicateurs couleur** : Cadre vert (photo custom), orange (photo profil publique), rouge (pas de photo), gris (rôle non attribué).
    - **Layouts** : Boutons en haut de la section pour changer l'affichage (1, 2 ou 4 par ligne).
    - **Export ODT** : Génère un document imprimable avec options (type de rôle, nom du joueur, groupement).
    - **Export Images (ZIP)** : Télécharge toutes les photos dans une archive ZIP avec motifs de nommage configurables.
- **P.A.F.** : Tableau de suivi des paiements (Participation Aux Frais).
    - Vue par participant avec montants, méthodes de paiement et statut.
    - Tri par colonne.
- **GForms** : Interface dédiée pour visualiser et catégoriser les réponses Google Forms.
    - Catégories avec codes couleur.
    - Mapping de champs et aliases.
- **Notifications** : Journal d'activité de l'événement.
    - Liste chronologique de toutes les actions (inscriptions, modifications, casting, PAF, etc.).
    - Indicateur de notifications non lues (clôche orange dans la barre latérale).
    - Bouton "Tout marquer comme lu".

---

## 4. Écrans et Fonctions Accessibles à l'Administrateur Système
Les utilisateurs ayant le rôle global **"Sysadmin"** ou **"Créateur"** ont accès à un menu spécifique, symbolisé par une icône **"Clé à molette jaune"** dans la barre de navigation.

### A. Dashboard Administrateur
Page de résumé technique affichant :
- Nombre total d'utilisateurs.
- Nombre d'événements.
- Métriques système (version de l'app, espace disque, charge).

### B. Gestion des Utilisateurs
Permet de lister tous les comptes de la plateforme.

- **Recherche** : Filtrer par nom ou email.
- **Actions** :
    - **Promouvoir/Rétrograder** : Changer le rôle global (Utilisateur, Créateur, Sysadmin).
    - **Bannir/Activer** : Bloquer l'accès à un utilisateur.
    - **Supprimer** : Effacer définitivement un compte.

### C. Logs Système
Interface de consultation des journaux d'événements techniques (erreurs, actions critiques, tentatives de connexion). Utile pour le débogage et la surveillance de sécurité.

### D. Gestion des Événements (Super-Admin)
L'administrateur peut voir et modifier **tous** les événements, même ceux dont il n'est pas l'organisateur direct, afin de modérer le contenu ou d'aider à la configuration.
