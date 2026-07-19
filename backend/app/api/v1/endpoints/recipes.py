"""Endpoints Recettes : CRUD, filtres, recherche, favoris, image."""

import os
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security_utils import safe_image_extension, sniff_image
from app.core.deps import CurrentUser, get_db, _get_optional_user
from app.models.cookbook import CookbookMember, CookbookRole
from app.models.user import User
from app.models.recipe import (
    Comment,
    Recipe,
    RecipeFavorite,
    RecipeIngredient,
    RecipeStep,
    RecipeTag,
    Tag,
)
from app.schemas.recipe import (
    CommentCreate,
    CommentRead,
    RecipeCreate,
    RecipeRead,
    RecipeSummary,
    RecipeUpdate,
)

router = APIRouter()
settings = get_settings()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


# ---------- Helpers de permission ----------

async def _cookbook_role(
    db: AsyncSession, cookbook_id: int, user_id: int
) -> CookbookRole | None:
    """Renvoie le role de l'user dans le cookbook, ou None s'il n'est pas membre."""
    result = await db.execute(
        select(CookbookMember).where(
            (CookbookMember.cookbook_id == cookbook_id) & (CookbookMember.user_id == user_id)
        )
    )
    m = result.scalar_one_or_none()
    return m.role if m else None


async def _can_view(recipe: Recipe, user_id: int | None, db: AsyncSession) -> bool:
    if recipe.is_public:
        return True
    if user_id is None:
        return False
    if recipe.owner_id == user_id:
        return True
    if recipe.cookbook_id:
        return await _cookbook_role(db, recipe.cookbook_id, user_id) is not None
    return False


async def _can_edit(recipe: Recipe, user_id: int, db: AsyncSession) -> bool:
    if recipe.owner_id == user_id:
        return True
    if recipe.cookbook_id:
        role = await _cookbook_role(db, recipe.cookbook_id, user_id)
        if role in (CookbookRole.CREATOR, CookbookRole.EDITOR):
            return True
    return False


# ---------- Helpers de transformation ----------

def _recipe_to_read(recipe: Recipe) -> RecipeRead:
    data = RecipeRead.model_validate(recipe).model_dump()
    data["is_favorite"] = bool(getattr(recipe, "_is_favorite", False))
    return RecipeRead.model_validate(data)


def _recipe_to_summary(recipe: Recipe) -> RecipeSummary:
    data = RecipeSummary.model_validate(recipe).model_dump()
    data["is_favorite"] = bool(getattr(recipe, "_is_favorite", False))
    return RecipeSummary.model_validate(data)


async def _favorite_recipe_ids(db: AsyncSession, user_id: int, recipe_ids: list[int]) -> set[int]:
    if not recipe_ids:
        return set()
    result = await db.execute(
        select(RecipeFavorite.recipe_id).where(
            (RecipeFavorite.user_id == user_id) & (RecipeFavorite.recipe_id.in_(recipe_ids))
        )
    )
    return set(result.scalars().all())


async def _build_search_vector(recipe_id: int, db: AsyncSession) -> None:
    """Reconstruit le tsvector d'une recette (utilise par trigger ou a la main)."""
    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.steps),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        return
    parts = [
        recipe.title or "",
        recipe.description or "",
        recipe.cuisine_type or "",
        recipe.difficulty or "",
    ]
    parts.extend(i.name for i in recipe.ingredients)
    parts.extend(s.content for s in recipe.steps)
    parts.extend(t.name for t in recipe.tags)
    full_text = " ".join(parts)
    await db.execute(
        text("UPDATE recipes SET search_vector = to_tsvector('french', :txt) WHERE id = :rid"),
        {"txt": full_text, "rid": recipe_id},
    )


# ---------- Endpoints CRUD ----------

