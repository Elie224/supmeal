"""Schemas Pydantic lies a Cookbook, Member, Message."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.cookbook import CookbookRole
from app.schemas.user import UserPublic


class CookbookCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=150)]
    description: str | None = None
    image_url: str | None = None


class CookbookUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    image_url: str | None = None


class CookbookMemberRead(BaseModel):
    id: int
    user: UserPublic
    role: CookbookRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CookbookRead(BaseModel):
    id: int
    name: str
    description: str | None
    image_url: str | None
    owner_id: int
    members: list[CookbookMemberRead]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CookbookSummary(BaseModel):
    id: int
    name: str
    description: str | None
    image_url: str | None
    owner_id: int
    member_count: int = 0
    recipe_count: int = 0
    my_role: CookbookRole | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AddMemberRequest(BaseModel):
    user_email: EmailStr
    role: CookbookRole = CookbookRole.READER


class UpdateMemberRoleRequest(BaseModel):
    role: CookbookRole


class CookbookMessageCreate(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=2000)]


class CookbookMessageRead(BaseModel):
    id: int
    author_id: int
    author: UserPublic | None = None
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)