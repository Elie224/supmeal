"""Modele User."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.cookbook import Cookbook
    from app.models.recipe import Recipe


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class AuthProvider(str, enum.Enum):
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, name="auth_provider", values_callable=lambda x: [e.value for e in x]),
        default=AuthProvider.LOCAL,
        nullable=False,
    )
    provider_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda x: [e.value for e in x]), default=UserRole.USER, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Preferences culinaires (JSON serialise via Text pour portabilite)
    dietary_preferences: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    allergies: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    favorite_cuisines: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    default_servings: Mapped[int] = mapped_column(default=4, nullable=False)

    # Relations
    recipes: Mapped[list["Recipe"]] = relationship(
        "Recipe", back_populates="owner", cascade="all, delete-orphan", lazy="noload"
    )
    owned_cookbooks: Mapped[list["Cookbook"]] = relationship(
        "Cookbook", back_populates="owner", cascade="all, delete-orphan", lazy="noload"
    )
