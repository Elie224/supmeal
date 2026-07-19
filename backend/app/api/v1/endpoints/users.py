"""Endpoints utilisateur : profil, mot de passe, preferences."""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import CurrentUser, get_db
from app.core.security import hash_password, verify_password
from app.core.security_utils import safe_image_extension, sniff_image
from app.models.user import User
from app.schemas.user import PasswordChange, UserPublic, UserRead, UserUpdate

router = APIRouter()
settings = get_settings()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.get("", response_model=list[UserPublic])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = ...,
    q: str | None = None,
) -> list[UserPublic]:
    """Liste minimale des utilisateurs (pour inviter dans un cookbook). Auth requise."""
    stmt = select(User).order_by(User.username).limit(200)
    if q:
        like = f"%{q[:60]}%"
        stmt = stmt.where((User.username.ilike(like)) | (User.email.ilike(like)))
    result = await db.execute(stmt)
    return [UserPublic.model_validate(u) for u in result.scalars().all()]


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = ...,
) -> UserPublic:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return UserPublic.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> UserRead:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(current_user, key, value)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> None:
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="Compte OAuth - pas de mot de passe a changer")
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    db.add(current_user)
    await db.commit()


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> UserRead:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Format non supporte")

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux")

    # Validation par magic bytes (defense contre svg, php, html, scripts)
    sniffed = sniff_image(content)
    if sniffed is None:
        raise HTTPException(
            status_code=400,
            detail="Contenu invalide: seuls JPEG, PNG, GIF, WebP sont acceptes",
        )
    ext = safe_image_extension(os.path.splitext(file.filename or "")[1], sniffed)

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex}{ext}"
    filepath = upload_dir / filename
    filepath.write_bytes(content)

    # Supprimer ancien avatar si local
    if current_user.avatar_url and current_user.avatar_url.startswith("/uploads/"):
        old = upload_dir / Path(current_user.avatar_url).name
        if old.exists() and old.is_file():
            old.unlink()

    current_user.avatar_url = f"/uploads/{filename}"
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return UserRead.model_validate(current_user)
