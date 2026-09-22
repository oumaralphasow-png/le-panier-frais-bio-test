# Le Panier Frais Bio — V64 Functional QA consolidée

Cette version poursuit la construction de l'écosystème complet sans micro-déploiement intermédiaire.

## Nouveautés majeures V53
- Accueil B2C enrichi : recherche, filtres par famille, formats, portions et usages.
- Planificateur recette : nombre de personnes -> quantités nettes et besoins bruts estimés.
- Catalogue public enrichi : découpes, rendement, portion de référence, formats B2C/PRO.
- Espace PRO restauration repensé comme un outil de commande cuisine.
- Commande rapide multi-produits avec découpe, conditionnement 1 / 2,5 / 5 / 10 kg et kg nets.
- Panier PRO avec estimation de valeur, kg nets et simulation de temps de préparation interne évité.
- Compte restaurant de démonstration dédié.
- Commandes types / récurrentes : mémorisation et rechargement d'une mise en place habituelle.
- Création d'une commande PRO multi-lignes générant automatiquement les besoins de production, la livraison et la facture brouillon.
- Dashboard interne enrichi avec alertes, valeur des commandes, panier moyen, commandes ouvertes et clients PRO.
- Alertes : lots bloqués, DLC proches et commandes à préparer.
- Référentiel existant maintenu : produits, découpes, portions, recettes, stock, lots, FEFO, production, livraison, facturation, fournisseurs, équipements et audit.

## Comptes de démonstration
### Administration
- [identifiant de démonstration retiré]
- [identifiant de démonstration retiré]

### Restaurant PRO
- [identifiant de démonstration retiré]
- [identifiant de démonstration retiré]

## Important
Ne pas déployer cette version sur Render pour le moment. Elle reste une Release Candidate de construction et sera consolidée avec les interfaces restantes avant le prochain déploiement unique.

## Vérifications effectuées
- Compilation Python de `app.py` réussie.
- Vérification syntaxique JavaScript avec Node réussie.
- Le test serveur local complet n'a pas été exécuté dans l'environnement de fabrication, car les dépendances FastAPI/Jose du pack ne sont pas installées dans le runtime de validation. Elles restent déclarées dans `requirements.txt` pour Render.

## Avant ouverture commerciale
Les éléments suivants restent à valider/finaliser : paiement réel, facturation finale conforme, sécurité, sauvegardes automatisées, règles HACCP/DLC validées par l'exploitant, tests E2E complets et paramétrage de production réel.


## V53 — Réalité restaurant & pilotage journée
- Mode Chef : calcul par couverts, grammage, découpe et conditionnement.
- Estimation du besoin brut à partir du rendement de préparation.
- Simulation de temps de préparation et valeur de main-d’œuvre, avec paramètres modifiables par le restaurant.
- Profil restaurant : couverts midi/soir, jours de livraison, conditionnement préféré, coût horaire et temps de préparation/kg.
- Tableau « Aujourd’hui » côté administration : séquence de journée et besoins de production regroupés par produit.
- Aucun micro-déploiement requis : ce pack reste une Release Candidate consolidée.


## V54 — Parcours client & achats intelligents
- Panier intelligent B2C par usage : repas pour 2, famille 4, batch cooking.
- Dosages par personne et arrondi vers les formats 250 g / 500 g / 750 g / 1 kg.
- Parcours Click & Collect plus lisible côté particulier.
- Enregistrement local d'un panier type avant connexion client définitive.
- Nouveau module Admin « Achats & prévisions ».
- Suggestion d'achat maraîcher à partir du stock disponible, du rendement et d'une marge de sécurité.
- Statuts visuels « OK / À surveiller / À sécuriser ».
- Validation humaine obligatoire : aucune commande fournisseur automatique.
- Cette version reste une Release Candidate consolidée et ne doit pas être déployée séparément.


