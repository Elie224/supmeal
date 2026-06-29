# Diagrammes UML

## 1. Diagramme de cas d utilisation

```
                              +-----------------+
                              |    Utilisateur  |
                              +-----------------+
                                     |
                +--------------------+--------------------+
                |                    |                    |
         +------v------+      +------v------+      +------v------+
         |  Creer un   |      |  Consulter  |      |  Partager   |
         |  compte     |      |  une recette|      |  via OAuth  |
         +-------------+      +-------------+      +-------------+
                                       |
                          +------------+-------------+
                          |            |             |
                  +-------v-----+ +----v----+  +-----v------+
                  | Rechercher  | | Filtrer |  |  Favoris   |
                  +-------------+ +---------+  +------------+

                              +-----------------+
                              | Membre cookbook |
                              +-----------------+
                                     |
                +--------------------+--------------------+
                |                    |                    |
         +------v------+      +------v------+      +------v------+
         |  Commenter  |      | Discuter en |      |  Planifier  |
         |  une recette|      |   chat      |      |  un repas   |
         +-------------+      +-------------+      +-------------+
```

## 2. Diagramme de classes (extrait)

```
+----------------+        +------------------+
|     User       |        |    Cookbook      |
+----------------+        +------------------+
| id: int        |<>------| id: int          |
| email: str     |  owner | name: str        |
| username: str  |        | description: str |
| password: str  |        +------------------+
| auth_provider  |                |
| role: enum     |                | 1
+----------------+                | owns
        | 1                       |
        |                          v many
        | creates           +------------------+
        | many              |  CookbookMember  |
        v                   +------------------+
+----------------+        | role: enum       |
|    Recipe      |        | user_id: FK      |
+----------------+        | cookbook_id: FK  |
| id: int        |        +------------------+
| title: str     |
| description    |        +------------------+
| prep_time      |        |      Tag         |
| cook_time      |        +------------------+
| servings       |        | id: int          |
| difficulty     |        | name: str        |
| is_favorite    |        | category: str    |
| is_public      |        +------------------+
| search_vector  |                ^
+----------------+                | N-N
        | many                    |
        | has              +------+
        v                   |
+----------------+    +-----+--------+
| RecipeIngredient|   |  RecipeTag    |
+----------------+    +--------------+

+----------------+        +------------------+
|   MealPlan     |        |  ShoppingList    |
+----------------+        +------------------+
| recipe_id: FK  |        | user_id: FK      |
| planned_date   |        | start_date       |
| meal_slot      |        | end_date         |
| servings       |        | is_completed     |
+----------------+        +------------------+
                                  | 1
                                  | has
                                  v many
                          +------------------+
                          | ShoppingListItem |
                          +------------------+
                          | name, qty, unit  |
                          | is_checked       |
                          +------------------+
```

## 3. Diagramme de sequence : Creation d une recette

```
Client            API FastAPI          PostgreSQL
  |                     |                    |
  |--POST /recipes----->|                    |
  |   (JWT, payload)    |                    |
  |                     |--INSERT recipe----->|
  |                     |                    |
  |                     |--INSERT ingredient->|
  |                     |--INSERT step------>|
  |                     |--INSERT tag_link-->|
  |                     |                    |
  |                     |--trigger met a jour|
  |                     |  search_vector     |
  |                     |                    |
  |<--201 + Recipe------|                    |
  |                     |                    |
```

## 4. Diagramme de sequence : Chat cookbook (WebSocket)

```
Client A          Serveur WS         Client B
  |                    |                 |
  |---WS open--------->|                 |
  |  (token)           |                 |
  |<--accept-----------|                 |
  |                    |                 |
  |---{content:"hi"}-->|                 |
  |                    |--persist msg    |
  |                    |                 |
  |                    |--broadcast------>|
  |                    |                 |
  |<--{content:"hi"}---|-----------------|
  |                    |                 |
```

## 5. Architecture deploiement

```
+---------------------------------------+
|  Docker host                          |
|                                       |
|  +-----------+   +-----------+        |
|  |  web      |   |  server   |        |
|  |  (5173)   |   |  (8000)   |        |
|  +-----------+   +-----------+        |
|        |               |              |
|        +-------+-------+              |
|                |                      |
|          +-----v-----+                |
|          |   db      |                |
|          |  (5432)   |                |
|          +-----------+                |
+---------------------------------------+
```