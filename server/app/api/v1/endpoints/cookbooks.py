"""Endpoints Cookbook : CRUD, membres, recettes du cookbook, messagerie."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, get_db
from app.models.cookbook import (
    Cookbook,
    CookbookMember,
    CookbookMessage,
    CookbookRole,
)
from app.models.recipe import Recipe
from app.models.recipe import RecipeIngredient, RecipeStep
from app.models.user import User
from app.schemas.cookbook import (
    AddMemberRequest,
    CookbookCreate,
    CookbookMessageCreate,
    CookbookMessageRead,
    CookbookRead,
    CookbookSummary,
    CookbookUpdate,
    UpdateMemberRoleRequest,
)
from app.schemas.recipe import RecipeCreate, RecipeRead
from app.schemas.user import UserPublic
from app.services.connection_manager import manager

router = APIRouter()


# ---------- Cookbook CRUD ----------

@router.post("", response_model=CookbookRead, status_code=status.HTTP_201_CREATED)
async def create_cookbook(
    payload: CookbookCreate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> CookbookRead:
    cookbook = Cookbook(
        name=payload.name,
        description=payload.description,
        image_url=payload.image_url,
        owner_id=current_user.id,
    )
    db.add(cookbook)
    await db.flush()
    # Le createur est automatiquement membre avec le role CREATOR
    db.add(
        CookbookMember(cookbook_id=cookbook.id, user_id=current_user.id, role=CookbookRole.CREATOR)
    )
    await db.commit()
    await db.refresh(cookbook)
    result = await db.execute(
        select(Cookbook)
        .options(selectinload(Cookbook.members).selectinload(CookbookMember.user))
        .where(Cookbook.id == cookbook.id)
    )
    return CookbookRead.model_validate(result.scalar_one())


@router.get("", response_model=list[CookbookSummary])
async def list_my_cookbooks(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> list[CookbookSummary]:
    stmt = (
        select(Cookbook, CookbookMember.role)
        .join(CookbookMember, CookbookMember.cookbook_id == Cookbook.id)
        .where(CookbookMember.user_id == current_user.id)
        .order_by(Cookbook.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    summaries: list[CookbookSummary] = []
    for cookbook, role in rows:
        # Compter membres et recettes
        members_count = await db.execute(
            select(CookbookMember).where(CookbookMember.cookbook_id == cookbook.id)
        )
        recipes_count = await db.execute(
            select(Recipe).where(Recipe.cookbook_id == cookbook.id)
        )
        summaries.append(
            CookbookSummary(
                id=cookbook.id,
                name=cookbook.name,
                description=cookbook.description,
                image_url=cookbook.image_url,
                owner_id=cookbook.owner_id,
                member_count=len(members_count.scalars().all()),
                recipe_count=len(recipes_count.scalars().all()),
                my_role=role,
                created_at=cookbook.created_at,
            )
        )
    return summaries


@router.get("/{cookbook_id}", response_model=CookbookRead)
async def get_cookbook(
    cookbook_id: int, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> CookbookRead:
    # Verifier que l'utilisateur est membre
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role is None:
        raise HTTPException(status_code=403, detail="Vous n'etes pas membre de ce cookbook")
    result = await db.execute(
        select(Cookbook)
        .options(selectinload(Cookbook.members).selectinload(CookbookMember.user))
        .where(Cookbook.id == cookbook_id)
    )
    cookbook = result.scalar_one_or_none()
    if not cookbook:
        raise HTTPException(status_code=404, detail="Cookbook introuvable")
    return CookbookRead.model_validate(cookbook)


@router.patch("/{cookbook_id}", response_model=CookbookRead)
async def update_cookbook(
    cookbook_id: int,
    payload: CookbookUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CookbookRead:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role != CookbookRole.CREATOR:
        raise HTTPException(status_code=403, detail="Reserve au createur")
    result = await db.execute(select(Cookbook).where(Cookbook.id == cookbook_id))
    cookbook = result.scalar_one_or_none()
    if not cookbook:
        raise COOKBOOK_NOT_FOUND
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(cookbook, key, value)
    await db.commit()
    await db.refresh(cookbook)
    return CookbookRead.model_validate(cookbook)


@router.delete("/{cookbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cookbook(
    cookbook_id: int, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> None:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role != CookbookRole.CREATOR:
        raise HTTPException(status_code=403, detail="Reserve au createur")
    result = await db.execute(select(Cookbook).where(Cookbook.id == cookbook_id))
    cookbook = result.scalar_one_or_none()
    if not cookbook:
        raise HTTPException(status_code=404, detail="Cookbook introuvable")
    await db.delete(cookbook)
    await db.commit()


# ---------- Membres ----------

@router.post("/{cookbook_id}/members", status_code=201)
async def add_member(
    cookbook_id: int,
    payload: AddMemberRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role not in (CookbookRole.CREATOR,):
        raise HTTPException(status_code=403, detail="Reserve au createur")
    user_result = await db.execute(select(User).where(User.email == payload.user_email))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    existing = await _get_member_role(db, cookbook_id, user.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Deja membre")
    db.add(
        CookbookMember(cookbook_id=cookbook_id, user_id=user.id, role=payload.role)
    )
    await db.commit()
    return {"detail": "Membre ajoute"}


@router.patch("/{cookbook_id}/members/{user_id}", status_code=204)
async def update_member_role(
    cookbook_id: int,
    user_id: int,
    payload: UpdateMemberRoleRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role != CookbookRole.CREATOR:
        raise HTTPException(status_code=403, detail="Reserve au createur")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Impossible de modifier son propre role")
    result = await db.execute(
        select(CookbookMember).where(
            (CookbookMember.cookbook_id == cookbook_id) & (CookbookMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    member.role = payload.role
    await db.commit()


@router.delete("/{cookbook_id}/members/{user_id}", status_code=204)
async def remove_member(
    cookbook_id: int,
    user_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role != CookbookRole.CREATOR and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission insuffisante")
    result = await db.execute(
        select(CookbookMember).where(
            (CookbookMember.cookbook_id == cookbook_id) & (CookbookMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    if member.role == CookbookRole.CREATOR:
        raise HTTPException(status_code=400, detail="Impossible de retirer le createur")
    await db.delete(member)
    await db.commit()


# ---------- Recettes du cookbook ----------

@router.get("/{cookbook_id}/recipes", response_model=list[RecipeRead])
async def list_cookbook_recipes(
    cookbook_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    search: str | None = None,
    tag_ids: Annotated[list[int] | None, Query()] = None,
    tag_category: str | None = None,
    ingredient: str | None = None,
    max_prep_time: int | None = None,
    favorites_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> list[RecipeRead]:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role is None:
        raise HTTPException(status_code=403, detail="Vous n'etes pas membre de ce cookbook")

    stmt = (
        select(Recipe)
        .options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.steps),
            selectinload(Recipe.tags),
        )
        .where(Recipe.cookbook_id == cookbook_id)
    )
    if search:
        from sqlalchemy import func
        ts_query = func.to_tsquery("french", func.replace(func.lower(search), " ", " & "))
        stmt = stmt.where(
            or_(
                Recipe.search_vector.op("@@")(ts_query),
                Recipe.title.ilike(f"%{search}%"),
            )
        )
    if tag_ids:
        from app.models.recipe import RecipeTag
        for tid in tag_ids:
            subq = select(RecipeTag.recipe_id).where(RecipeTag.tag_id == tid)
            stmt = stmt.where(Recipe.id.in_(subq))
    if tag_category:
        from app.models.recipe import RecipeTag, Tag
        category_subq = (
            select(RecipeTag.recipe_id)
            .join(Tag, Tag.id == RecipeTag.tag_id)
            .where(Tag.category == tag_category)
        )
        stmt = stmt.where(Recipe.id.in_(category_subq))
    if ingredient:
        from app.models.recipe import RecipeIngredient
        ing_subq = select(RecipeIngredient.recipe_id).where(
            RecipeIngredient.name.ilike(f"%{ingredient}%")
        )
        stmt = stmt.where(Recipe.id.in_(ing_subq))
    if max_prep_time is not None:
        stmt = stmt.where(Recipe.prep_time_minutes <= max_prep_time)
    if favorites_only:
        stmt = stmt.where(Recipe.is_favorite.is_(True))

    stmt = stmt.order_by(Recipe.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return [RecipeRead.model_validate(r) for r in result.scalars().unique().all()]


@router.post("/{cookbook_id}/recipes", response_model=RecipeRead, status_code=201)
async def create_cookbook_recipe(
    cookbook_id: int,
    payload: RecipeCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> RecipeRead:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role not in (CookbookRole.CREATOR, CookbookRole.EDITOR):
        raise HTTPException(status_code=403, detail="Permission insuffisante")

    tag_ids = payload.tag_ids or []
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
        is_favorite=payload.is_favorite,
        is_public=False,
        owner_id=current_user.id,
        cookbook_id=cookbook_id,
    )
    db.add(recipe)
    await db.flush()

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
    for step in payload.steps:
        db.add(
            RecipeStep(recipe_id=recipe.id, content=step.content, position=step.position)
        )
    if tag_ids:
        from app.models.recipe import RecipeTag, Tag
        result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        for tag in result.scalars().all():
            db.add(RecipeTag(recipe_id=recipe.id, tag_id=tag.id))

    await db.commit()
    # search_vector
    from app.api.v1.endpoints.recipes import _build_search_vector
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
    return RecipeRead.model_validate(result.scalar_one())


# ---------- Messagerie instantanee ----------

@router.get("/{cookbook_id}/messages", response_model=list[CookbookMessageRead])
async def list_messages(
    cookbook_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    before_id: int | None = None,
) -> list[CookbookMessageRead]:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role is None:
        raise HTTPException(status_code=403, detail="Vous n'etes pas membre de ce cookbook")
    stmt = (
        select(CookbookMessage)
        .options(selectinload(CookbookMessage.author))
        .where(CookbookMessage.cookbook_id == cookbook_id)
    )
    if before_id:
        stmt = stmt.where(CookbookMessage.id < before_id)
    stmt = stmt.order_by(CookbookMessage.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    msgs = [CookbookMessageRead.model_validate(m) for m in result.scalars().all()]
    return list(reversed(msgs))


@router.post("/{cookbook_id}/messages", response_model=CookbookMessageRead, status_code=201)
async def post_message(
    cookbook_id: int,
    payload: CookbookMessageCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CookbookMessageRead:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role is None:
        raise HTTPException(status_code=403, detail="Vous n'etes pas membre de ce cookbook")
    if role == CookbookRole.READER:
        raise HTTPException(status_code=403, detail="Les lecteurs ne peuvent pas envoyer de messages")
    msg = CookbookMessage(
        cookbook_id=cookbook_id, author_id=current_user.id, content=payload.content
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    # Broadcaster via WebSocket
    await manager.broadcast(
        cookbook_id,
        {
            "id": msg.id,
            "author_id": msg.author_id,
            "author": UserPublic.model_validate(current_user).model_dump(),
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        },
    )
    return CookbookMessageRead.model_validate(msg)


# ---------- WebSocket chat ----------

@router.websocket("/ws/{cookbook_id}")
async def websocket_chat(
    websocket: WebSocket, cookbook_id: int, db: AsyncSession = Depends(get_db)
):
    """Chat WebSocket pour un cookbook. Auth par token dans query string."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    from app.core.security import decode_access_token
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=4401)
        return
    user_id = int(payload["sub"])
    role = await _get_member_role(db, cookbook_id, user_id)
    if role is None:
        await websocket.close(code=4403)
        return
    if role == CookbookRole.READER:
        await websocket.close(code=4403)
        return

    await manager.connect(cookbook_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "").strip()
            if not content:
                continue
            msg = CookbookMessage(
                cookbook_id=cookbook_id, author_id=user_id, content=content[:2000]
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)
            author = await db.get(User, user_id)
            await manager.broadcast(
                cookbook_id,
                {
                    "id": msg.id,
                    "author_id": user_id,
                    "author": UserPublic.model_validate(author).model_dump(),
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                },
            )
    except WebSocketDisconnect:
        manager.disconnect(cookbook_id, websocket)


# ---------- Helpers ----------

async def _get_member_role(
    db: AsyncSession, cookbook_id: int, user_id: int
) -> CookbookRole | None:
    result = await db.execute(
        select(CookbookMember).where(
            (CookbookMember.cookbook_id == cookbook_id) & (CookbookMember.user_id == user_id)
        )
    )
    m = result.scalar_one_or_none()
    return m.role if m else None


COOKBOOK_NOT_FOUND = HTTPException(status_code=404, detail="Cookbook introuvable")