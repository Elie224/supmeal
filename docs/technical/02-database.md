# Schema de la base de donnees

## Vue d ensemble

PostgreSQL 16. Les principales tables :

```
users
  |--< recipes >-- recipe_ingredients
  |             >-- recipe_steps
  |             >-- recipe_tags >-- tags
  |             >-- comments
  |             >-- meal_plans
  |
  |--< cookbooks >-- cookbook_members
  |              >-- cookbook_messages
  |              >-- recipes (recettes du cookbook)
  |
  |--< shopping_lists >-- shopping_list_items
```

## Tables

### `users`

| Colonne | Type | Contraintes |
|---------|------|-------------|
| id | SERIAL | PK |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| username | VARCHAR(50) | UNIQUE, NOT NULL |
| full_name | VARCHAR(120) | |
| avatar_url | VARCHAR(500) | |
| hashed_password | VARCHAR(255) | (NULL si OAuth) |
| auth_provider | ENUM(local, google, github) | NOT NULL |
| provider_user_id | VARCHAR(255) | (pour lier OAuth) |
| role | ENUM(user, admin) | NOT NULL |
| is_active | BOOLEAN | |
| is_verified | BOOLEAN | |
| dietary_preferences | TEXT | |
| allergies | TEXT | |
| favorite_cuisines | TEXT | |
| default_servings | INTEGER | |
| created_at, updated_at | TIMESTAMPTZ | |

### `recipes`

| Colonne | Type | Contraintes |
|---------|------|-------------|
| id | SERIAL | PK |
| title | VARCHAR(200) | NOT NULL |
| description | TEXT | |
| source_url | VARCHAR(1000) | |
| prep_time_minutes, cook_time_minutes | INTEGER | |
| servings | INTEGER | |
| difficulty, cuisine_type | VARCHAR | |
| image_url | VARCHAR(500) | |
| is_favorite, is_public | BOOLEAN | |
| owner_id | INT | FK users(id) ON DELETE CASCADE |
| cookbook_id | INT | FK cookbooks(id) ON DELETE CASCADE |
| search_vector | TSVECTOR | (indexe GIN) |

### `recipe_ingredients`, `recipe_steps`

Listes structurees liees a `recipes` (CASCADE).

### `recipe_tags` + `tags`

Table d association N-N entre recettes et tags.

### `meal_plans`

Planification d une recette a une date + un creneau.

### `comments`

Commentaires sur une recette (utilises dans les cookbooks).

### `cookbooks`

| Colonne | Type | Contraintes |
|---------|------|-------------|
| id | SERIAL | PK |
| name | VARCHAR(150) | NOT NULL |
| description | TEXT | |
| image_url | VARCHAR(500) | |
| owner_id | INT | FK users(id) ON DELETE CASCADE |

### `cookbook_members`

Lien N-N avec role (creator / editor / commentator / reader).

### `cookbook_messages`

Messages de chat par cookbook, classes par `created_at`.

### `shopping_lists` + `shopping_list_items`

Listes de courses generees depuis le planning.

## Index

- `users.email`, `users.username` : UNIQUE B-tree.
- `recipes.title` : B-tree + GIN trigram (`gin_trgm_ops`).
- `recipes.search_vector` : GIN (`to_tsvector`).
- `recipe_ingredients.name` : B-tree.
- `cookbook_messages (cookbook_id, created_at)` : B-tree.
- `meal_plans (user_id, planned_date)` : B-tree composite.

## Recherche plein texte

Un trigger PostgreSQL met a jour automatiquement `search_vector` apres chaque `INSERT/UPDATE` sur `recipes`. Le contenu agrege comprend : titre, description, type de cuisine, difficulte, ingredients (noms), etapes, tags.

Configuration : `to_tsvector('french', ...)` (snowball francais).

## Contraintes d integrite

- `ON DELETE CASCADE` sur toutes les FK d appartenance (recettes -> user/cookbook).
- `UNIQUE (cookbook_id, user_id)` sur `cookbook_members` (pas de doublons).
- `UNIQUE` sur `tags.name` (normalise en lowercase cote serveur).