## V55 — Espace particulier complet & continuité omnicanale
- Nouveau compte particulier avec connexion dédiée.
- Profil foyer : nombre de personnes, budget hebdomadaire, objectifs alimentaires généraux, aliments non appréciés et allergies/intolérances déclarées.
- Préférence Click & Collect / livraison et créneau favori.
- Fidélité : compteur de points prêt à être relié aux règles commerciales définitives.
- Favoris produits pour préparer la fonction « mes habituels ».
- Abonnements particuliers : fréquence, budget et jour de retrait, avec pause/réactivation.
- Historique des dernières commandes du particulier.
- Compte démonstration particulier : `[identifiant de démonstration retiré]` / `[identifiant de démonstration retiré]`.
- Le pack V55 réintègre le backend complet de la V53, le frontend V54 et les nouveaux modules V55 dans un seul ZIP, afin d'éviter les paquets front-only.
- Cette version reste une Release Candidate hors ligne : ne pas la déployer séparément sur Render avant validation globale.


## V56 — Parcours d'achat particulier de bout en bout
- Panier B2C persistant dans le navigateur.
- Ajout d'un produit avec format et découpe depuis le catalogue.
- Modification des quantités, suppression d'une ligne et vidage du panier.
- Choix Click & Collect / livraison, créneau et note de commande.
- Paiement au retrait / à la remise intégré au flux ; paiement en ligne volontairement laissé désactivé tant qu'un prestataire réel n'est pas connecté.
- Confirmation de commande depuis le compte particulier.
- Création automatique : commande, lignes, réservation FEFO, besoin de production si stock insuffisant, livraison, facture brouillon et statut de paiement.
- Historique des commandes particulier enrichi avec annulation sécurisée.
- Annulation = libération des réservations, arrêt des productions non terminées, annulation de la livraison et du paiement non encaissé.
- Nouveau modèle `Payment` pour préparer le futur branchement à un prestataire de paiement.
- Version API portée à 56.0-rc.
- Toujours aucune mise en ligne intermédiaire : cette version reste une Release Candidate consolidée.


## V57 — Atelier, lot fini et traçabilité amont/aval
- Nouveau mode atelier dans le module Production.
- Proposition FEFO des lots sources à partir de la quantité réellement consommée.
- Finalisation d'une production avec quantité d'entrée réelle, quantité nette obtenue, découpe et conditionnement.
- Création d'un lot fini distinct avec son propre numéro interne.
- Conservation de la filiation entre lots sources et lot fini via `ProductionConsumption`.
- Saisie opérateur de la température constatée : aucune valeur ou seuil n'est imposé par le logiciel.
- Date de conservation/DLC saisie et validée par l'opérateur : aucune durée n'est générée automatiquement.
- Validation qualité explicite : lot libéré si `VALIDEE`, lot bloqué si `BLOQUEE`.
- Recherche de traçabilité par numéro de lot : origine fournisseur/lots sources, transformation et commandes liées.
- Aperçu d'étiquette atelier imprimable avec produit, lot, découpe, emballage, quantité et date validée.
- Le lot source est décrémenté selon la consommation réelle au moment de la finalisation.
- Le lot fini redevient disponible pour les réservations FEFO uniquement s'il a été libéré.
- Version API : 57.0-rc.
- Release Candidate hors ligne : ne pas déployer séparément avant validation globale.


## V58 — Achats fournisseurs & réception en lots
- Référentiel fournisseur/produit avec prix d'achat, minimum de commande, délai et référence fournisseur.
- Bons d'achat multi-lignes avec date prévue, note, prix HT et statut.
- Envoi/annulation manuels d'un bon d'achat.
- Réception partielle ou complète d'un bon d'achat.
- Chaque ligne réceptionnée crée un lot interne avec lot fournisseur, quantité réellement reçue, date saisie et statut qualité.
- Par défaut, la réception peut rester BLOQUÉE jusqu'à validation de l'opérateur.
- Les quantités reçues sont suivies ligne par ligne et le bon passe à `PARTIELLEMENT_RECUE` ou `RECUE`.
- Le module Achats prévisionnels reste indicatif : aucune commande fournisseur automatique n'est envoyée.
- Version API : 58.0-rc.


