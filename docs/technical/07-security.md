# Securite

SUPMEAL suit les bonnes pratiques de securite applicative.

## Mots de passe

- **Hashage bcrypt** avec 12 rounds (`passlib.context.CryptContext`).
- Les mots de passe ne sont **jamais** stockes en clair.
- Les comptes OAuth (Google/GitHub) n ont pas de mot de passe local (`hashed_password = NULL`).
- Limite bcrypt 72 octets appliquee via troncature avant hash (compatibilite bcrypt).

## Authentification

- JWT signe avec `JWT_SECRET` (variable d environnement obligatoire).
- Duree de vie configurable (`ACCESS_TOKEN_EXPIRE_MINUTES`, defaut 24h).
- Le serveur decode le token a chaque requete protegee ; aucune session serveur.
- Le serveur pose un cookie httpOnly `supmeal_token` et un cookie CSRF `supmeal_csrf` (pattern double-submit).
- Le client envoie `X-CSRF-Token` sur les requetes mutantes et peut aussi utiliser `Authorization: Bearer` en fallback de compatibilite.

## Validation des entrees

- Pydantic v2 valide toutes les entrees (longueurs, formats email, regex username).
- Pas d injection SQL possible : SQLAlchemy parametre toutes les requetes.
- Pas d injection XSS : le frontend React echappe automatiquement le contenu.

## Secrets

- `.env.example` documente les variables ; `.env` (reel) est dans `.gitignore`.
- Aucun secret n est commit dans le depot.
- Pour la production : generer des valeurs aleatoires d au moins 32 caracteres pour `SECRET_KEY` et `JWT_SECRET`.

## CORS

- Liste blanche d origines configurable via `BACKEND_CORS_ORIGINS`.
- En production, n autoriser que le domaine reel.

## Uploads

- Types MIME verifies (JPEG, PNG, WebP, GIF uniquement).
- Taille max configurable (`MAX_UPLOAD_SIZE_MB`).
- Noms de fichiers randomises (UUID) pour eviter les collisions et path traversal.

## Cookies / CORS

- Auth cookie-based en `SameSite=Lax` et `Secure` en production.
- Protection CSRF active sur POST/PUT/PATCH/DELETE via verification cookie/header.
- `allow_credentials=true` est necessaire pour transporter les cookies entre front et API.

## Logs

- Pas de logs de mots de passe ou de tokens.
- Logs structures recommandes en production (hors scope de ce livrable).