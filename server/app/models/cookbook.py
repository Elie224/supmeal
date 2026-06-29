"""Modeles Cookbook, CookbookMember, CookbookMessage."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.recipe import Recipe
    from app.models.user import User


class CookbookRole(str, enum.Enum):
    """Role d'un membre dans un cookbook partage.

    - CREATOR: createur, tous les droits dont suppression du cookbook
    - EDITOR: peut ajouter/modifier/supprimer les recettes
    - COMMENTATOR: peut commenter et discuter
    - READER: lecture seule
    """

    CREATOR = "creator"
    EDITOR = "editor"
    COMMENTATOR = "commentator"
    READER = "reader"


class Cookbook(Base, TimestampMixin):
    __tablename__ = "cookbooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    members: Mapped[list["CookbookMember"]] = relationship(
        back_populates="cookbook", cascade="all, delete-orphan", lazy="selectin"
    )
    recipes: Mapped[list["Recipe"]] = relationship(back_populates="cookbook", lazy="selectin")
    messages: Mapped[list["CookbookMessage"]] = relationship(
        back_populates="cookbook", cascade="all, delete-orphan", lazy="selectin",
        order_by="CookbookMessage.created_at"
    )

    @property
    def creator_role(self) -> CookbookRole:
        return CookbookRole.CREATOR


class CookbookMember(Base, TimestampMixin):
    __tablename__ = "cookbook_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    cookbook_id: Mapped[int] = mapped_column(
        ForeignKey("cookbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[CookbookRole] = mapped_column(
        Enum(CookbookRole, name="cookbook_role"),
        default=CookbookRole.READER,
        nullable=False,
    )

    cookbook: Mapped["Cookbook"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("cookbook_id", "user_id", name="uq_cookbook_member"),
    )


class CookbookMessage(Base):
    """Message de chat dans un cookbook partage."""
    __tablename__ = "cookbook_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    cookbook_id: Mapped[int] = mapped_column(
        ForeignKey("cookbooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    cookbook: Mapped["Cookbook"] = relationship(back_populates="messages")
    author: Mapped["User"] = relationship(lazy="selectin")