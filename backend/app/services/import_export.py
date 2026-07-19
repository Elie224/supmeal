"""Utilitaires Import/Export : conversion Mealie / SUPMEAL."""

from typing import Any


def recipe_to_dict(recipe: Any) -> dict[str, Any]:
    """Convertit un objet Recipe SQLAlchemy en dict serialisable pour export."""
    return {
        "title": recipe.title,
        "description": recipe.description,
        "source_url": recipe.source_url,
        "prep_time_minutes": recipe.prep_time_minutes,
        "cook_time_minutes": recipe.cook_time_minutes,
        "servings": recipe.servings,
        "difficulty": recipe.difficulty,
        "cuisine_type": recipe.cuisine_type,
        "image_url": recipe.image_url,
        "ingredients": [
            {
                "name": i.name,
                "quantity": i.quantity,
                "unit": i.unit,
                "note": i.note,
            }
            for i in recipe.ingredients
        ],
        "steps": [{"content": s.content} for s in recipe.steps],
        "tag_names": [t.name for t in recipe.tags],
    }


def mealie_to_recipe(mealie_data: dict[str, Any]) -> dict[str, Any]:
    """Convertit une recette au format Mealie vers le format SUPMEAL."""
    return {
        "title": mealie_data.get("name") or "Sans titre",
        "description": mealie_data.get("description"),
        "source_url": mealie_data.get("orgURL"),
        "prep_time_minutes": _parse_minutes(mealie_data.get("prepTime")),
        "cook_time_minutes": _parse_minutes(mealie_data.get("cookTime")),
        "servings": mealie_data.get("recipeServings") or 4,
        "cuisine_type": None,
        "image_url": mealie_data.get("image"),
        "ingredients": [
            {
                "name": i.get("note", ""),
                "unit": i.get("unit", {}).get("name") if isinstance(i.get("unit"), dict) else None,
                "quantity": _to_float(i.get("quantity")),
            }
            for i in mealie_data.get("recipeIngredient", [])
        ],
        "steps": [
            {"content": "\n".join(s.get("text", "").split("\n"))}
            for s in mealie_data.get("recipeInstructions", [])
        ],
        "tag_names": [
            t.get("name", "").lower()
            for t in mealie_data.get("tags", [])
            if t.get("name")
        ],
    }


def _parse_minutes(value: Any) -> int:
    if not value:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return 0
    # Format ISO 8601 : PT15M
    if s.startswith("PT"):
        minutes = 0
        iso = s[2:]
        if "H" in iso:
            h_part, iso = iso.split("H", 1)
            minutes += int(h_part or 0) * 60
        if "M" in iso:
            m_part = iso.split("M", 1)[0]
            minutes += int(m_part or 0)
        return minutes
    # Format "30 min"
    digits = "".join(c for c in s if c.isdigit())
    return int(digits) if digits else 0


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None