"""Endpoints Shopping List : generation et gestion des listes de courses."""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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


class ShoppingListUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_completed: bool | None = None


class ShoppingItemCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: float | None = None
    unit: str | None = Field(default=None, max_length=50)
    is_checked: bool = False


class ShoppingItemUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    quantity: float | None = None
    unit: str | None = Field(default=None, max_length=50)
    is_checked: bool | None = None


async def _get_owned_list_or_404(
    db: AsyncSession, current_user: CurrentUser, list_id: int
) -> ShoppingList:
    result = await db.execute(
        select(ShoppingList).where(
            (ShoppingList.id == list_id) & (ShoppingList.user_id == current_user.id)
        )
    )
    sl = result.scalar_one_or_none()
    if not sl:
        raise HTTPException(status_code=404, detail="Liste introuvable")
    return sl


async def _get_owned_item_or_404(
    db: AsyncSession, current_user: CurrentUser, list_id: int, item_id: int
) -> ShoppingListItem:
    stmt = (
        select(ShoppingListItem)
        .join(ShoppingList, ShoppingList.id == ShoppingListItem.shopping_list_id)
        .where(
            (ShoppingListItem.id == item_id)
            & (ShoppingListItem.shopping_list_id == list_id)
            & (ShoppingList.user_id == current_user.id)
        )
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item introuvable")
    return item


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
    sl = await _get_owned_list_or_404(db, current_user, list_id)
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


@router.patch("/{list_id}")
async def update_shopping_list(
    list_id: int,
    payload: ShoppingListUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    sl = await _get_owned_list_or_404(db, current_user, list_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        sl.name = data["name"].strip()
    if "is_completed" in data and data["is_completed"] is not None:
        sl.is_completed = bool(data["is_completed"])
    db.add(sl)
    await db.commit()
    await db.refresh(sl)
    return {
        "id": sl.id,
        "name": sl.name,
        "start_date": sl.start_date,
        "end_date": sl.end_date,
        "is_completed": sl.is_completed,
        "created_at": sl.created_at.isoformat(),
    }


@router.delete("/{list_id}", status_code=204)
async def delete_shopping_list(
    list_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    sl = await _get_owned_list_or_404(db, current_user, list_id)
    await db.delete(sl)
    await db.commit()


@router.post("/{list_id}/items", status_code=201)
async def add_shopping_item(
    list_id: int,
    payload: ShoppingItemCreateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_owned_list_or_404(db, current_user, list_id)
    item = ShoppingListItem(
        shopping_list_id=list_id,
        name=payload.name.strip().lower(),
        quantity=payload.quantity,
        unit=payload.unit.strip().lower() if payload.unit else None,
        is_checked=payload.is_checked,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {
        "id": item.id,
        "name": item.name,
        "quantity": item.quantity,
        "unit": item.unit,
        "is_checked": item.is_checked,
    }


@router.patch("/{list_id}/items/{item_id}")
async def update_shopping_item(
    list_id: int,
    item_id: int,
    payload: ShoppingItemUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await _get_owned_item_or_404(db, current_user, list_id, item_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        item.name = data["name"].strip().lower()
    if "quantity" in data:
        item.quantity = data["quantity"]
    if "unit" in data:
        item.unit = data["unit"].strip().lower() if data["unit"] else None
    if "is_checked" in data and data["is_checked"] is not None:
        item.is_checked = bool(data["is_checked"])
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {
        "id": item.id,
        "name": item.name,
        "quantity": item.quantity,
        "unit": item.unit,
        "is_checked": item.is_checked,
    }


@router.delete("/{list_id}/items/{item_id}", status_code=204)
async def delete_shopping_item(
    list_id: int,
    item_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    item = await _get_owned_item_or_404(db, current_user, list_id, item_id)
    await db.delete(item)
    await db.commit()
