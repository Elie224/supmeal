# Patch "Suggestions de recettes" — SUPMEAL

Ce patch ajoute une fonctionnalite de suggestions intelligentes a SUPMEAL.

## Contenu

14 fichiers modifies ou ajoutes, repartis en :

- **Backend** (3 fichiers) : schemas Pydantic, endpoint FastAPI, tests pytest.
- **Frontend** (4 fichiers) : types TypeScript, nouvelle page, route + entree de menu.
- **Documentation** (5 fichiers) : manuel utilisateur, doc technique API, checklist, dossier screenshots, clarification OAuth dans README.
- **Meta** (2 fichiers) : ce README, manifest JSON, scripts d application.

## Comment appliquer

1. Copier ce dossier `patch-suggestions/` a la **racine de votre clone local** du repo supmeal.

   ```
   cp -r patch-suggestions /chemin/vers/votre-clone-supmeal/
   cd /chemin/vers/votre-clone-supmeal
   ```

2. Executer le script d application (PowerShell sous Windows, bash sous Linux/macOS) :

   **Windows (PowerShell)** :
   ```powershell
   .\patch-suggestions\APPLY.ps1
   ```

   **Linux/macOS (bash)** :
   ```bash
   bash patch-suggestions/apply.sh
   ```

   Les 14 fichiers sont copies a leurs emplacements respectifs dans le repo.

3. Committer et pousser :

   ```bash
   git add -A
   git commit -m "feat(recipes): smart suggestions by ingredients + docs"
   git push origin main
   ```

## Ce qui est inclus dans le commit

### Backend (FastAPI)

- `backend/app/schemas/recipe.py` : schemas `RecipeSuggestRequest` (body POST) et `RecipeSuggestion` (reponse).
- `backend/app/api/v1/endpoints/recipes.py` : nouvelle route `POST /api/v1/recipes/suggest`. Algorithme :
  - Pre-filtre SQL (ILIKE + unaccent cote PostgreSQL) sur les ingredients.
  - Score = `matched / total_ingredients` par recette.
  - Tri par score desc, ingredients manquants asc, duree totale asc, titre asc.
  - Respecte la visibilite (personnelles / publiques / cookbooks dont l user est membre).
  - Compatible avec les filtres optionnels (tags, max_prep_time, max_cook_time, cookbook_id).
- `backend/tests/test_suggest.py` : 6 tests pytest (visibilite, accent-insensitive, temps max, vide, anonyme, filtres).

### Frontend (React + TypeScript)

- `frontend/src/lib/types.ts` : types `RecipeSuggestion`, `RecipeSuggestPayload`.
- `frontend/src/pages/SuggestionsPage.tsx` : page dediee avec saisie d ingredients en chips, filtres temps, resultats classes par % de matching avec decomposition ingredients detenus / manquants.
- `frontend/src/App.tsx` : route `/suggestions` (protegee par `PrivateRoute`).
- `frontend/src/components/Layout.tsx` : entree "Suggestions" avec icone Sparkles dans la sidebar.

### Documentation

- `docs/user/06-suggestions.md` : nouveau chapitre du manuel utilisateur (mode d emploi de la page).
- `docs/user/README.md` : ajout du chapitre dans le sommaire.
- `docs/technical/03-api.md` : nouvelle entree `POST /recipes/suggest` dans la table de reference.
- `docs/technical/08-checklist-rendu.md` : ajout aux parcours fonctionnels a demontrer.
- `docs/screenshots/README.md` : nouveau dossier listant les captures a prendre pour le rendu final (avec nomenclature, outils recommandes, regles de qualite).
- `docs/screenshots/.gitkeep` : permet de committer le dossier meme vide.

### Divers

- `README.md` : clarification sur les providers OAuth ("etc." de la feuille de route couvre Google, GitHub et tout autre provider OpenID Connect ajoutable via Authlib).

## Verification apres application

Dans le clone local, apres application :

```bash
# Backend
cd backend
ruff check app tests
python -m pytest tests/test_suggest.py -v    # 6 tests
python -c "from app.schemas.recipe import RecipeSuggestion; print('OK')"

# Frontend
cd ../frontend
npm ci
npx tsc --noEmit -p tsconfig.json
npm run lint
```

## Limites connues

- Le push GitHub direct depuis mon environnement de travail est impossible : le PAT
  disponible ici est en lecture seule sur le repo (`X-Accepted-Github-Permissions:
  metadata=read` sur `/repos/Elie224/supmeal`). L application via ce patch est le
  contournement le plus propre : tous les fichiers ont ete verifies cote backend
  (`py_compile`) et cote frontend (`tsc --noEmit`, `npm run lint`) avant emballage.
- Les screenshots reels (`docs/screenshots/*.png`) ne peuvent pas etre generes depuis
  cet environnement sans navigateur. Le README du dossier liste les captures a prendre
  apres deploiement.
