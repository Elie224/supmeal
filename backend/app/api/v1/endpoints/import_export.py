"""Endpoints Import / Export."""

import csv
import io
import json
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, get_db
from app.models.cookbook import Cookbook, CookbookMember, CookbookRole
from app.models.recipe import (
    Recipe,
    RecipeIngredient,
    RecipeStep,
    RecipeTag,
    Tag,
)
from app.schemas.recipe import RecipeRead
from app.core.security_utils import sanitize_csv_cell
from app.services.import_export import mealie_to_recipe, recipe_to_dict

router = APIRouter()


def _parse_int(value: Any, field_name: str, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Valeur invalide pour {field_name}: {value}")


def _parse_float(value: Any, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Valeur invalide pour {field_name}: {value}")


# ---------- Export ----------

@router.get("/json")
async def export_json(current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Exporte toutes les recettes personnelles + cookbooks en JSON brut."""
    member_cb_subq = select(CookbookMember.cookbook_id).where(CookbookMember.user_id == current_user.id)
    recipes_result = await db.execute(
        select(Recipe)
        .options(selectinload(Recipe.ingredients), selectinload(Recipe.steps), selectinload(Recipe.tags))
        .where(or_(Recipe.owner_id == current_user.id, Recipe.cookbook_id.in_(member_cb_subq)))
    )
    recipes = [recipe_to_dict(r) for r in recipes_result.scalars().unique().all()]

    cookbooks_result = await db.execute(
        select(Cookbook)
        .options(selectinload(Cookbook.members))
        .where(Cookbook.owner_id == current_user.id)
    )
    cookbooks = []
    for cb in cookbooks_result.scalars().all():
        cb_recipes = await db.execute(
            select(Recipe)
            .options(
                selectinload(Recipe.ingredients),
                selectinload(Recipe.steps),
                selectinload(Recipe.tags),
            )
            .where(Recipe.cookbook_id == cb.id)
        )
        cookbooks.append({
            "name": cb.name,
            "description": cb.description,
            "members": [{"user_id": m.user_id, "role": m.role.value} for m in cb.members],
            "recipes": [recipe_to_dict(r) for r in cb_recipes.scalars().unique().all()],
        })

    return {
        "format": "supmeal-json",
        "version": 1,
        "user": {"username": current_user.username, "email": current_user.email},
        "recipes": recipes,
        "cookbooks": cookbooks,
    }


@router.get("/csv")
async def export_csv(current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """Exporte les recettes en CSV (1 ligne par ingredient)."""
    member_cb_subq = select(CookbookMember.cookbook_id).where(
        CookbookMember.user_id == current_user.id
    )
    recipes_result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.steps),
            selectinload(Recipe.tags),
        )
        .where(or_(Recipe.owner_id == current_user.id, Recipe.cookbook_id.in_(member_cb_subq)))
    )
    recipes = recipes_result.scalars().unique().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "title", "description", "servings", "prep_time", "cook_time",
        "ingredient", "quantity", "unit", "step", "tags", "source",
    ])
    for r in recipes:
        steps_dict = {s.position: s.content for s in r.steps}
        max_step = max(steps_dict.keys()) if steps_dict else 0
        tags_str = ",".join(t.name for t in r.tags)
        for ing in r.ingredients:
            row = [
                sanitize_csv_cell(r.title),
                sanitize_csv_cell(r.description or ""),
                r.servings,
                r.prep_time_minutes,
                r.cook_time_minutes,
                sanitize_csv_cell(ing.name),
                ing.quantity or "",
                sanitize_csv_cell(ing.unit or ""),
                "",
                sanitize_csv_cell(tags_str),
                sanitize_csv_cell(r.source_url or ""),
            ]
            writer.writerow(row)
        # Une ligne par etape pour les etapes
        for pos in range(1, max_step + 1):
            writer.writerow([
                sanitize_csv_cell(r.title),
                sanitize_csv_cell(r.description or ""),
                r.servings,
                r.prep_time_minutes,
                r.cook_time_minutes,
                "",
                "",
                "",
                sanitize_csv_cell(steps_dict.get(pos, "")),
                sanitize_csv_cell(tags_str),
                sanitize_csv_cell(r.source_url or ""),
            ])

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=supmeal_export.csv"},
    )


# ---------- Import ----------

@router.post("/json", status_code=201)
async def import_json(
    file: UploadFile = File(...),
    current_user: CurrentUser = ...,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Importe un JSON SUPMEAL ou compatible Mealie."""
    # Anti-DoS : limite a 5 MB pour l import JSON
    MAX_IMPORT_SIZE = 5 * 1024 * 1024
    content = await file.read(MAX_IMPORT_SIZE + 1)
    if len(content) > MAX_IMPORT_SIZE:
        raise HTTPException(status_code=413, detail="Fichier d import trop volumineux (max 5 MB)")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON invalide: {e}")

    fmt = data.get("format", "supmeal-json")
    recipes = []
    if fmt == "mealie":
        recipes = [mealie_to_recipe(r) for r in data.get("recipes", [])]
    else:
        recipes = data.get("recipes", [])

    count = 0
    for r in recipes:
        await _create_recipe_from_dict(db, current_user.id, r)
        count += 1

    # Cookbooks (uniquement format supmeal-json)
    for cb in data.get("cookbooks", []):
        cb_obj = Cookbook(
            name=cb["name"],
            description=cb.get("description"),
            owner_id=current_user.id,
        )
        db.add(cb_obj)
        await db.flush()
        db.add(
            CookbookMember(cookbook_id=cb_obj.id, user_id=current_user.id, role=CookbookRole.CREATOR)
        )
        for r in cb.get("recipes", []):
            await _create_recipe_from_dict(db, current_user.id, r, cookbook_id=cb_obj.id)
            count += 1
    await db.commit()
    return {"imported_recipes": count}


@router.post("/csv", status_code=201)
async def import_csv(
    file: UploadFile = File(...),
    current_user: CurrentUser = ...,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Importe un CSV. Le regroupement par titre est automatique."""
    MAX_IMPORT_SIZE = 5 * 1024 * 1024
    raw = await file.read(MAX_IMPORT_SIZE + 1)
    if len(raw) > MAX_IMPORT_SIZE:
        raise HTTPException(status_code=413, detail="Fichier d import trop volumineux (max 5 MB)")
    content = raw.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    by_title: dict[str, dict[str, Any]] = {}
    for line_no, row in enumerate(reader, start=2):
        title = sanitize_csv_cell((row.get("title") or "").strip())
        if not title:
            continue
        if title not in by_title:
            by_title[title] = {
                "title": title,
                "description": row.get("description") or None,
                "servings": _parse_int(row.get("servings"), f"servings (ligne {line_no})", 4),
                "prep_time_minutes": _parse_int(row.get("prep_time"), f"prep_time (ligne {line_no})", 0),
                "cook_time_minutes": _parse_int(row.get("cook_time"), f"cook_time (ligne {line_no})", 0),
                "source_url": row.get("source") or None,
                "ingredients": [],
                "steps": [],
                "tag_names": [t.strip() for t in (row.get("tags") or "").split(",") if t.strip()],
            }
        entry = by_title[title]
        ing_name = (row.get("ingredient") or "").strip()
        if ing_name:
            entry["ingredients"].append({
                "name": ing_name,
                "quantity": _parse_float(row.get("quantity"), f"quantity (ligne {line_no})"),
                "unit": row.get("unit") or None,
            })
        step_content = (row.get("step") or "").strip()
        if step_content:
            entry["steps"].append({"content": step_content})
    count = 0
    for r in by_title.values():
        await _create_recipe_from_dict(db, current_user.id, r)
        count += 1
    await db.commit()
    return {"imported_recipes": count}


async def _create_recipe_from_dict(
    db: AsyncSession, user_id: int, data: dict[str, Any], cookbook_id: int | None = None
) -> Recipe:
    """Helper : cree une recette a partir d'un dict (import)."""
    recipe = Recipe(
        title=data.get("title", "Sans titre"),
        description=data.get("description"),
        source_url=data.get("source_url") or data.get("source"),
        prep_time_minutes=_parse_int(data.get("prep_time_minutes"), "prep_time_minutes", 0),
        cook_time_minutes=_parse_int(data.get("cook_time_minutes"), "cook_time_minutes", 0),
        servings=_parse_int(data.get("servings"), "servings", 4),
        difficulty=data.get("difficulty"),
        cuisine_type=data.get("cuisine_type") or data.get("cuisine"),
        image_url=data.get("image_url") or data.get("image"),
        owner_id=user_id,
        cookbook_id=cookbook_id,
    )
    db.add(recipe)
    await db.flush()
    for i, ing in enumerate(data.get("ingredients", [])):
        if isinstance(ing, dict):
            db.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    name=ing.get("name", ""),
                    quantity=ing.get("quantity"),
                    unit=ing.get("unit"),
                    position=i,
                )
            )
    for i, step in enumerate(data.get("steps", [])):
        content = step.get("content") if isinstance(step, dict) else str(step)
        db.add(
            RecipeStep(recipe_id=recipe.id, content=content, position=i)
        )
    for tag_name in data.get("tag_names") or []:
        tag_name = tag_name.lower().strip()
        if not tag_name:
            continue
        result = await db.execute(select(Tag).where(Tag.name == tag_name))
        tag = result.scalar_one_or_none()
        if not tag:
            tag = Tag(name=tag_name)
            db.add(tag)
            await db.flush()
        db.add(RecipeTag(recipe_id=recipe.id, tag_id=tag.id))

    # Garder la recherche plein texte coherente apres import.
    parts = [
        recipe.title or "",
        recipe.description or "",
        recipe.cuisine_type or "",
        recipe.difficulty or "",
    ]
    parts.extend(str(ing.get("name", "")) for ing in data.get("ingredients", []) if isinstance(ing, dict))
    parts.extend(
        str(step.get("content", "")) if isinstance(step, dict) else str(step)
        for step in data.get("steps", [])
    )
    parts.extend(str(t).strip().lower() for t in (data.get("tag_names") or []) if str(t).strip())
    await db.execute(
        text("UPDATE recipes SET search_vector = to_tsvector('french', :txt) WHERE id = :rid"),
        {"txt": " ".join(parts), "rid": recipe.id},
    )

    return recipe