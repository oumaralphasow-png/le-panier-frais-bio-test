# Le Panier Frais Bio — V2 design, paiement et sécurité

## Interface
- Hero premium avec la mascotte validée comme visuel principal.
- Barre de réassurance, navigation affinée, cartes et CTA modernisés.
- Responsive mobile/tablette renforcé.
- Panier B2C conservé en cas d'annulation d'un paiement en ligne.
- Paiement en ligne masqué tant que la configuration Stripe n'est pas complète.

## Paiement Stripe
- Nouveau mode `STRIPE` dans le checkout B2C.
- Session Stripe Checkout créée côté serveur uniquement.
- Montant calculé côté serveur à partir des lignes de commande et des profils TVA.
- Paiement en ligne refusé si un profil TVA produit n'est pas configuré.
- Webhook signé `/payments/stripe/webhook` : paiement confirmé, échec/expiration, libération des réservations si nécessaire.
- Aucune donnée de carte n'est stockée par l'application.
- Apple Pay / Google Pay sont gérés par Stripe Checkout lorsqu'ils sont activés et éligibles dans le compte Stripe.

## Variables d'environnement
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_CURRENCY=eur`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`

Ne jamais commiter les vraies valeurs des secrets.

## Sécurité
- Import SQLAlchemy `inspect` restauré pour le contrôle de schéma.
- Limite de taille des requêtes HTTP à 2 Mo.
- En-têtes HSTS, CSP, anti-framing, nosniff, referrer et permissions renforcés.
- Réponses sensibles non mises en cache.
- Protection anti-bruteforce de connexion : blocage après plusieurs échecs récents.
- Les échecs de connexion ne journalisent plus l'adresse e-mail en clair ; un identifiant SHA-256 tronqué est utilisé.
- Vérification de mot de passe factice pour limiter les différences de timing liées à l'existence d'un compte.

## Déploiement
Le Dockerfile exécute `alembic upgrade head` avant Uvicorn.
Après déploiement, configurer le webhook Stripe vers :
`https://lepanierfraisbio.fr/payments/stripe/webhook`

## Validation locale
`qa_static.py` : PASS, 123 routes contrôlées.
`python -m py_compile app.py` : PASS.
