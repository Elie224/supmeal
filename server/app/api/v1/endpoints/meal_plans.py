"""Endpoints Meal Plans accessibles depuis /api/v1/meal-plans."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models.cookbook import CookbookMember, CookbookRole
from app.models.recipe import MealPlan, Recipe
from app.schemas.recipe import MealPlanCreate, MealPlanRead

router = APIRouter()


@router.post("", response_model=MealPlanRead, status_code=201)
async def create_meal_plan(
    payload: MealPlanCreate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> MealPlanRead:
    result = await db.execute(select(Recipe).where(Recipe.id == payload.recipe_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Recette introuvable")
    mp = MealPlan(
        user_id=current_user.id,
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
) -> list[MealPlanRead]:
    stmt = select(MealPlan).where(MealPlan.user_id == current_user.id)
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
    result = await db.execute(
        select(MealPlan).where(
            (MealPlan.id == plan_id) & (MealPlan.user_id == current_user.id)
        )
    )
    mp = result.scalar_one_or_none()
    if not mp:
        raise HTTPException(status_code=404, detail="Plan introuvable")
    await db.delete(mp)
    await db.commit()