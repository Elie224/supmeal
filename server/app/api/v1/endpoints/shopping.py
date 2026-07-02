"""Endpoints Shopping List : generation automatique depuis le planning."""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models.cookbook import CookbookMember
from app.models.recipe import MealPlan, Recipe, RecipeIngredient
from app.models.shopping import ShoppingList, ShoppingListItem

router = APIRouter()


class GenerateListRequest(BaseModel):
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    cookbook_id: int | None = None
    name: str | None = None


@router.post("/generate", status_code=201)
async def generate_shopping_list(
    payload: GenerateListRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Agrege les ingredients de toutes les recettes planifiees sur la periode."""
    if payload.cookbook_id is not None:
        membership = await db.execute(
            select(CookbookMember).where(
                (CookbookMember.cookbook_id == payload.cookbook_id)
                & (CookbookMember.user_id == current_user.id)
            )
        )
        if membership.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Vous n'etes pas membre de ce cookbook")

    stmt = (
        select(MealPlan, Recipe)
        .join(Recipe, Recipe.id == MealPlan.recipe_id)
        .where(
            (MealPlan.planned_date >= payload.start_date)
            & (MealPlan.planned_date <= payload.end_date)
        )
    )
    if payload.cookbook_id is not None:
        stmt = stmt.where(MealPlan.cookbook_id == payload.cookbook_id)
    else:
        stmt = stmt.where((MealPlan.user_id == current_user.id) & (MealPlan.cookbook_id.is_(None)))

    result = await db.execute(
        stmt.options()
    )
    rows = result.all()
    if not rows:
        raise HTTPException(status_code=404, detail="Aucun repas planifie sur cette periode")

    # Collecter tous les ingredients
    aggregated: dict[tuple[str, str | None], float] = defaultdict(float)
    for mp, recipe in rows:
        # Ajuster les quantites en fonction des servings
        factor = (mp.servings or 1) / max(recipe.servings or 1, 1)
        ing_result = await db.execute(
            select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
        )
        for ing in ing_result.scalars().all():
            key = (ing.name.lower().strip(), ing.unit)
            qty = (ing.quantity or 0) * factor
            aggregated[key] += qty

    name = payload.name or f"Courses du {payload.start_date} au {payload.end_date}"
    shopping_list = ShoppingList(
        user_id=current_user.id,
        name=name,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(shopping_list)
    await db.flush()
    for (iname, unit), qty in aggregated.items():
        db.add(
            ShoppingListItem(
                shopping_list_id=shopping_list.id,
                name=iname,
                quantity=qty if qty > 0 else None,
                unit=unit,
            )
        )
    await db.commit()
    return {"id": shopping_list.id, "items_count": len(aggregated)}


@router.get("")
async def list_shopping_lists(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> list[dict]:
    result = await db.execute(
        select(ShoppingList)
        .where(ShoppingList.user_id == current_user.id)
        .order_by(ShoppingList.created_at.desc())
    )
    return [
        {
            "id": sl.id,
            "name": sl.name,
            "start_date": sl.start_date,
            "end_date": sl.end_date,
            "is_completed": sl.is_completed,
            "created_at": sl.created_at.isoformat(),
        }
        for sl in result.scalars().all()
    ]


@router.get("/{list_id}")
async def get_shopping_list(
    list_id: int, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await db.execute(
        select(ShoppingList)
        .where((ShoppingList.id == list_id) & (ShoppingList.user_id == current_user.id))
    )
    sl = result.scalar_one_or_none()
    if not sl:
        raise HTTPException(status_code=404, detail="Liste introuvable")
    items_result = await db.execute(
        select(ShoppingListItem).where(ShoppingListItem.shopping_list_id == list_id)
    )
    return {
        "id": sl.id,
        "name": sl.name,
        "start_date": sl.start_date,
        "end_date": sl.end_date,
        "is_completed": sl.is_completed,
        "items": [
            {
                "id": it.id,
                "name": it.name,
                "quantity": it.quantity,
                "unit": it.unit,
                "is_checked": it.is_checked,
            }
            for it in items_result.scalars().all()
        ],
    }