## V59 — Coûts, marges et historique de prix
- Nouveau coût complet par produit : achat, emballage, main-d’œuvre et autres coûts.
- Marge actuelle calculée à partir du prix HT et du coût complet renseigné.
- Marge cible configurable par produit.
- Suggestion de prix calculée à partir de la marge cible, sans modification automatique du tarif.
- Toute modification du prix de vente exige une action humaine, un motif et crée une ligne d'historique.
- Historique de prix avec date, utilisateur et motif.
- Tableau de rentabilité par produit.
- Indicateurs globaux : CA HT enregistré, coûts estimés, marge estimée et taux de marge estimé.
- Les résultats restent explicitement estimatifs tant que les coûts réels ne sont pas tous renseignés.
- Aucun taux de TVA n'est codé en dur dans ce module.
- Version API : 59.0-rc.


## V60 — Fiscalité produit, factures figées, paiements & avoirs
- Nouveau profil fiscal par produit avec taux et libellé configurables.
- Aucun taux n'est imposé par défaut : les produits restent à 0 % / « À configurer » tant qu'un opérateur autorisé ne les renseigne pas.
- Aperçu fiscal d'une facture avant validation : HT, montant de taxe et TTC par ligne.
- Validation d'une facture = création d'un instantané des taux appliqués afin que l'historique ne change pas si le produit est reparamétré ensuite.
- Numérotation interne de facture générée au moment de la validation (`LPFB-AAAA-xxxxxx`).
- Détail facture : lignes, quantités, prix HT, taux configuré, taxe et TTC.
- Suivi des encaissements et action manuelle « marquer payé » avec mode et référence.
- Création d'avoirs en brouillon reliés à la facture ; leur fiscalité reste à valider avant usage comptable réel.
- Aucune prétention de conformité fiscale finale : règles de TVA, mentions obligatoires, numérotation légale, échéances et avoirs devront être validés avant ouverture commerciale.
- Version API : 60.0-rc.


## V61 — Équipe, rôles & durcissement des accès
- Nouveau module « Équipe & accès » réservé aux administrateurs.
- Création de comptes internes : ADMIN, MANAGER, VENTE, PRODUCTION, LIVRAISON, COMPTA.
- Activation / désactivation d’un compte interne.
- Réinitialisation manuelle du mot de passe d’un membre de l’équipe.
- Blocage de la désactivation de son propre compte administrateur depuis l’interface.
- Journalisation des échecs de connexion en plus des connexions réussies.
- Tableau d’état de sécurité : type de base, présence de comptes de démonstration, SECRET_KEY par défaut, effectif actif et échecs de connexion journalisés.
- Les principales routes internes de lecture sont maintenant limitées aux rôles équipe ; les comptes B2C et PRO utilisent leurs routes dédiées.
- Le module signale explicitement SQLite, la clé secrète de démonstration et les comptes de démonstration avant mise en production.
- Version API : 61.0-rc.
- Avant ouverture commerciale : remplacer SECRET_KEY, utiliser PostgreSQL persistant, retirer/changer les comptes de démonstration et effectuer des tests d’autorisation complets.


## V62 — Pré-production & readiness
- Nouveau module « Pré-production » réservé à l'administrateur.
- Checklist automatique avec statuts PASS / WARN / BLOCK.
- Contrôles : PostgreSQL, SECRET_KEY, CORS, comptes de démonstration, administrateur actif, profils fiscaux, profils de coût, lots bloqués, productions ouvertes et factures non validées.
- Export JSON du rapport de pré-production.
- Sauvegarde JSON élargie : produits, découpes, clients, lots, commandes, lignes de commande, productions, fournisseurs, achats, factures, paiements, équipements et paramètres.
- CORS désormais configurable par variable `ALLOWED_ORIGINS`.
- Nouveau `render.production.yaml` séparé du blueprint de test, avec PostgreSQL, `SECRET_KEY` générée et emplacement à remplacer par le vrai domaine.
- Version API : 62.0-rc.

