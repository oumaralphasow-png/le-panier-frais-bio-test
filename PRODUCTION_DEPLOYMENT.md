# Déploiement final — Le Panier Frais Bio V102

## Domaine
- Principal : https://lepanierfraisbio.fr
- WWW : https://www.lepanierfraisbio.fr → redirection vers le domaine principal
- Les domaines sont déjà vérifiés dans Render et les certificats HTTPS sont émis.

## Administrateur
- E-mail bootstrap : oumar.alpha.sow@hotmail.fr
- Mot de passe : à définir uniquement comme secret `BOOTSTRAP_ADMIN_PASSWORD` dans Render.
- Aucun mot de passe de production n'est stocké dans ce ZIP.

## Variables de production
- ENVIRONMENT=production
- SEED_DEMO_DATA=false
- PRODUCTION_STRICT=true
- AUTO_CREATE_SCHEMA=false
- SITE_URL=https://lepanierfraisbio.fr
- ALLOWED_ORIGINS=https://lepanierfraisbio.fr,https://www.lepanierfraisbio.fr
- BOOTSTRAP_ADMIN_EMAIL=oumar.alpha.sow@hotmail.fr
- BOOTSTRAP_ADMIN_PASSWORD=<secret Render>
- RELEASE_CHANNEL=production
- DATABASE_URL=<PostgreSQL Render>

## Mise en ligne
1. Sauvegarder la base existante si elle contient des données utiles.
2. Définir le secret `BOOTSTRAP_ADMIN_PASSWORD` dans Render.
3. Déployer la V102 sur le service Render qui porte déjà le domaine.
4. Laisser Render exécuter `python -m alembic upgrade head`.
5. Vérifier `/health/ready`.
6. Se connecter avec oumar.alpha.sow@hotmail.fr.
7. Vérifier dans le Centre de contrôle : schéma migré, intégrité bloquante = 0, environnement production.
8. Tester un parcours complet B2C et PRO avant ouverture commerciale.

## Validation réglementaire
Les paramètres fiscaux, mentions légales, étiquetage, règles d'hygiène/HACCP, DLC et certification bio doivent être validés humainement avant ouverture commerciale.
