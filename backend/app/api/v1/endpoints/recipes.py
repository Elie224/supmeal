"""Endpoints Recettes : CRUD, filtres, recherche, favoris, image."""

import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.deps import CurrentUser, _get_optional_user, get_db
from app.core.security_utils import safe_image_extension, sniff_image
from app.models.cookbook import CookbookMember, CookbookRole
from app.models.recipe import (
    Comment,
    Recipe,
    RecipeFavorite,
    RecipeIngredient,
    RecipeTag,
    Tag,
)
from app.models.user import User
from app.schemas.recipe import (
    CommentCreate,
    CommentRead,
    RecipeCreate,
    RecipeRead,
    RecipeSuggestion,
    RecipeSuggestRequest,
    RecipeSummary,
    RecipeUpdate,
)
from app.services.recipe_service import create_recipe as svc_create_recipe
from app.services.recipe_service import update_recipe as svc_update_recipe

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
    recipe = await svc_create_recipe(
        db,
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        source_url=payload.source_url,
        prep_time_minutes=payload.prep_time_minutes,
        cook_time_minutes=payload.cook_time_minutes,
        servings=payload.servings,
        difficulty=payload.difficulty,
        cuisine_type=payload.cuisine_type,
        image_url=payload.image_url,
        is_public=payload.is_public,
        cookbook_id=cookbook_id,
        ingredients=[ing.model_dump() for ing in payload.ingredients],
        steps=[step.model_dump() for step in payload.steps],
        tag_ids=tag_ids,
    )
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
    recipe_out._is_favorite = False
    return _recipe_to_read(recipe_out)


