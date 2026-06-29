# SUPMEAL

Application web de gestion de recettes et planification de repas, developpee pour la societe SUPMEAL Pro.

Alternative a Mealie, Tandoor Recipes, Paprika : creer, importer, organiser et planifier des recettes de cuisine, seul ou en cookbook partage.

## Stack

- **Backend** : Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16
- **Frontend** : React 18, Vite, TypeScript, TailwindCSS, shadcn/ui
- **Realtime** : WebSocket natif FastAPI (chat cookbook)
- **Auth** : fastapi-users (local) + OAuth2 (Google, GitHub, Microsoft) via authlib
- **Recherche** : PostgreSQL Full Text Search (tsvector + pg_trgm)
- **Conteneurisation** : Docker + docker-compose

## Demarrage rapide

`ash
git clone <url>
cd supmeal
cp .env.example .env
docker compose up --build
`

- API : http://localhost:8000
- Documentation OpenAPI : http://localhost:8000/docs
- Web : http://localhost:5173

## Structure

`
.
|-- server/          # API FastAPI
|-- web/             # Client React
|-- docs/            # Documentation technique + manuel utilisateur
|-- docker-compose.yml
`

## Documentation

- Guide technique : docs/technical/
- Manuel utilisateur : docs/user/
- Charte graphique : docs/design/

## Licence

Projet academique - SUPMEAL Pro.

