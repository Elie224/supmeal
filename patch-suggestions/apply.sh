#!/usr/bin/env bash
# Applique le patch "Suggestions de recettes" sur un clone local du repo supmeal.
# A executer depuis la racine du clone (la ou se trouvent docker-compose.yml, etc.).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_DIR="$SCRIPT_DIR/patch-suggestions"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

declare -a ITEMS=(
  "README.md|README.md"
  "backend/app/schemas/recipe.py|backend/app/schemas/recipe.py"
  "backend/app/api/v1/endpoints/recipes.py|backend/app/api/v1/endpoints/recipes.py"
  "backend/tests/test_suggest.py|backend/tests/test_suggest.py"
  "frontend/src/lib/types.ts|frontend/src/lib/types.ts"
  "frontend/src/pages/SuggestionsPage.tsx|frontend/src/pages/SuggestionsPage.tsx"
  "frontend/src/App.tsx|frontend/src/App.tsx"
  "frontend/src/components/Layout.tsx|frontend/src/components/Layout.tsx"
  "docs/user/README.md|docs/user/README.md"
  "docs/user/06-suggestions.md|docs/user/06-suggestions.md"
  "docs/technical/03-api.md|docs/technical/03-api.md"
  "docs/technical/08-checklist-rendu.md|docs/technical/08-checklist-rendu.md"
  "docs/screenshots/README.md|docs/screenshots/README.md"
  "docs/screenshots/.gitkeep|docs/screenshots/.gitkeep"
)

ok=0
for item in "${ITEMS[@]}"; do
    src_rel="${item%|*}"
    dst_rel="${item#*|}"
    src="$PATCH_DIR/$src_rel"
    dst="$REPO_ROOT/$dst_rel"
    if [ ! -f "$src" ]; then
        echo "  MISSING: $src_rel"
        continue
    fi
    mkdir -p "$(dirname "$dst")"
    cp -f "$src" "$dst"
    echo "  OK   $dst_rel"
    ok=$((ok + 1))
done

echo ""
echo "$ok fichiers appliques."
echo ""
echo "Prochaines etapes :"
echo "  1. git add -A"
echo "  2. git commit -m 'feat(recipes): smart suggestions by ingredients + docs'"
echo "  3. git push origin main"
