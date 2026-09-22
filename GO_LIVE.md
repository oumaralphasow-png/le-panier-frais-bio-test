# GO LIVE — Le Panier Frais Bio 1.0.0

## 1. Dans Render
Utilise le service qui possède déjà :
- `lepanierfraisbio.fr`
- `www.lepanierfraisbio.fr`

## 2. Variables obligatoires
- `ENVIRONMENT=production`
- `SEED_DEMO_DATA=false`
- `PRODUCTION_STRICT=true`
- `AUTO_CREATE_SCHEMA=false`
- `SITE_URL=https://lepanierfraisbio.fr`
- `ALLOWED_ORIGINS=https://lepanierfraisbio.fr,https://www.lepanierfraisbio.fr`
- `BOOTSTRAP_ADMIN_EMAIL=oumar.alpha.sow@hotmail.fr`
- `BOOTSTRAP_ADMIN_PASSWORD=<secret à définir dans Render>`
- `RELEASE_CHANNEL=stable`
- `DATABASE_URL=<PostgreSQL Render>`

## 3. Déploiement
Le blueprint production lance :
`python -m alembic upgrade head`

Puis Render démarre l'application et contrôle :
`/health/ready`

## 4. Test après déploiement
Depuis un terminal :
`python post_deploy_smoke.py https://lepanierfraisbio.fr`

Le résultat attendu est :
`"status": "PASS"`

## 5. Vérification manuelle
Tester au minimum :
- page d'accueil,
- connexion admin,
- création d'une commande test,
- stock et réservation,
- approvisionnement fournisseur,
- réception,
- production RAW → PREPARED,
- livraison/retrait,
- facturation,
- PWA sur téléphone.

## 6. Avant ouverture commerciale
Valider humainement :
- prix,
- fournisseurs,
- fiscalité/TVA,
- facturation,
- mentions légales,
- politique de confidentialité,
- étiquetage,
- hygiène/HACCP,
- DLC,
- certification et communication bio.
