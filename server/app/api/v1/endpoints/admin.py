"""Endpoints admin : stats globales, gestion des utilisateurs, moderation des recettes.

Proteges par le role UserRole.ADMIN (defini dans app.models.user).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models.cookbook import Cookbook
from app.models.recipe import Comment, MealPlan, Recipe
from app.models.user import User, UserRole

router = APIRouter()


async def require_admin(current_user: CurrentUser) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces reserve aux administrateurs",
        )
    return current_user


AdminUser = Depends(require_admin)


# ---------- Vue d ensemble / stats ----------


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db), _: User = AdminUser
) -> dict:
    """Statistiques globales de l application (admin uniquement)."""
    now = datetime.now(timezone.utc)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)

    users_total = (await db.execute(select(func.count(User.id)))).scalar_one()
    users_active = (
        await db.execute(
            select(func.count(User.id)).where(User.is_active.is_(True))
        )
    ).scalar_one()
    users_verified = (
        await db.execute(
            select(func.count(User.id)).where(User.is_verified.is_(True))
        )
    ).scalar_one()
    users_new_7d = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at >= last_7d)
        )
    ).scalar_one()
    users_new_30d = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at >= last_30d)
        )
    ).scalar_one()

    recipes_total = (await db.execute(select(func.count(Recipe.id)))).scalar_one()
    recipes_public = (
        await db.execute(
            select(func.count(Recipe.id)).where(Recipe.is_public.is_(True))
        )
    ).scalar_one()

    cookbooks_total = (
        await db.execute(select(func.count(Cookbook.id)))
    ).scalar_one()
    comments_total = (
        await db.execute(select(func.count(Comment.id)))
    ).scalar_one()
    meal_plans_total = (
        await db.execute(select(func.count(MealPlan.id)))
    ).scalar_one()

    provider_rows = (
        await db.execute(
            select(User.auth_provider, func.count(User.id)).group_by(
                User.auth_provider
            )
        )
    ).all()
    auth_providers = {p.value: count for p, count in provider_rows}

    return {
        "generated_at": now.isoformat(),
        "users": {
            "total": users_total,
            "active": users_active,
            "verified": users_verified,
            "new_last_7d": users_new_7d,
            "new_last_30d": users_new_30d,
            "by_provider": auth_providers,
        },
        "recipes": {"total": recipes_total, "public": recipes_public},
        "cookbooks": {"total": cookbooks_total},
        "comments": {"total": comments_total},
        "meal_plans": {"total": meal_plans_total},
    }


# ---------- Gestion des utilisateurs ----------


class AdminUserRead(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email: str
    role: UserRole
    auth_provider: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    recipe_count: int = 0
    cookbook_count: int = 0

    model_config = ConfigDict(from_attributes=True)


@router.get("/users", response_model=list[AdminUserRead])
async def list_all_users(
    db: AsyncSession = Depends(get_db),
    _: User = AdminUser,
    q: Optional[str] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0, le=10000),
    limit: int = Query(50, ge=1, le=200),
) -> list[AdminUserRead]:
    """Liste tous les utilisateurs avec filtres et pagination."""
    stmt = select(User).order_by(User.created_at.desc())
    if q:
        like = f"%{q[:60]}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.username.ilike(like)))
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    user_ids = [u.id for u in users]
    recipe_counts: dict = {}
    cookbook_counts: dict = {}
    if user_ids:
        rr = await db.execute(
            select(Recipe.owner_id, func.count(Recipe.id))
            .where(Recipe.owner_id.in_(user_ids))
            .group_by(Recipe.owner_id)
        )
        recipe_counts = dict(rr.all())
        cr = await db.execute(
            select(Cookbook.owner_id, func.count(Cookbook.id))
            .where(Cookbook.owner_id.in_(user_ids))
            .group_by(Cookbook.owner_id)
        )
        cookbook_counts = dict(cr.all())

    out: list[AdminUserRead] = []
    for u in users:
        out.append(AdminUserRead(
            id=u.id,
            username=u.username,
            full_name=u.full_name,
            avatar_url=u.avatar_url,
            email=u.email,
            role=u.role,
            auth_provider=(u.auth_provider.value if hasattr(u.auth_provider, "value") else str(u.auth_provider)),
            is_active=u.is_active,
            is_verified=u.is_verified,
            created_at=u.created_at,
            recipe_count=recipe_counts.get(u.id, 0),
            cookbook_count=cookbook_counts.get(u.id, 0),
        ))
    return out


class RoleUpdate(BaseModel):
    role: UserRole


@router.patch("/users/{user_id}/role", response_model=AdminUserRead)
async def update_user_role(
    user_id: int,
    payload: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = AdminUser,
) -> AdminUserRead:
    if user_id == admin.id and payload.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas vous retirer le role admin vous-meme",
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.role = payload.role
    await db.commit()
    await db.refresh(user)
    return AdminUserRead(
        id=user.id, username=user.username, full_name=user.full_name,
        avatar_url=user.avatar_url, email=user.email, role=user.role,
        auth_provider=(user.auth_provider.value if hasattr(user.auth_provider, "value") else str(user.auth_provider)),
        is_active=user.is_active, is_verified=user.is_verified, created_at=user.created_at,
    )


class ActiveUpdate(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}/active", response_model=AdminUserRead)
async def toggle_user_active(
    user_id: int,
    payload: ActiveUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = AdminUser,
) -> AdminUserRead:
    if user_id == admin.id and not payload.is_active:
        raise HTTPException(
            status_code=400, detail="Vous ne pouvez pas vous desactiver vous-meme"
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return AdminUserRead(
        id=user.id, username=user.username, full_name=user.full_name,
        avatar_url=user.avatar_url, email=user.email, role=user.role,
        auth_provider=(user.auth_provider.value if hasattr(user.auth_provider, "value") else str(user.auth_provider)),
        is_active=user.is_active, is_verified=user.is_verified, created_at=user.created_at,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = AdminUser,
) -> None:
    if user_id == admin.id:
        raise HTTPException(
            status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte"
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    await db.delete(user)
    await db.commit()


# ---------- Moderation des recettes ----------


class AdminRecipeSummary(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    owner_id: Optional[int] = None
    owner_username: Optional[str] = None
    cookbook_id: Optional[int] = None
    is_public: bool
    is_favorite: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/recipes", response_model=list[AdminRecipeSummary])
async def list_all_recipes(
    db: AsyncSession = Depends(get_db),
    _: User = AdminUser,
    q: Optional[str] = None,
    owner_id: Optional[int] = None,
    is_public: Optional[bool] = None,
    skip: int = Query(0, ge=0, le=10000),
    limit: int = Query(50, ge=1, le=200),
) -> list[AdminRecipeSummary]:
    """Liste toutes les recettes (toutes visibilites confondues)."""
    stmt = select(Recipe).order_by(Recipe.created_at.desc())
    if q:
        like = f"%{q[:60]}%"
        stmt = stmt.where(Recipe.title.ilike(like))
    if owner_id is not None:
        stmt = stmt.where(Recipe.owner_id == owner_id)
    if is_public is not None:
        stmt = stmt.where(Recipe.is_public == is_public)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    recipes = result.scalars().all()

    owner_ids = {r.owner_id for r in recipes if r.owner_id is not None}
    owners: dict = {}
    if owner_ids:
        ur = await db.execute(select(User).where(User.id.in_(owner_ids)))
        owners = {u.id: u.username for u in ur.scalars().all()}

    return [
        AdminRecipeSummary(
            id=r.id,
            title=r.title,
            description=r.description,
            image_url=r.image_url,
            owner_id=r.owner_id,
            owner_username=owners.get(r.owner_id) if r.owner_id else None,
            cookbook_id=r.cookbook_id,
            is_public=r.is_public,
            is_favorite=r.is_favorite,
            created_at=r.created_at,
        )
        for r in recipes
    ]


@router.delete("/recipes/{recipe_id}", status_code=204)
async def admin_delete_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = AdminUser,
) -> None:
    """Supprimer une recette (moderation, admin uniquement)."""
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    # Nettoyer l image si elle existe
    if recipe.image_url and recipe.image_url.startswith("/uploads/"):
        from pathlib import Path
        try:
            old = Path(recipe.image_url.lstrip("/"))
            if old.exists() and old.is_file():
                old.unlink()
        except OSError:
            pass
    await db.delete(recipe)
    await db.commit()
