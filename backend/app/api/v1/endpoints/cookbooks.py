"""Endpoints Cookbook : CRUD, membres, recettes du cookbook, messagerie."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, get_db
from app.models.cookbook import (
    Cookbook,
    CookbookInvitation,
    CookbookMember,
    CookbookMessage,
    CookbookRole,
    InvitationStatus,
)
from app.models.recipe import Recipe, RecipeFavorite
from app.models.user import User
from app.schemas.cookbook import (
    AddMemberRequest,
    CookbookCreate,
    CookbookInvitationCreate,
    CookbookInvitationRead,
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
from app.services.recipe_service import create_recipe as svc_create_recipe

router = APIRouter()


def _recipe_read_with_user_favorite(recipe: Recipe, is_favorite: bool) -> RecipeRead:
    data = RecipeRead.model_validate(recipe).model_dump()
    data["is_favorite"] = is_favorite
    return RecipeRead.model_validate(data)


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
    cookbook_ids = [cookbook.id for cookbook, _ in rows]

    member_count_by_cookbook: dict[int, int] = {}
    recipe_count_by_cookbook: dict[int, int] = {}

    if cookbook_ids:
        members_result = await db.execute(
            select(CookbookMember.cookbook_id, func.count(CookbookMember.user_id))
            .where(CookbookMember.cookbook_id.in_(cookbook_ids))
            .group_by(CookbookMember.cookbook_id)
        )
        member_count_by_cookbook = {
            cookbook_id: int(count)
            for cookbook_id, count in members_result.all()
        }

        recipes_result = await db.execute(
            select(Recipe.cookbook_id, func.count(Recipe.id))
            .where(Recipe.cookbook_id.in_(cookbook_ids))
            .group_by(Recipe.cookbook_id)
        )
        recipe_count_by_cookbook = {
            int(cookbook_id): int(count)
            for cookbook_id, count in recipes_result.all()
            if cookbook_id is not None
        }

    summaries: list[CookbookSummary] = []
    for cookbook, role in rows:
        summaries.append(
            CookbookSummary(
                id=cookbook.id,
                name=cookbook.name,
                description=cookbook.description,
                image_url=cookbook.image_url,
                owner_id=cookbook.owner_id,
                member_count=member_count_by_cookbook.get(cookbook.id, 0),
                recipe_count=recipe_count_by_cookbook.get(cookbook.id, 0),
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


@router.post("/{cookbook_id}/invitations", response_model=CookbookInvitationRead, status_code=201)
async def create_invitation(
    cookbook_id: int,
    payload: CookbookInvitationCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CookbookInvitationRead:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role != CookbookRole.CREATOR:
        raise HTTPException(status_code=403, detail="Reserve au createur")

    invited_email = payload.invited_email.lower().strip()

    user_result = await db.execute(select(User).where(User.email == invited_email))
    user = user_result.scalar_one_or_none()
    if user:
        existing = await _get_member_role(db, cookbook_id, user.id)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Utilisateur deja membre")

    pending_result = await db.execute(
        select(CookbookInvitation).where(
            (CookbookInvitation.cookbook_id == cookbook_id)
            & (CookbookInvitation.invited_email == invited_email)
            & (CookbookInvitation.status == InvitationStatus.PENDING)
        )
    )
    pending = pending_result.scalars().all()
    for inv in pending:
        inv.status = InvitationStatus.REVOKED

    invitation = CookbookInvitation(
        cookbook_id=cookbook_id,
        invited_email=invited_email,
        invited_role=payload.invited_role,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(UTC) + timedelta(days=payload.expires_in_days),
        status=InvitationStatus.PENDING,
        invited_by_user_id=current_user.id,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return CookbookInvitationRead.model_validate(invitation)


@router.get("/{cookbook_id}/invitations", response_model=list[CookbookInvitationRead])
async def list_invitations(
    cookbook_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    only_pending: bool = True,
) -> list[CookbookInvitationRead]:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role != CookbookRole.CREATOR:
        raise HTTPException(status_code=403, detail="Reserve au createur")

    stmt = select(CookbookInvitation).where(CookbookInvitation.cookbook_id == cookbook_id)
    if only_pending:
        stmt = stmt.where(CookbookInvitation.status == InvitationStatus.PENDING)
    stmt = stmt.order_by(CookbookInvitation.created_at.desc())
    result = await db.execute(stmt)
    return [CookbookInvitationRead.model_validate(i) for i in result.scalars().all()]


@router.delete("/{cookbook_id}/invitations/{invitation_id}", status_code=204)
async def revoke_invitation(
    cookbook_id: int,
    invitation_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    role = await _get_member_role(db, cookbook_id, current_user.id)
    if role != CookbookRole.CREATOR:
        raise HTTPException(status_code=403, detail="Reserve au createur")

    result = await db.execute(
        select(CookbookInvitation).where(
            (CookbookInvitation.id == invitation_id)
            & (CookbookInvitation.cookbook_id == cookbook_id)
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation introuvable")

    if invitation.status == InvitationStatus.PENDING:
        invitation.status = InvitationStatus.REVOKED
        await db.commit()


@router.post("/invitations/{token}/accept", status_code=200)
async def accept_invitation(
    token: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    result = await db.execute(select(CookbookInvitation).where(CookbookInvitation.token == token))
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation introuvable")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invitation non valide")

    if invitation.invited_email.lower() != current_user.email.lower():
        raise HTTPException(status_code=403, detail="Cette invitation ne vous est pas destinee")

    now = datetime.now(UTC)
    if invitation.expires_at < now:
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(status_code=400, detail="Invitation expiree")

    existing = await _get_member_role(db, invitation.cookbook_id, current_user.id)
    if existing is None:
        db.add(
            CookbookMember(
                cookbook_id=invitation.cookbook_id,
                user_id=current_user.id,
                role=invitation.invited_role,
            )
        )

    invitation.status = InvitationStatus.ACCEPTED
    await db.commit()
    return {
        "detail": "Invitation acceptee",
        "cookbook_id": invitation.cookbook_id,
    }


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
        ts_query = func.websearch_to_tsquery("french", search)
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
    if favorites_only:
        stmt = stmt.join(
            RecipeFavorite,
            and_(
                RecipeFavorite.recipe_id == Recipe.id,
                RecipeFavorite.user_id == current_user.id,
            ),
        )
    if max_prep_time is not None:
        stmt = stmt.where(Recipe.prep_time_minutes <= max_prep_time)
    stmt = stmt.order_by(Recipe.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    recipes = result.scalars().unique().all()

    favorite_ids: set[int] = set()
    if recipes:
        fav_result = await db.execute(
            select(RecipeFavorite.recipe_id).where(
                (RecipeFavorite.user_id == current_user.id)
                & (RecipeFavorite.recipe_id.in_([r.id for r in recipes]))
            )
        )
        favorite_ids = set(fav_result.scalars().all())

    if favorites_only:
        favorite_ids = {r.id for r in recipes}

    return [_recipe_read_with_user_favorite(r, r.id in favorite_ids) for r in recipes]


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
        is_public=False,
        cookbook_id=cookbook_id,
        ingredients=[ing.model_dump() for ing in payload.ingredients],
        steps=[step.model_dump() for step in payload.steps],
        tag_ids=payload.tag_ids or [],
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
    return _recipe_read_with_user_favorite(recipe_out, False)


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

# Vide par defaut (tests). En prod, remplir avec les origines frontend autorisees.
_ALLOWED_WS_ORIGINS: set = set()


def _extract_ws_token(websocket) -> str | None:
    """Recupere le JWT via :
    1. Sec-WebSocket-Protocol (le client demande un sub-protocol bearer.<token>)
    2. Cookie httpOnly supmeal_token
    3. Authorization: Bearer <token> header
    NE CHERCHE PLUS le token dans l URL (fuite logs/referrer).
    """
    proto = websocket.headers.get("sec-websocket-protocol") or ""
    for part in proto.split(","):
        part = part.strip()
        if part.startswith("bearer."):
            token = part[len("bearer."):]
            if token:
                return token
    cookie_header = websocket.headers.get("cookie") or ""
    for chunk in cookie_header.split(";"):
        kv = chunk.strip()
        if kv.startswith("supmeal_token="):
            return kv[len("supmeal_token="):]
    auth = websocket.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


async def _get_member_role_ws(db, cookbook_id: int, user_id: int):
    """Meme logique que _get_member_role, exposee pour la session WS manuelle."""
    from sqlalchemy import select as _select
    result = await db.execute(
        _select(CookbookMember).where(
            (CookbookMember.cookbook_id == cookbook_id) & (CookbookMember.user_id == user_id)
        )
    )
    m = result.scalar_one_or_none()
    return m.role if m else None


@router.websocket("/{cookbook_id}/ws")
async def websocket_chat(websocket, cookbook_id: str):
    """Chat WebSocket pour un cookbook. Auth via sub-protocol ou cookie httpOnly."""
    # 1) Accepter d abord (sinon Starlette renvoie 403 avant meme d executer la fonction)
    #    On valide tout le reste en interne.
    await websocket.accept()

    # 2) Verifier l origine
    origin = websocket.headers.get("origin")
    if origin and _ALLOWED_WS_ORIGINS and origin not in _ALLOWED_WS_ORIGINS:
        await websocket.close(code=4403)
        return

    # 3) Verifier le token
    token = _extract_ws_token(websocket)
    if not token:
        await websocket.close(code=4401)
        return
    from app.core.security import decode_access_token
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=4401)
        return
    user_id = int(payload["sub"])

    # 4) Rate limit par user
    from app.core.ratelimit import message_limiter, ws_limiter
    if not ws_limiter.is_allowed(str(user_id)):
        await websocket.close(code=4429)
        return

    # 5) Verifier les droits sur le cookbook
    try:
        cb_id = int(cookbook_id)
    except (TypeError, ValueError):
        await websocket.close(code=4400)
        return

    from app.db.session import AsyncSessionLocal as _AsyncSessionLocal
    async with _AsyncSessionLocal() as db:
        role = await _get_member_role_ws(db, cb_id, user_id)
        if role is None:
            await websocket.close(code=4403)
            return

    # 6) Boucle de chat
    await manager.connect(cb_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            content = (data.get("content") or "").strip()
            if not content:
                continue
            # Rate limit sur les messages
            if not message_limiter.is_allowed(str(user_id)):
                continue
            async with _AsyncSessionLocal() as db:
                msg = CookbookMessage(cookbook_id=cb_id, author_id=user_id, content=content[:2000])
                db.add(msg)
                await db.commit()
                await db.refresh(msg)
                author = await db.get(User, user_id)
            await manager.broadcast(
                cb_id,
                {
                    "id": msg.id,
                    "author_id": user_id,
                    "author": UserPublic.model_validate(author).model_dump(),
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                },
            )
    except WebSocketDisconnect:
        manager.disconnect(cb_id, websocket)


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
