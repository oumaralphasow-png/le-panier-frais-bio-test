# Le Panier Frais Bio — Release 1.0.0

## État
Release logicielle finale gelée pour mise en production.

## Domaine
- https://lepanierfraisbio.fr
- https://www.lepanierfraisbio.fr → redirection vers le domaine principal
- DNS vérifiés
- certificats HTTPS émis

## Inclus
- B2C : catalogue, panier, compte, favoris, abonnements, Click & Collect / livraison
- PRO : commandes multi-produits, découpes, conditionnements, commandes types, profil restaurant
- Admin : produits, clients, commandes, stock, lots, production, livraisons, facturation, fournisseurs, achats, audit, utilisateurs
- catalogue universel extensible fruits & légumes
- approvisionnement sur rupture et demandes de sourcing
- fournisseurs, bons d'achat, réceptions et réconciliation des besoins
- séparation explicite des lots RAW / PREPARED
- réservations, production, livraison/retrait et consommation cohérentes
- traçabilité amont/aval
- PWA installable
- rôles et sécurité
- mode maintenance
- contrôle d'intégrité
- Alembic pour les migrations de base de données
- health check et readiness check
- préflight de production
- checksums SHA-256 du pack

## Secrets volontairement absents
Le mot de passe administrateur de production n'est pas inclus dans les fichiers.
Il doit être défini comme secret Render `BOOTSTRAP_ADMIN_PASSWORD`.

## Conditions avant ouverture commerciale
L'ouverture commerciale exige encore une validation humaine des paramètres réellement applicables :
- prix et fournisseurs réels,
- fiscalité / TVA,
- facturation,
- mentions légales et confidentialité,
- étiquetage,
- règles d'hygiène / HACCP,
- DLC saisies par l'opérateur,
- certification et communication bio.

Ces éléments ne doivent jamais être déduits automatiquement par le logiciel.
