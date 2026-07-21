# SUPMEAL

[![CI](https://github.com/Elie224/supmeal/actions/workflows/ci.yml/badge.svg)](https://github.com/Elie224/supmeal/actions/workflows/ci.yml)

Application web de gestion de recettes et planification de repas, developpee pour la societe SUPMEAL Pro.

Alternative a Mealie, Tandoor Recipes, Paprika : creer, importer, organiser et planifier des recettes de cuisine, seul ou en cookbook partage.

## Stack

- **Backend** : Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16
- **Frontend** : React 18, Vite, TypeScript, TailwindCSS, shadcn/ui
- **Realtime** : WebSocket natif FastAPI (chat cookbook)
- **Auth** : authentification locale JWT + OAuth2 (Google, GitHub) via Authlib. La feuille de route mentionne OAuth2 au sens large (Google, Microsoft, GitHub, etc.). Microsoft et tout autre provider OpenID Connect peuvent etre ajoutes via la meme couche Authlib (provider deja enregistre dans pp/api/v1/endpoints/oauth.py).
- **Recherche** : PostgreSQL Full Text Search (tsvector + pg_trgm)
- **Conteneurisation** : Docker + docker-compose

### Regle de discussion collaborative

- Tous les membres d un cookbook (`creator`, `editor`, `commentator`, `reader`) peuvent participer au chat.
- Le role `reader` reste en lecture seule pour les actions d edition de contenu (recettes, etc.).

## Demarrage rapide

> Important : `docker compose up --build` (sans override) demarre seulement l'API et la base.
> Pour avoir l'application complete (frontend + backend), utilisez explicitement un override.

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


