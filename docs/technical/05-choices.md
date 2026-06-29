# Justification des choix techniques

## Backend : Python 3.12 + FastAPI

**Pourquoi pas Django ?**
- Django est excellent pour les projets avec admin integre, mais pour une API REST pure il apporte du poids inutile (ORM sync, templates, sessions).
- FastAPI est nativement async, ce qui est important pour les WebSockets (chat cookbook) et les requetes DB concurrentes.
- La generation automatique d OpenAPI par FastAPI simplifie considerablement la documentation.

**Pourquoi pas Node.js (NestJS/Express) ?**
- L ecosysteme Python est tres riche pour le traitement de donnees (parsing d imports, conversion Mealie).
- Le typage strict (Pydantic + mypy) offre une garantie de qualite superieure.
- Python est un standard dans le monde academique francais (et l entreprise SUPMEAL Pro le mentionne).

## ORM : SQLAlchemy 2 (async) + Alembic

- Standard de fait en Python.
- Mode async nativement supporte (moteurs `asyncpg`).
- Alembic gere les migrations de maniere incrementalise.
- Typage complet des modeles.

## Base de donnees : PostgreSQL 16

- Recherche plein texte integree (`tsvector`, `pg_trgm`) : evite de deployer un ElasticSearch ou Meilisearch.
- Contraintes d integrite avancees (CASCADE, triggers).
- Extension `unaccent` pour normaliser les recherches.

## Frontend : React 18 + Vite + TypeScript

- React est le standard de l industrie frontend.
- Vite : demarrage instantane, HMR rapide, build optimise.
- TypeScript pour un code maintenable.
- TailwindCSS pour la productivite et la coherence visuelle.

**Pourquoi pas Next.js ?**
- Le projet impose un client web separe (3 briques). Next.js melange SSR et client, ce qui complique l architecture.
- Un SPA React + Vite est plus simple a conteneuriser.

## Bibliotheques frontend

- **TanStack Query** : cache, invalidation automatique, gestion d etat serveur.
- **Zustand** : store global leger (auth), sans la complexite de Redux.
- **React Hook Form + Zod** : formulaires performants et valides.
- **Lucide React** : icones SVG, legeres, open source.

## Recherche : PostgreSQL FTS (pas d Elasticsearch)

- Suffisant pour 190 pts du bareme (filtrage + recherche plein texte).
- Aucun service externe a deployer.
- Index GIN performant.

## Auth : JWT + bcrypt + Authlib

- JWT stateless : pas de session cote serveur, parfait pour une API REST.
- bcrypt : algorithme de hash reconnu et resistant aux attaques par force brute.
- Authlib : librairie de reference pour OAuth2 en Python (Google, GitHub, Microsoft).

## WebSocket : natif FastAPI

- Pas besoin de Socket.IO (overhead protocole).
- FastAPI gere parfaitement le multiplexage via son `ConnectionManager`.

## Conteneurisation

- **Multi-stage builds** : images optimisees (futur).
- **Volumes nommes** : persistance des donnees (DB, uploads).
- **Healthcheck** sur la DB : le serveur ne demarre qu une fois la base prete.
- **docker-compose v2** : syntaxe moderne, profiles par environnement (futur).

## Qualite du code

- **Ruff** : linter + formateur ultra rapide (remplace flake8, isort, black).
- **mypy** : verification de types statique.
- **Tests** : pytest + httpx AsyncClient pour les tests d integration.
- **Separation des responsabilites** : `models/`, `schemas/`, `services/`, `api/v1/endpoints/`.

## Securite

- Mots de passe hasher (bcrypt 12 rounds) ; aucune trace en clair.
- Secrets dans `.env` (jamais commit grace a `.gitignore` et `.env.example`).
- Validation des entrees (Pydantic) : pas d injection possible.
- CORS strictement configure.
- Pas d authentification par cookie (XSS-safe) : JWT dans le header.