@router.get("", response_model=list[RecipeSummary])
async def list_recipes(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(_get_optional_user),
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
        # Recherche ingredient insensible a la casse
        ingredient_subq = (
            select(RecipeIngredient.recipe_id)
            .where(RecipeIngredient.name.ilike(f"%{ingredient}%"))
            .distinct()
        )
        conditions.append(Recipe.id.in_(ingredient_subq))

    if favorites_only:
        if not current_user:
            return []
        stmt = stmt.join(
            RecipeFavorite,
            and_(
                RecipeFavorite.recipe_id == Recipe.id,
                RecipeFavorite.user_id == current_user.id,
            ),
        )

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
        if favorites_only:
            favorite_ids = {r.id for r in recipes}
        else:
            favorite_ids = await _favorite_recipe_ids(db, current_user.id, [r.id for r in recipes])
    for r in recipes:
        r._is_favorite = r.id in favorite_ids
    return [_recipe_to_summary(r) for r in recipes]


@router.get("/{recipe_id}", response_model=RecipeRead)
async def get_recipe(
    recipe_id: int, db: AsyncSession = Depends(get_db), current_user: User | None = Depends(_get_optional_user)
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
        recipe._is_favorite = fav_result.scalar_one_or_none() is not None
    else:
        recipe._is_favorite = False
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

    await svc_update_recipe(
        db,
        recipe=recipe,
        fields=data,
        ingredients=ingredients,
        steps=steps,
        tag_ids=tag_ids,
    )
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
    recipe_out._is_favorite = fav_result.scalar_one_or_none() is not None
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
        recipe._is_favorite = False
    else:
        db.add(RecipeFavorite(user_id=current_user.id, recipe_id=recipe.id))
        recipe._is_favorite = True

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
    current_user: User | None = Depends(_get_optional_user),
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


# ---------- Suggestions de recettes ----------

import unicodedata as _unicodedata


def _normalize_text(value: str) -> str:
    """Normalise pour la comparaison d ingredients : minuscules + suppression des accents."""
    if not value:
        return ""
    nfkd = _unicodedata.normalize("NFKD", value)
    return "".join(c for c in nfkd if not _unicodedata.combining(c)).lower().strip()


@router.post("/suggest", response_model=list[RecipeSuggestion])
async def suggest_recipes(
    payload: RecipeSuggestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(_get_optional_user),
) -> list[RecipeSuggestion]:
    """Suggere des recettes realisables a partir d une liste d ingredients disponibles.

    Algorithme :
      1. Normalisation (lowercase + strip accents) des ingredients saisis.
      2. Pre-filtre SQL : recettes ayant au moins un ingredient qui matche (ILIKE
         insensible a la casse + `unaccent` cote PostgreSQL).
      3. Filtres optionnels : tags, temps max, cookbook.
      4. Score final = matched / total_ingredients ; tri par score desc, puis
         nombre d ingredients manquants croissant, puis duree totale croissante.
    """
    have = [_normalize_text(ing) for ing in payload.ingredients]
    have = [h for h in have if h]
    if not have:
        return []

    stmt = (
        select(Recipe)
        .options(selectinload(Recipe.ingredients), selectinload(Recipe.tags))
    )

    # Visibilite : memes regles que list_recipes
    visibility_clauses = [and_(Recipe.is_public.is_(True), Recipe.owner_id.is_not(None))]
    if current_user:
        visibility_clauses.append(Recipe.owner_id == current_user.id)
        member_cb_subq = select(CookbookMember.cookbook_id).where(
            CookbookMember.user_id == current_user.id
        )
        visibility_clauses.append(Recipe.cookbook_id.in_(member_cb_subq))
    stmt = stmt.where(or_(*visibility_clauses))

    if payload.cookbook_id is not None:
        stmt = stmt.where(Recipe.cookbook_id == payload.cookbook_id)
    if payload.max_prep_time is not None:
        stmt = stmt.where(Recipe.prep_time_minutes <= payload.max_prep_time)
    if payload.max_cook_time is not None:
        stmt = stmt.where(Recipe.cook_time_minutes <= payload.max_cook_time)
    if payload.tag_ids:
        for tid in payload.tag_ids:
            tag_subq = select(RecipeTag.recipe_id).where(RecipeTag.tag_id == tid)
            stmt = stmt.where(Recipe.id.in_(tag_subq))

    # Pre-filtre SQL : au moins un ingredient matche (ILIKE sur le nom normalise).
    # On tente d utiliser `unaccent` cote PG ; il est protege par un fallback ILIKE simple.
    try:
        like_clauses = [
            func.unaccent(RecipeIngredient.name).ilike(f"%{h}%") for h in have
        ]
        ingredient_match_subq = (
            select(RecipeIngredient.recipe_id)
            .where(or_(*like_clauses))
            .distinct()
        )
    except Exception:
        ingredient_match_subq = (
            select(RecipeIngredient.recipe_id)
            .where(or_(*[RecipeIngredient.name.ilike(f"%{h}%") for h in have]))
            .distinct()
        )
    stmt = stmt.where(Recipe.id.in_(ingredient_match_subq))

    recipes = (await db.execute(stmt)).scalars().unique().all()
    if not recipes:
        return []

    suggestions: list[RecipeSuggestion] = []
    for recipe in recipes:
        ing_names = [i.name for i in recipe.ingredients if i.name]
        if not ing_names:
            continue
        matched: list[str] = []
        missing: list[str] = []
        for name in ing_names:
            norm = _normalize_text(name)
            hit = any(h and (h in norm or norm in h) for h in have)
            (matched if hit else missing).append(name)
        if not matched:
            continue
        total = len(matched) + len(missing)
        score = len(matched) / total if total else 0.0
        suggestion = RecipeSuggestion(
            recipe=_recipe_to_summary(recipe),
            match_score=round(score, 3),
            matched_ingredients=matched,
            missing_ingredients=missing,
        )
        suggestions.append(suggestion)

    suggestions.sort(
        key=lambda s: (
            -s.match_score,
            len(s.missing_ingredients),
            s.recipe.prep_time_minutes + s.recipe.cook_time_minutes,
            s.recipe.title.lower(),
        )
    )
    return suggestions[: payload.limit]

