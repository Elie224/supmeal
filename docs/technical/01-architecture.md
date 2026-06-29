# Architecture globale

## Vue d ensemble

SUPMEAL suit une architecture trois tiers stricte :

```
+------------------------+
|  Client Web (React)    |   <-- aucune logique metier, uniquement UI + appels API
+------------------------+
            |  HTTP/WS (proxy dev : Vite ; prod : reverse-proxy)
            v
+------------------------+
|  API REST (FastAPI)    |   <-- toute la logique applicative
+------------------------+
            |  asyncpg (driver async)
            v
+------------------------+
|  PostgreSQL 16         |   <-- persistance + recherche plein texte
+------------------------+
```

## Briques logicielles

### 1. Client Web (`web/`)

- **Framework** : React 18 + Vite + TypeScript.
- **Routing** : React Router v6.
- **State serveur** : TanStack Query (cache, invalidation, refetch).
- **State local** : Zustand (auth persistee dans localStorage).
- **UI** : TailwindCSS + composants custom (charte graphique) + icones Lucide.
- **Communication** : `axios` pour le REST, `WebSocket` natif pour le chat.

Aucun secret ni logique metier sur le client : il sert uniquement d interface et delegue tout au serveur.

### 2. Serveur API (`server/`)

- **Framework** : FastAPI (async, OpenAPI auto-genere).
- **ORM** : SQLAlchemy 2 (async) + Alembic pour les migrations.
- **Validation** : Pydantic v2 (schemas separes des modeles SQLAlchemy).
- **Auth** : JWT (passlib + bcrypt + python-jose) ; OAuth2 via Authlib (Google, GitHub, Microsoft).
- **Realtime** : WebSocket natif FastAPI pour le chat cookbook (ConnectionManager par cookbook).
- **Recherche** : PostgreSQL FTS (`tsvector` + index GIN + extension pg_trgm).
- **Uploads** : fichiers stockes sur disque dans un volume Docker, servis par `StaticFiles`.

### 3. Base de donnees (`db`)

- **SGBD** : PostgreSQL 16.
- **Extensions** : `pg_trgm` (trigrammes pour recherche floue), `unaccent` (normalisation).
- **Index** : GIN sur `search_vector`, GIN trigram sur `title`, B-tree sur cles etrangeres.

## Conteneurisation

3 services Docker :

| Service | Image | Role |
|---------|-------|------|
| `db` | postgres:16-alpine | Base de donnees |
| `server` | python:3.12-slim (build local) | API FastAPI |
| `web` | node:20-alpine (build local) | Client React (Vite dev server) |

Le fichier `docker-compose.yml` definit ces services, leurs reseaux et volumes partages. Un healthcheck sur `db` garantit que `server` ne demarre qu une fois la base prete.

## Flux principaux

### Inscription / Connexion

1. Client envoie `POST /api/v1/auth/register` (ou `/login`).
2. Serveur hash le mot de passe (bcrypt) et cree un `User` en base.
3. Serveur genere un JWT (`access_token`) signe avec `JWT_SECRET`.
4. Client stocke le token et l envoie dans le header `Authorization: Bearer ...` a chaque requete.

### Recherche plein texte

1. Client envoie `GET /api/v1/recipes?search=tarte`.
2. Serveur transforme la requete en `to_tsquery('french', 'tarte')` et interroge `search_vector` (index GIN).
3. Fallback `ILIKE` si la requete FTS ne renvoie rien.
4. Trigger PostgreSQL met a jour `search_vector` automatiquement a chaque `INSERT/UPDATE`.

### Chat cookbook (WebSocket)

1. Client ouvre `ws://server/api/v1/cookbooks/ws/{id}?token=...`.
2. Serveur valide le token et verifie que l utilisateur est membre.
3. Chaque message envoye est persiste puis diffuse a tous les clients connectes du meme cookbook.