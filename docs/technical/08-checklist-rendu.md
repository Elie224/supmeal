# Checklist de rendu SUPMEAL

## 1) Verification de demarrage

- Copier la config: `cp .env.example .env`
- Demarrage production-like:
  - `docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d`
- Demarrage developpement:
  - `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d`
- Verifier les URLs:
  - API: http://localhost:8765/docs
  - Frontend prod-like: http://localhost
  - Frontend dev: http://localhost:5173

## 2) Securite et secrets

- Verifier qu aucun secret reel n est commite.
- Confirmer les en-tetes de securite actifs.
- Confirmer CORS sans wildcard avec cookies.
- Verifier hashing mot de passe et absence de `hashed_password` dans les reponses API.

## 3) Parcours fonctionnels a demontrer

- Inscription et connexion locale.
- OAuth Google/GitHub (si credentials configures).
- CRUD recette complet.
- Cookbooks et roles (createur/editeur/commentateur/lecteur).
- Chat temps reel cookbook.
- Planning hebdomadaire et liste de courses.
- Import/Export JSON et CSV.
- Isolation inter-utilisateurs.

## 4) Qualite et CI

- Backend lint: `ruff check app tests`
- Backend tests: `pytest -q`
- Frontend lint: `npm run lint`
- Frontend build: `npm run build`
- Workflow GitHub Actions vert sur PR et main.

## 5) Documentation et soutenance

- Verifier coherence README + docs techniques.
- Ajouter captures ecran sur les parcours critiques.
- Ajouter matrice finale des permissions.
- Prepararer un scenario de demo de 8 a 12 minutes.

## 6) Commandes utiles

- Build local frontend: `cd frontend && npm run build`
- Tests backend local: `cd backend && python -m pytest -q`
- Stop stack: `docker compose down`
- Stop + volumes: `docker compose down -v`
