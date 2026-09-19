# Le Panier Frais Bio — Interface de test V45

Cette version combine :
- backend FastAPI
- base SQLite persistante locale
- interface web de test
- réservation FEFO
- annulation/libération stock
- endpoints santé, produits, lots, commandes et audit

## Lancer localement
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Puis ouvrir http://127.0.0.1:8000

## Déploiement de test
Le dossier inclut :
- `Dockerfile`
- `render.yaml`
- `railway.json`

Vous pouvez le déposer sur un hébergeur compatible Docker/Python.

### Important
Cette V45 est destinée aux tests. Avant une vraie production commerciale :
- remplacer SQLite par une base serveur adaptée
- ajouter authentification réelle et rôles
- restreindre CORS
- mettre les secrets en variables d'environnement
- HTTPS
- sauvegardes
- journalisation et monitoring
- tests de sécurité et de charge