### Important avant déploiement final
1. Remplacer `https://YOUR-PRODUCTION-DOMAIN.example` dans `render.production.yaml`.
2. Désactiver/supprimer les comptes de démonstration.
3. Valider les profils fiscaux et les coûts réels.
4. Faire un export de sauvegarde.
5. Exécuter un test complet du parcours commande → stock → production → livraison/retrait → facture → paiement.
6. Ne considérer l'application prête commercialement qu'après validation des règles fiscales, d'étiquetage, HACCP/DLC et bio applicables.


## V63 — Final QA, séparation démo/production
- Correction importante : les comptes de démonstration ne sont plus obligatoirement recréés au démarrage.
- Nouvelle variable `SEED_DEMO_DATA`; le blueprint de production la fixe à `false`.
- Bootstrap d’un vrai administrateur via `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD` et `BOOTSTRAP_ADMIN_NAME`.
- Le contrôle de pré-production bloque désormais un environnement `production` si la réinjection démo est encore active.
- Stockage local du navigateur normalisé sur les clés `lpfb63` / `lpfb63role` pour éviter les anciennes clés de Release Candidate.
- Sauvegarde versionnée `LPFB_BACKUP_V63`.
- `render.production.yaml` mis à jour avec `ENVIRONMENT=production`, démo désactivée et bootstrap admin.
- Ajout de `qa_static.py` : contrôle de version, routes dupliquées, clés locales obsolètes et routes internes non protégées.
- Cette version constitue une passe de QA finale, pas encore le déploiement commercial.

### À renseigner avant le déploiement unique
- vrai domaine dans `ALLOWED_ORIGINS`,
- vrai e-mail administrateur,
- mot de passe bootstrap admin dans Render,
- validation des taux fiscaux, coûts, données fournisseurs et règles sanitaires.


## V64 — Functional QA transactionnel
- Nouveau test fonctionnel à blanc depuis la page Pré-production.
- Le test exécute dans une transaction : lecture catalogue, création client temporaire, commande, livraison, facture, paiement, calcul fiscal, lot source, production, lot fini, filiation de traçabilité, bon fournisseur et réception.
- Toutes les écritures du test sont annulées par `rollback` : aucune donnée de test ne reste dans la base.
- Le test retourne un résultat PASS/FAIL détaillé étape par étape.
- Le rapport de pré-production reste séparé de ce test fonctionnel.
- Sauvegarde versionnée `LPFB_BACKUP_V64`.
- Version API : `64.0-rc`.
- Cette version rapproche le projet du déploiement final mais ne remplace pas les validations métier, fiscales, sanitaires ni les essais réels sur l’environnement Render final.


## V65 — Candidate au déploiement final
- Garde-fous de démarrage en environnement `production`.
- Le démarrage est bloqué si PostgreSQL n'est pas configuré, si la clé secrète est faible/par défaut, si les données démo sont actives, si CORS est ouvert à `*`, ou si les identifiants bootstrap admin sont encore des exemples.
- Nouvel endpoint public minimal `/health/ready` pour le health check Render.
- `render.production.yaml` utilise désormais `/health/ready`.
- `Dockerfile` contient également un `HEALTHCHECK`.
- Ajout de `deployment_preflight.py` pour détecter les placeholders et erreurs de configuration avant le déploiement.
- Ajout de `release_manifest.json` pour figer le contenu attendu de la release.
- Sauvegarde versionnée `LPFB_BACKUP_V65`.

### Séquence finale de déploiement
1. Remplacer le domaine exemple dans `render.production.yaml`.
2. Remplacer l'e-mail administrateur exemple.
3. Saisir le mot de passe bootstrap administrateur dans Render.
4. Créer/utiliser PostgreSQL persistant.
5. Laisser `SEED_DEMO_DATA=false` et `PRODUCTION_STRICT=true`.
6. Lancer `python deployment_preflight.py`.
7. Déployer une seule fois.
8. Ouvrir l'admin, exécuter Pré-production puis le test fonctionnel à blanc.
9. Valider ensuite les données métier réelles avant ouverture publique.

