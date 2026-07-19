# SUPMEAL

Application web de gestion de recettes et planification de repas, developpee pour la societe SUPMEAL Pro.

Alternative a Mealie, Tandoor Recipes, Paprika : creer, importer, organiser et planifier des recettes de cuisine, seul ou en cookbook partage.

## Stack

- **Backend** : Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16
- **Frontend** : React 18, Vite, TypeScript, TailwindCSS, shadcn/ui
- **Realtime** : WebSocket natif FastAPI (chat cookbook)
- **Auth** : fastapi-users (local) + OAuth2 (Google, GitHub) via authlib
- **Recherche** : PostgreSQL Full Text Search (tsvector + pg_trgm)
- **Conteneurisation** : Docker + docker-compose

## Demarrage rapide

### Mode production-like

```bash
git clone <url>
cd supmeal
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

- API : http://localhost:8765
- Documentation OpenAPI : http://localhost:8765/docs
- Web : http://localhost

### Mode developpement

```bash
git clone <url>
cd supmeal
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

- API : http://localhost:8765
- Documentation OpenAPI : http://localhost:8765/docs
- Web (Vite) : http://localhost:5173

## Structure

`
.
|-- backend/         # API FastAPI
|-- frontend/        # Client React
|-- docs/            # Documentation technique + manuel utilisateur
|-- docker-compose.yml
`

## Documentation

- Guide technique : docs/technical/
- Manuel utilisateur : docs/user/
- Charte graphique : docs/design/

## Licence

Projet academique - SUPMEAL Pro.

