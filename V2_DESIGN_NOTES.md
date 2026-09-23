# Le Panier Frais Bio — V2 Design Refresh

Cette version conserve les fonctionnalités 1.0.0 et améliore l'interface publique sans casser les routes API existantes.

- Nouveau hero premium avec la mascotte préférée de la marque.
- Barre de réassurance, navigation et boutons modernisés.
- Hiérarchie typographique et espacements retravaillés.
- Cartes boutique, bénéfices, visuels et formulaires plus cohérents.
- Meilleure adaptation tablette/mobile.
- Aucun moyen de paiement n'est présenté comme actif tant que Stripe/Apple Pay/Google Pay ne sont pas configurés côté serveur.
- Correctifs de production déjà découverts réintégrés : import SQLAlchemy `inspect` et migration Alembic au démarrage Render.