Cette release reste une candidate technique : les validations fiscales, sanitaires, d'étiquetage et bio doivent être confirmées avant exploitation commerciale.

## V66 — Visuels commerciaux intégrés
- Intégration dans l’interface des créas **Le Panier Frais Bio** déjà validées et disponibles dans le projet.
- Mise en avant B2C des **Poke Bowls Signature** et des **jus / shots**.
- Mise en avant directe de la formule **salade + jus à 7 €**.
- Ajout d’un visuel PRO dédié à la préparation fruits & légumes pour restaurants.
- Images optimisées en WebP et servies localement via `/assets` : aucune dépendance à un hébergement externe.
- Responsive mobile/tablette.
- Les visuels portant l’ancienne marque « Mon Panier Frais Bio » ne sont volontairement pas intégrés.

## V67 — Catalogue visuel & fiches produits
- Les visuels ne restent plus seulement en bannière : ils sont désormais reliés aux cartes produits concernées.
- Nouvelle fiche produit visuelle en plein écran avec image, famille, prix, usages, portions, formats et découpes.
- Ajout au panier directement depuis la fiche produit.
- Ajout aux favoris depuis la fiche pour un client connecté.
- Nouvelle zone d’inspiration avec la gamme bien-être, les formats jus et les formats PRO.
- Les produits sans photo dédiée utilisent un fallback visuel propre plutôt qu’une image trompeuse.

## V68 — Gestion des visuels depuis le back-office
- Nouveau module **Visuels & merchandising** dans l'admin.
- Association d'une image à un produit sans modifier le code.
- Gestion du texte alternatif, badge et activation.
- Bibliothèque de visuels merchandising avec placement, titre, sous-titre, filtre cible et ordre.
- Endpoints publics séparés pour charger les visuels actifs.
- Les cartes et fiches produits utilisent en priorité l'image configurée dans le back-office.
- Les créas embarquées dans `/assets` restent disponibles comme bibliothèque stable du pack.
- Aucune image de l'ancienne marque n'est seedée par défaut.

## V69 — Catalogue universel & approvisionnement fournisseur
- Le catalogue n'est plus limité au stock physique du jour.
- Ajout d'un **catalogue maître extensible** de fruits, légumes, champignons, aromatiques et fruits à coque.
- Les nouvelles références sans prix réel renseigné apparaissent avec **« Prix à confirmer »** plutôt qu'un tarif inventé.
- Statuts de disponibilité : `EN_STOCK`, `SUR_COMMANDE`, `SAISONNIER`, `INDISPONIBLE`.
- Un produit peut rester visible et commandable/demandable même avec stock à zéro.
- Une demande client ou une commande avec stock insuffisant crée automatiquement un **besoin d'approvisionnement**.
- Le back-office permet de régler le mode de disponibilité, le délai fournisseur indicatif et l'autorisation de commande.
- Les commandes B2C/PRO génèrent un besoin fournisseur lorsqu'une quantité n'est pas couverte par le stock.
- Cette architecture est volontairement extensible : toute nouvelle variété peut être ajoutée comme produit sans refonte du logiciel.

## V70 — Approvisionnement piloté & conversion en bons fournisseurs
- Tableau de bord des besoins d'approvisionnement ouverts.
- Vue des produits les plus demandés à ravitailler.
- Recherche des fournisseurs déjà associés à chaque produit.
- Affichage du dernier prix d'achat, minimum de commande, délai et référence fournisseur.
- Conversion d'un besoin client directement en **bon d'achat fournisseur**.
- Regroupement possible de plusieurs besoins par fournisseur côté API.
- Suivi de statut : `A_APPROVISIONNER`, `EN_COURS`, `COMMANDE_FOURNISSEUR`, `COUVERT`, `ANNULE`.
- Aucune commande fournisseur n'est envoyée automatiquement : la création du bon reste une validation humaine.