@router.post("", response_model=RecipeRead, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    payload: RecipeCreate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> RecipeRead:
    # Si cookbook_id fourni, verifier les droits (editeur/creator)
    tag_ids: list[int] = getattr(payload, "tag_ids", []) or []

    # Validation du cookbook cible
    cookbook_id = getattr(payload, "cookbook_id", None)
    if cookbook_id is not None:
        role = await _cookbook_role(db, cookbook_id, current_user.id)
        if role is None:
            raise HTTPException(status_code=403, detail="Vous n etes pas membre de ce cookbook")
        if role not in (CookbookRole.CREATOR, CookbookRole.EDITOR):
            raise HTTPException(status_code=403, detail="Permission insuffisante")
    recipe = Recipe(
        title=payload.title,
        description=payload.description,
        source_url=payload.source_url,
        prep_time_minutes=payload.prep_time_minutes,
        cook_time_minutes=payload.cook_time_minutes,
        servings=payload.servings,
        difficulty=payload.difficulty,
        cuisine_type=payload.cuisine_type,
        image_url=payload.image_url,
        is_favorite=False,
        is_public=payload.is_public,
        owner_id=current_user.id,
        cookbook_id=cookbook_id,
    )
    db.add(recipe)
    await db.flush()

    # Ingredients
    for ing in payload.ingredients:
        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                name=ing.name,
                quantity=ing.quantity,
                unit=ing.unit,
                note=ing.note,
                position=ing.position,
            )
        )
    # Etapes
    for step in payload.steps:
        db.add(
            RecipeStep(
                recipe_id=recipe.id, content=step.content, position=step.position
            )
        )
    # Tags
    if tag_ids:
        result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        for tag in result.scalars().all():
            db.add(RecipeTag(recipe_id=recipe.id, tag_id=tag.id))

    await db.commit()
    await _build_search_vector(recipe.id, db)
    await db.commit()

    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.steps),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe.id)
    )
    recipe_out = result.scalar_one()
    setattr(recipe_out, "_is_favorite", False)
    return _recipe_to_read(recipe_out)


