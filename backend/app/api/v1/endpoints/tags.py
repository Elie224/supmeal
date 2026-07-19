"""Endpoints Tags."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models.recipe import Tag
from app.schemas.recipe import TagCreate, TagRead

router = APIRouter()


@router.get("", response_model=list[TagRead])
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[TagRead]:
    result = await db.execute(select(Tag).order_by(Tag.name))
    return [TagRead.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=TagRead, status_code=201)
async def create_tag(
    payload: TagCreate, _: CurrentUser, db: AsyncSession = Depends(get_db)
) -> TagRead:
    existing = await db.execute(select(Tag).where(Tag.name == payload.name.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Tag deja existant")
    tag = Tag(name=payload.name.lower(), category=payload.category)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return TagRead.model_validate(tag)