## V71 — Couverture fournisseurs du catalogue
- Tableau de couverture fournisseurs sur l'ensemble du catalogue actif.
- KPI : nombre total de références, références avec fournisseur, références sans fournisseur et taux de couverture.
- Vue par famille de produits.
- Détection des besoins d'approvisionnement urgents qui n'ont encore aucun fournisseur associé.
- Association en lot de plusieurs produits à un fournisseur depuis le back-office.
- Lorsqu'un besoin n'a pas de fournisseur déjà lié, l'application propose aussi les fournisseurs actifs comme options **« À confirmer »**.
- Si l'opérateur choisit volontairement un fournisseur non encore lié et crée le bon d'achat, cette validation humaine crée l'association fournisseur/produit.
- Aucun fournisseur n'est automatiquement déclaré comme source certaine d'un produit : les associations restent contrôlées par l'opérateur.

## V72 — Réconciliation réception fournisseur → besoin client
- Nouveau lien explicite entre chaque **besoin d'approvisionnement** et la ligne de bon d'achat fournisseur qui le couvre.
- Lors d'une réception fournisseur, la quantité réceptionnée est automatiquement imputée aux besoins concernés.
- Gestion des réceptions partielles : un besoin passe en `EN_COURS` tant qu'il n'est pas entièrement couvert.
- Passage automatique à `COUVERT` lorsque la quantité affectée a été totalement réceptionnée.
- Le tableau de bord affiche désormais les volumes en commande fournisseur et les volumes déjà réceptionnés.
- Barre de progression par besoin.
- Vue de traçabilité : besoin client → bon fournisseur → fournisseur → quantité affectée → quantité réceptionnée.
- Cette évolution évite de considérer un besoin comme traité uniquement parce qu'un bon fournisseur a été créé.

## V73 — Application installable & domaine prêt
- Ajout d'une **Progressive Web App (PWA)** installable sur téléphone/tablette/ordinateur.
- `manifest.webmanifest`, icônes 192/512 et Service Worker inclus.
- Bouton « Installer l’app » lorsque le navigateur le permet.
- Sur iPhone/iPad : installation via Partager → Sur l’écran d’accueil.
- Cache de l'interface et de quelques visuels de marque pour un démarrage plus rapide ; les opérations métier sensibles restent réseau-first.
- Nouvelle variable `SITE_URL` pour le futur domaine public.
- Le contrôle production bloque si `SITE_URL` contient encore le domaine exemple.
- Le canonical du site est alimenté depuis la configuration publique `/app-config`.
- Cette V73 prépare le site pour `lepanierfraisbio.fr`, `lepanierfraisbio.com` ou tout autre domaine réellement acheté/configuré, sans présumer de leur disponibilité.

## V74 — Nettoyage production & sécurité front
- Suppression de tous les identifiants/mots de passe de démonstration du HTML et du JavaScript public.
- Les champs de connexion sont vides par défaut avec attributs d'autocomplétion adaptés.
- L'espace PRO ne publie plus de compte de démonstration dans l'interface.
- `/app-config` n'expose que des informations publiques sûres et indique si l'environnement non-production autorise les données démo.
- Ajout d'en-têtes HTTP de sécurité : `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy` et HSTS en production.
- Le préflight de déploiement échoue si un identifiant de démonstration réapparaît dans `index.html`.
- Badge d'environnement visible uniquement hors production.


# Consolidation V75 → V97

Cette branche a été consolidée directement jusqu'à la **V97 Release Candidate**. Les numéros intermédiaires correspondent à des jalons de finition intégrés dans le même pack final :

