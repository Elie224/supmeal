"""Modele Recipe et structures associees (ingredients, etapes, tags)."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.cookbook import Cookbook
    from app.models.user import User


class Recipe(Base, TimestampMixin):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    prep_time_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cook_time_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    servings: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cuisine_type: Mapped[str | None] = mapped_column(String(80), nullable=True)

    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Proprietaire (null si recette dans un cookbook seulement)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Cookbook d'appartenance (null si recette personnelle)
    cookbook_id: Mapped[int | None] = mapped_column(
        ForeignKey("cookbooks.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Recherche plein texte : champ calcule
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    owner: Mapped["User | None"] = relationship("User", back_populates="recipes", lazy="selectin")
    cookbook: Mapped["Cookbook | None"] = relationship(
        "Cookbook", back_populates="recipes", lazy="selectin"
    )
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", lazy="selectin", order_by="RecipeIngredient.position"
    )
    steps: Mapped[list["RecipeStep"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", lazy="selectin", order_by="RecipeStep.position"
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="recipe_tags", back_populates="recipes", lazy="selectin"
    )
    meal_plans: Mapped[list["MealPlan"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_recipes_search", "search_vector", postgresql_using="gin"),
        Index("ix_recipes_title_trgm", "title", postgresql_using="gin",
              postgresql_ops={"title": "gin_trgm_ops"}),
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    quantity: Mapped[float | None] = mapped_column(nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="steps")


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # category: "diet", "cuisine", "difficulty", "type"

    recipes: Mapped[list["Recipe"]] = relationship(
        secondary="recipe_tags", back_populates="tags", lazy="selectin"
    )


class RecipeTag(Base):
    """Table d'association Recipe <-> Tag."""
    __tablename__ = "recipe_tags"

    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


class MealPlan(Base, TimestampMixin):
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    cookbook_id: Mapped[int | None] = mapped_column(
        ForeignKey("cookbooks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    planned_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    meal_slot: Mapped[str] = mapped_column(String(20), nullable=False)  # breakfast/lunch/dinner/snack
    servings: Mapped[int] = mapped_column(Integer, default=4, nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="meal_plans", lazy="selectin")
    cookbook: Mapped["Cookbook | None"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_meal_plans_user_date", "user_id", "planned_date"),
        Index("ix_meal_plans_cookbook_date", "cookbook_id", "planned_date"),
    )


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="comments", lazy="selectin")