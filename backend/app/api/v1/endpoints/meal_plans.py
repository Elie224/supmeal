"""Endpoints Meal Plans accessibles depuis /api/v1/meal-plans."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models.cookbook import CookbookMember, CookbookRole
from app.models.recipe import MealPlan, Recipe
from app.schemas.recipe import MealPlanCreate, MealPlanRead

router = APIRouter()


async def _get_member_role(
    db: AsyncSession, cookbook_id: int, user_id: int
) -> CookbookRole | None:
    result = await db.execute(
        select(CookbookMember).where(
            (CookbookMember.cookbook_id == cookbook_id) & (CookbookMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    return member.role if member else None


_ALLOWED_MEAL_SLOTS = {"breakfast", "lunch", "dinner", "snack"}


@router.post("", response_model=MealPlanRead, status_code=201)
async def create_meal_plan(
    payload: MealPlanCreate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> MealPlanRead:
    # Validation meal_slot (whitelist)
    if payload.meal_slot not in _ALLOWED_MEAL_SLOTS:
        raise HTTPException(status_code=400, detail="meal_slot invalide")
    # Validation planned_date format
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", payload.planned_date or ""):
        raise HTTPException(status_code=400, detail="planned_date doit etre YYYY-MM-DD")

    result = await db.execute(select(Recipe).where(Recipe.id == payload.recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette introuvable")

    if payload.cookbook_id is not None:
        role = await _get_member_role(db, payload.cookbook_id, current_user.id)
        if role is None:
            raise HTTPException(status_code=403, detail="Vous n'etes pas membre de ce cookbook")
        if role == CookbookRole.READER:
            raise HTTPException(status_code=403, detail="Permission insuffisante")
        if recipe.cookbook_id != payload.cookbook_id:
            raise HTTPException(
                status_code=400,
                detail="La recette doit appartenir au cookbook du planning",
            )
        existing = await db.execute(
            select(MealPlan).where(
                (MealPlan.cookbook_id == payload.cookbook_id)
                & (MealPlan.planned_date == payload.planned_date)
                & (MealPlan.meal_slot == payload.meal_slot)
            )
        )
    else:
        existing = await db.execute(
            select(MealPlan).where(
                (MealPlan.cookbook_id.is_(None))
                & (MealPlan.user_id == current_user.id)
                & (MealPlan.planned_date == payload.planned_date)
                & (MealPlan.meal_slot == payload.meal_slot)
            )
        )

    existing_plan = existing.scalar_one_or_none()
    if existing_plan:
        raise HTTPException(
            status_code=409,
            detail="Un repas est deja planifie sur ce slot",
        )

    mp = MealPlan(
        user_id=current_user.id,
        cookbook_id=payload.cookbook_id,
        recipe_id=payload.recipe_id,
        planned_date=payload.planned_date,
        meal_slot=payload.meal_slot,
        servings=payload.servings,
    )
    db.add(mp)
    await db.commit()
    await db.refresh(mp)
    return MealPlanRead.model_validate(mp)


@router.get("", response_model=list[MealPlanRead])
async def list_my_meal_plans(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    cookbook_id: int | None = Query(None),
) -> list[MealPlanRead]:
    if cookbook_id is not None:
        role = await _get_member_role(db, cookbook_id, current_user.id)
        if role is None:
            raise HTTPException(status_code=403, detail="Vous n'etes pas membre de ce cookbook")
        stmt = select(MealPlan).where(MealPlan.cookbook_id == cookbook_id)
    else:
        stmt = select(MealPlan).where(
            (MealPlan.user_id == current_user.id) & (MealPlan.cookbook_id.is_(None))
        )

    if start_date:
        stmt = stmt.where(MealPlan.planned_date >= start_date)
    if end_date:
        stmt = stmt.where(MealPlan.planned_date <= end_date)
    stmt = stmt.order_by(MealPlan.planned_date)
    result = await db.execute(stmt)
    return [MealPlanRead.model_validate(mp) for mp in result.scalars().all()]


@router.delete("/{plan_id}", status_code=204)
async def delete_meal_plan(
    plan_id: int, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> None:
    result = await db.execute(select(MealPlan).where(MealPlan.id == plan_id))
    mp = result.scalar_one_or_none()
    if not mp:
        raise HTTPException(status_code=404, detail="Plan introuvable")

    if mp.cookbook_id is None:
        if mp.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission insuffisante")
    else:
        role = await _get_member_role(db, mp.cookbook_id, current_user.id)
        if role is None or role == CookbookRole.READER:
            raise HTTPException(status_code=403, detail="Permission insuffisante")

    await db.delete(mp)
    await db.commit()