- **V75** : nettoyage final des écrans de connexion et des comptes démo.
- **V76** : configuration publique sûre via `/app-config`.
- **V77** : état de maintenance configurable.
- **V78** : contrôle d'intégrité des lots et compteurs de stock.
- **V79** : contrôle de cohérence des liens approvisionnement → achats.
- **V80** : alertes sur produits sans prix réel.
- **V81** : alertes sur produits sans fournisseur associé.
- **V82** : demande publique d'un produit non encore référencé.
- **V83** : formulaire « sourcer ce produit » sans inventer de prix ni de disponibilité.
- **V84** : changement de mot de passe en libre-service pour utilisateur connecté.
- **V85** : résumé d'audit opérationnel.
- **V86** : matrice lisible des rôles opérationnels.
- **V87** : centre de contrôle de release.
- **V88** : indicateurs de support client configurables.
- **V89** : variables `SUPPORT_EMAIL` et `SUPPORT_PHONE`.
- **V90** : durée de jeton configurable par `TOKEN_TTL_MINUTES`.
- **V91** : bannière publique de maintenance.
- **V92** : sauvegarde enrichie avec demandes de sourcing libre.
- **V93** : snapshot d'intégrité inclus dans l'export de sauvegarde.
- **V94** : séparation du canal de release via `RELEASE_CHANNEL`.
- **V95** : consolidation des contrôles pré-production.
- **V96** : renforcement du préflight final.
- **V97** : **Release Candidate consolidée** : catalogue universel, visuels, B2C, PRO, admin, stock, production, traçabilité, fournisseurs, achats, approvisionnement, facturation, PWA, sécurité et contrôle de release.

## V97 — points restant obligatoirement à renseigner avant production
- vrai domaine public dans `SITE_URL` et `ALLOWED_ORIGINS`,
- vrai e-mail administrateur bootstrap,
- mot de passe administrateur bootstrap via secret Render,
- PostgreSQL persistant,
- support e-mail/téléphone si souhaité,
- taux fiscaux et prix réels,
- données fournisseurs confirmées,
- validation juridique/fiscale/sanitaire/étiquetage/bio,
- test fonctionnel réel sur l'environnement Render final.

Le pack V97 ne prétend pas que les contrôles réglementaires externes sont déjà validés.


# V98 — Intégrité RAW / PREPARED et transfert des réservations

Cette version corrige le principal risque de cohérence restant dans le flux stock → production :

- ajout d'un registre `LotStageInfo` compatible avec les bases existantes, sans ajouter de colonne risquée à la table `lots` ;
- chaque lot est explicitement `RAW` ou `PREPARED` ;
- les réceptions fournisseur et les réceptions manuelles créent des lots `RAW` ;
- les sorties de production créent des lots `PREPARED` ;
- migration de compatibilité : les anciens lots de sortie production sont reconnus `PREPARED`, les autres `RAW` ;
- l'atelier ne propose et ne consomme que des lots `RAW` ;
- les réservations RAW déjà liées à une commande sont transférées transactionnellement vers la consommation de production au lieu d'être double-comptées ;
- le lot fini PREPARED est réservé à la commande source lorsqu'il est libéré ;
- si la production obtenue ne couvre pas le besoin, un nouveau besoin de production est créé pour le reliquat ;
- les contrôles bloquent toute création qui rendrait le stock négatif ;
- l'endpoint `/stock/stages` sépare les métriques RAW / PREPARED ;
- la traçabilité et les étiquettes exposent le stage du lot ;
- l'interface stock affiche désormais les stages et les disponibilités sans masquer les valeurs négatives.

Un test runtime complet sur PostgreSQL reste requis avant ouverture commerciale.


# V99 — Cycle de vie complet des réservations

- Une commande livrée ou retirée transforme désormais ses réservations actives en consommation réelle de stock.
- `qty_reserved` diminue et `qty_consumed` augmente exactement de la quantité livrée/retirée.
- La commande passe à `TERMINEE` seulement au stade final de livraison ou de retrait.
- Une annulation libère proprement les réservations actives sans masquer une incohérence de compteur.
- Les productions non terminées liées à une commande annulée passent à `ANNULE`.
- Les besoins d'approvisionnement encore ouverts sont annulés ; un approvisionnement déjà commandé fournisseur reste signalé pour traitement manuel.
- Impossible d'annuler automatiquement une commande déjà livrée ou retirée.
- Nouveau contrôle d'intégrité des réservations sur commandes fermées.
- Nouveau détail « Affectations stock » : réservations, lots RAW/PREPARED, productions et approvisionnements liés à chaque commande.

