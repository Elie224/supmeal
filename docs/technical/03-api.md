# API REST - reference rapide

Base URL : `http://localhost:8000/api/v1`
Documentation interactive : `http://localhost:8000/docs` (Swagger UI)

## Auth

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/auth/register` | Inscription (email, username, password) |
| POST | `/auth/login` | Connexion, renvoie `{access_token, user}` |
| GET | `/auth/me` | Profil de l utilisateur connecte |
| GET | `/auth/oauth/{provider}/login` | Redirige vers Google/GitHub/Microsoft |
| GET | `/auth/oauth/{provider}/callback` | Callback OAuth, redirige vers le front avec token |

## Utilisateurs

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/users` | Liste des utilisateurs (pour invitations) |
| GET | `/users/{id}` | Profil public |
| PATCH | `/users/me` | Modifier profil (nom, avatar, preferences) |
| POST | `/users/me/change-password` | Changer le mot de passe |
| POST | `/users/me/avatar` | Upload avatar (multipart) |

## Recettes

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/recipes` | Liste filtree (params : `cookbook_id`, `tag_ids`, `ingredient`, `max_prep_time`, `max_cook_time`, `favorites_only`, `search`, `skip`, `limit`) |
| POST | `/recipes` | Creer une recette personnelle |
| GET | `/recipes/{id}` | Detail |
| PATCH | `/recipes/{id}` | Modifier (owner ou editeur du cookbook) |
| DELETE | `/recipes/{id}` | Supprimer |
| POST | `/recipes/{id}/favorite` | Toggle favori |
| POST | `/recipes/{id}/image` | Upload image |

## Recherche et filtres

Tous les filtres sont cumulables. La recherche utilise PostgreSQL FTS en francais avec fallback trigram.

Exemple : `GET /recipes?search=tarte&max_prep_time=30&favorites_only=true&tag_ids=1`

## Cookbooks

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/cookbooks` | Mes cookbooks |
| POST | `/cookbooks` | Creer un cookbook |
| GET | `/cookbooks/{id}` | Detail avec membres |
| PATCH | `/cookbooks/{id}` | Modifier (createur uniquement) |
| DELETE | `/cookbooks/{id}` | Supprimer (createur uniquement) |
| GET | `/cookbooks/{id}/recipes` | Recettes du cookbook (avec filtres) |
| POST | `/cookbooks/{id}/recipes` | Ajouter une recette au cookbook |

## Membres d un cookbook

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/cookbooks/{id}/members` | Inviter (createur) |
| PATCH | `/cookbooks/{id}/members/{user_id}` | Modifier le role (createur) |
| DELETE | `/cookbooks/{id}/members/{user_id}` | Retirer un membre (createur ou soi-meme) |

Roles : `creator`, `editor`, `commentator`, `reader`.

## Messagerie cookbook

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/cookbooks/{id}/messages` | Historique (pagination `before_id`) |
| POST | `/cookbooks/{id}/messages` | Envoyer un message (sauf lecteurs) |
| WS | `/cookbooks/ws/{id}?token=...` | Chat en temps reel |

## Commentaires recette

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/recipes/{id}/comments` | Liste des commentaires |
| POST | `/recipes/{id}/comments` | Ajouter (tous sauf `reader`) |
| DELETE | `/recipes/{id}/comments/{comment_id}` | Supprimer (auteur uniquement) |

## Planning de repas

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/meal-plans` | Planifier une recette |
| GET | `/meal-plans` | Mes plans (`start_date`, `end_date`) |
| DELETE | `/meal-plans/{id}` | Supprimer un plan |

## Tags

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/tags` | Liste |
| POST | `/tags` | Creer un tag |

## Liste de courses (bonus)

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/shopping/generate` | Genere depuis le planning |
| GET | `/shopping` | Mes listes |
| GET | `/shopping/{id}` | Detail avec items |

## Import / Export

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/import-export/json` | Export JSON complet (recettes + cookbooks) |
| GET | `/import-export/csv` | Export CSV (1 ligne par ingredient) |
| POST | `/import-export/json` | Importer JSON (SUPMEAL ou Mealie) |
| POST | `/import-export/csv` | Importer CSV |

## Authentification

Toutes les routes (sauf `/auth/*`, `/auth/oauth/*`, `/health`, `/docs`) requierent :

```
Authorization: Bearer <access_token>
```

Les tokens expirent apres 24h (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).