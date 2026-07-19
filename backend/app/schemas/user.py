"""Schemas Pydantic lies a User."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import AuthProvider, UserRole


class UserBase(BaseModel):
    email: EmailStr
    username: Annotated[str, Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")]
    full_name: str | None = None


class UserCreate(UserBase):
    password: Annotated[str, Field(min_length=8, max_length=128)]
    dietary_preferences: str | None = None
    allergies: str | None = None
    favorite_cuisines: str | None = None
    default_servings: int = Field(default=4, ge=1, le=50)


class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
    dietary_preferences: str | None = None
    allergies: str | None = None
    favorite_cuisines: str | None = None
    default_servings: int | None = Field(default=None, ge=1, le=50)


class PasswordChange(BaseModel):
    current_password: str
    new_password: Annotated[str, Field(min_length=8, max_length=128)]


class UserRead(UserBase):
    id: int
    avatar_url: str | None
    role: UserRole
    auth_provider: AuthProvider
    is_active: bool
    is_verified: bool
    default_servings: int
    dietary_preferences: str | None
    allergies: str | None
    favorite_cuisines: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserPublic(BaseModel):
    """Profil public (visible par les autres membres d'un cookbook)."""
    id: int
    username: str
    full_name: str | None
    avatar_url: str | None

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