Cette version ferme le cycle réservation → préparation → livraison/retrait → consommation et évite que les quantités restent réservées indéfiniment après exécution.


# V100 — Schéma versionné avec Alembic

La V100 remplace le comportement implicite `create_all()` en production par un vrai mécanisme de versionnement de schéma :

- ajout d'Alembic aux dépendances ;
- `alembic.ini`, `alembic/env.py` et répertoire `alembic/versions` inclus ;
- migration de baseline `v100_baseline` ;
- le déploiement Render exécute `python -m alembic upgrade head` avant le démarrage du service ;
- `AUTO_CREATE_SCHEMA=false` est obligatoire en production ;
- `create_all()` reste possible uniquement en développement/test pour simplifier le travail local ;
- le démarrage production échoue si des tables attendues manquent ou si `alembic_version` n'existe pas ;
- `/health/ready` inclut l'état du schéma ;
- `/ops/schema-status` permet aux administrateurs de vérifier la version Alembic et les tables manquantes ;
- le Centre V100 affiche si la base est migrée.

La baseline est conçue pour être compatible avec la base candidate existante : elle crée les tables manquantes sans supprimer ni recréer les tables métier déjà présentes. Les futures modifications de structure devront être réalisées par migrations Alembic explicites.


# V101 — Domaine réel & préflight de production

Le domaine vérifié est maintenant intégré dans le blueprint de production :

- `SITE_URL=https://lepanierfraisbio.fr`
- `ALLOWED_ORIGINS=https://lepanierfraisbio.fr,https://www.lepanierfraisbio.fr`
- le `.fr` est le domaine canonique ;
- `www.lepanierfraisbio.fr` peut rester redirigé vers le domaine racine côté Render ;
- les anciens placeholders de domaine ont été retirés du blueprint production ;
- le préflight a été réorganisé pour que **tous les contrôles soient exécutés avant le résultat final** ;
- le préflight contrôle aussi que le vrai domaine canonique est présent ;
- les identifiants de démonstration ont été retirés de la documentation utilisateur du pack.

## Point restant avant déploiement
Le blueprint conserve volontairement `admin@YOUR-DOMAIN.example` tant qu'une adresse administrateur de production n'a pas été explicitement choisie.

Le domaine est actuellement relié au service Render de test existant. Lors du déploiement final, il faudra soit :
1. déployer la V101 sur ce service existant puis le renommer si souhaité ; ou
2. créer le service production final et déplacer ensuite les domaines personnalisés vers ce service.

Ne pas attacher le même domaine à deux services simultanément.


# V102 FINAL — Production Ready

- Domaine canonique : `https://lepanierfraisbio.fr`
- `www` autorisé et redirigé vers le domaine principal
- E-mail administrateur bootstrap : `oumar.alpha.sow@hotmail.fr`
- Canal de release : `production`
- Alembic obligatoire en production
- Séparation RAW / PREPARED
- Cycle complet réservation → production → livraison/retrait → consommation
- Approvisionnement fournisseur et réception réconciliés
- PWA installable
- Centre de contrôle, intégrité, audit, rôles et maintenance
- Catalogue universel extensible
- B2C + PRO + Admin consolidés

Le seul secret non inclus est `BOOTSTRAP_ADMIN_PASSWORD`, à définir directement dans Render.


# RELEASE FINALE 1.0.0

À partir de cette release, la numérotation Vxx est arrêtée. Les futures modifications devront être des correctifs ou évolutions semver (`1.0.1`, `1.1.0`, etc.) après mise en production.

Le pack ne contient aucun mot de passe de production et aucun identifiant/mot de passe de démonstration codé en dur dans le frontend ou le backend.