@router.get("", response_model=list[RecipeSummary])
async def list_recipes(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(_get_optional_user),
    cookbook_id: int | None = None,
    tag_ids: Annotated[list[int] | None, Query()] = None,
    tag_category: str | None = None,
    ingredient: str | None = None,
    max_prep_time: int | None = None,
    max_cook_time: int | None = None,
    favorites_only: bool = False,
    search: str | None = None,
    skip: int = Query(0, ge=0, le=10000),
    limit: int = Query(20, ge=1, le=100),
) -> list[RecipeSummary]:
    """Liste paginee + filtres + recherche plein texte (PostgreSQL FTS)."""
    stmt = select(Recipe).options(selectinload(Recipe.tags))

    conditions = []

    # Visibilite : recettes personnelles, publiques, ou dans un cookbook dont je suis membre
    # is_public uniquement si owner present (anti recette orpheline)
    visibility_clauses = [and_(Recipe.is_public.is_(True), Recipe.owner_id.is_not(None))]
    if current_user:
        visibility_clauses.append(Recipe.owner_id == current_user.id)
        # cookbooks dont je suis membre
        member_cb_subq = select(CookbookMember.cookbook_id).where(
            CookbookMember.user_id == current_user.id
        )
        visibility_clauses.append(Recipe.cookbook_id.in_(member_cb_subq))
    conditions.append(or_(*visibility_clauses))

    if cookbook_id is not None:
        conditions.append(Recipe.cookbook_id == cookbook_id)

    if max_prep_time is not None:
        conditions.append(Recipe.prep_time_minutes <= max_prep_time)
    if max_cook_time is not None:
        conditions.append(Recipe.cook_time_minutes <= max_cook_time)

    if ingredient:
        # Utilise trigram pour recherche floue + insensible a la casse
        ingredient_subq = (
            select(RecipeIngredient.recipe_id)
            .where(RecipeIngredient.name.ilike(f"%{ingredient}%"))
            .distinct()
        )
        conditions.append(Recipe.id.in_(ingredient_subq))

    if tag_ids:
        for tid in tag_ids:
            tag_subq = select(RecipeTag.recipe_id).where(RecipeTag.tag_id == tid)
            conditions.append(Recipe.id.in_(tag_subq))

    if tag_category:
        category_subq = (
            select(RecipeTag.recipe_id)
            .join(Tag, Tag.id == RecipeTag.tag_id)
            .where(Tag.category == tag_category)
        )
        conditions.append(Recipe.id.in_(category_subq))

    if search:
        # Recherche plein texte + trigram en fallback
        ts_query = func.websearch_to_tsquery("french", search)
        conditions.append(
            or_(
                Recipe.search_vector.op("@@")(ts_query),
                Recipe.title.ilike(f"%{search}%"),
            )
        )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.order_by(Recipe.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    recipes = result.scalars().unique().all()
    favorite_ids: set[int] = set()
    if current_user:
        favorite_ids = await _favorite_recipe_ids(db, current_user.id, [r.id for r in recipes])
    if favorites_only:
        recipes = [r for r in recipes if r.id in favorite_ids]
    for r in recipes:
        setattr(r, "_is_favorite", r.id in favorite_ids)
    return [_recipe_to_summary(r) for r in recipes]


@router.get("/{recipe_id}", response_model=RecipeRead)
async def get_recipe(
    recipe_id: int, db: AsyncSession = Depends(get_db), current_user: Optional[User] = Depends(_get_optional_user)
) -> RecipeRead:
    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.steps),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    if not await _can_view(recipe, current_user.id if current_user else None, db):
        raise HTTPException(status_code=403, detail="Acces refuse")
    if current_user:
        fav_result = await db.execute(
            select(RecipeFavorite).where(
                (RecipeFavorite.user_id == current_user.id) & (RecipeFavorite.recipe_id == recipe.id)
            )
        )
        setattr(recipe, "_is_favorite", fav_result.scalar_one_or_none() is not None)
    else:
        setattr(recipe, "_is_favorite", False)
    return _recipe_to_read(recipe)


@router.patch("/{recipe_id}", response_model=RecipeRead)
async def update_recipe(
    recipe_id: int,
    payload: RecipeUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> RecipeRead:
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    if not await _can_edit(recipe, current_user.id, db):
        raise HTTPException(status_code=403, detail="Permission insuffisante")

    data = payload.model_dump(exclude_unset=True)
    ingredients = data.pop("ingredients", None)
    steps = data.pop("steps", None)
    tag_ids = data.pop("tag_ids", None)
    data.pop("is_favorite", None)

    for key, value in data.items():
        setattr(recipe, key, value)

    if ingredients is not None:
        # Remplacer
        for old in list(recipe.ingredients):
            await db.delete(old)
        for ing in ingredients:
            db.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    name=ing["name"],
                    quantity=ing.get("quantity"),
                    unit=ing.get("unit"),
                    note=ing.get("note"),
                    position=ing.get("position", 0),
                )
            )

    if steps is not None:
        for old in list(recipe.steps):
            await db.delete(old)
        for s in steps:
            db.add(
                RecipeStep(recipe_id=recipe.id, content=s["content"], position=s.get("position", 0))
            )

    if tag_ids is not None:
        await db.execute(RecipeTag.__table__.delete().where(RecipeTag.recipe_id == recipe.id))
        for tid in tag_ids:
            db.add(RecipeTag(recipe_id=recipe.id, tag_id=tid))

    await db.commit()
    await _build_search_vector(recipe.id, db)
    await db.commit()

    result = await db.execute(
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.steps),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
    )
    recipe_out = result.scalar_one()
    fav_result = await db.execute(
        select(RecipeFavorite).where(
            (RecipeFavorite.user_id == current_user.id) & (RecipeFavorite.recipe_id == recipe_out.id)
        )
    )
    setattr(recipe_out, "_is_favorite", fav_result.scalar_one_or_none() is not None)
    return _recipe_to_read(recipe_out)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: int, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> None:
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    if not await _can_edit(recipe, current_user.id, db):
        raise HTTPException(status_code=403, detail="Permission insuffisante")
    await db.delete(recipe)
    await db.commit()


