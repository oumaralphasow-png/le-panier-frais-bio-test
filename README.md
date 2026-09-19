# Le Panier Frais Bio — V46

Cette version ajoute :
- authentification réelle par mot de passe haché
- JWT de session
- rôles et permissions
- support PostgreSQL via `DATABASE_URL`
- fallback SQLite pour test local
- audit des connexions
- interface de connexion

## Compte de test
Email : `admin@lpfb.test`
Mot de passe : `LPFB-Test-2026!`

À changer avant toute utilisation réelle.

## Render
Ajoutez deux variables d'environnement :
- `DATABASE_URL` : URL PostgreSQL fournie par votre base Render
- `SECRET_KEY` : chaîne longue et aléatoire

Puis redéployez le service.