@router.post("/{recipe_id}/favorite", response_model=RecipeRead)
async def toggle_favorite(
    recipe_id: int, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> RecipeRead:
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    if not await _can_view(recipe, current_user.id, db):
        raise HTTPException(status_code=403, detail="Acces refuse")

    existing_result = await db.execute(
        select(RecipeFavorite).where(
            (RecipeFavorite.user_id == current_user.id) & (RecipeFavorite.recipe_id == recipe.id)
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        setattr(recipe, "_is_favorite", False)
    else:
        db.add(RecipeFavorite(user_id=current_user.id, recipe_id=recipe.id))
        setattr(recipe, "_is_favorite", True)

    await db.commit()
    await db.refresh(recipe)
    return _recipe_to_read(recipe)


@router.post("/{recipe_id}/image", response_model=RecipeRead)
async def upload_recipe_image(
    recipe_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> RecipeRead:
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    if not await _can_edit(recipe, current_user.id, db):
        raise HTTPException(status_code=403, detail="Permission insuffisante")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Format non supporte")

    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux")

    # Validation par magic bytes (defense en profondeur contre SVG, PHP, scripts)
    sniffed = sniff_image(content)
    if sniffed is None:
        raise HTTPException(
            status_code=400,
            detail="Contenu invalide: seuls JPEG, PNG, GIF, WebP sont acceptes",
        )
    ext = safe_image_extension(os.path.splitext(file.filename or "")[1], sniffed)

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"recipe_{recipe.id}_{uuid.uuid4().hex}{ext}"
    filepath = upload_dir / filename
    filepath.write_bytes(content)

    # Supprimer ancienne image
    if recipe.image_url and recipe.image_url.startswith("/uploads/"):
        old = upload_dir / Path(recipe.image_url).name
        if old.exists() and old.is_file():
            old.unlink()

    recipe.image_url = f"/uploads/{filename}"
    await db.commit()
    await db.refresh(recipe)
    return _recipe_to_read(recipe)


# ---------- Commentaires ----------

@router.post("/{recipe_id}/comments", response_model=CommentRead, status_code=201)
async def add_comment(
    recipe_id: int,
    payload: CommentCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CommentRead:
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    if not await _can_view(recipe, current_user.id, db):
        raise HTTPException(status_code=403, detail="Acces refuse")
    # Lecture seule ne peut pas commenter ; check role
    if recipe.cookbook_id:
        role = await _cookbook_role(db, recipe.cookbook_id, current_user.id)
        if role == CookbookRole.READER:
            raise HTTPException(status_code=403, detail="Permission insuffisante pour commenter")

    comment = Comment(recipe_id=recipe_id, author_id=current_user.id, content=payload.content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return CommentRead.model_validate(comment)


@router.get("/{recipe_id}/comments", response_model=list[CommentRead])
async def list_comments(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(_get_optional_user),
) -> list[CommentRead]:
    recipe_result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = recipe_result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    if not await _can_view(recipe, current_user.id if current_user else None, db):
        raise HTTPException(status_code=403, detail="Acces refuse")

    result = await db.execute(
        select(Comment).where(Comment.recipe_id == recipe_id).order_by(Comment.created_at)
    )
    return [CommentRead.model_validate(c) for c in result.scalars().all()]


@router.delete("/{recipe_id}/comments/{comment_id}", status_code=204)
async def delete_comment(
    recipe_id: int,
    comment_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Comment).where((Comment.id == comment_id) & (Comment.recipe_id == recipe_id))
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Commentaire introuvable")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission insuffisante")
    await db.delete(comment)
    await db.commit()
