"""Schemas Pydantic lies a Recipe, Ingredient, Step, Tag."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# ---------- Tags ----------

class TagBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=60)]
    category: str | None = None  # diet / cuisine / difficulty / type


class TagCreate(TagBase):
    pass


class TagRead(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Ingredients ----------

class IngredientBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    quantity: float | None = None
    unit: str | None = None
    note: str | None = None
    position: int = 0


class IngredientCreate(IngredientBase):
    pass


class IngredientRead(IngredientBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Steps ----------

class StepBase(BaseModel):
    content: str
    position: int = 0


class StepCreate(StepBase):
    pass


class StepRead(StepBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Recipes ----------

class RecipeBase(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: str | None = None
    source_url: str | None = None
    prep_time_minutes: int = Field(default=0, ge=0, le=24*60)
    cook_time_minutes: int = Field(default=0, ge=0, le=24*60)
    servings: int = Field(default=4, ge=1, le=50)
    difficulty: str | None = None
    cuisine_type: str | None = None
    image_url: str | None = None
    is_favorite: bool = False
    is_public: bool = False
    tag_ids: list[int] = []


class RecipeCreate(RecipeBase):
    ingredients: list[IngredientCreate] = []
    steps: list[StepCreate] = []
    cookbook_id: int | None = None  # Optionnel : creer dans un cookbook directement


class RecipeUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    source_url: str | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    servings: int | None = None
    difficulty: str | None = None
    cuisine_type: str | None = None
    image_url: str | None = None
    is_favorite: bool | None = None
    is_public: bool | None = None
    tag_ids: list[int] | None = None
    ingredients: list[IngredientCreate] | None = None
    steps: list[StepCreate] | None = None


class RecipeRead(RecipeBase):
    id: int
    owner_id: int | None
    cookbook_id: int | None
    ingredients: list[IngredientRead]
    steps: list[StepRead]
    tags: list[TagRead]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecipeSummary(BaseModel):
    """Version allegee pour listes (sans ingredients/etapes complets)."""
    id: int
    title: str
    description: str | None
    image_url: str | None
    prep_time_minutes: int
    cook_time_minutes: int
    servings: int
    is_favorite: bool = False
    owner_id: int | None
    cookbook_id: int | None
    tags: list[TagRead]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecipeFilter(BaseModel):
    """Parametres de filtrage des recettes."""
    cookbook_id: int | None = None
    tag_ids: list[int] | None = None
    ingredient: str | None = None
    max_prep_time: int | None = None
    max_cook_time: int | None = None
    favorites_only: bool = False
    search: str | None = None
    skip: int = 0
    limit: int = Field(default=20, le=100)


# ---------- Meal Plan ----------

class MealPlanBase(BaseModel):
    recipe_id: int
    cookbook_id: int | None = None
    planned_date: str  # YYYY-MM-DD
    meal_slot: str  # breakfast/lunch/dinner/snack
    servings: int = 4


class MealPlanCreate(MealPlanBase):
    pass


class MealPlanRead(MealPlanBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Comment ----------

class CommentCreate(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=2000)]


class CommentRead(BaseModel):
    id: int
    content: str
    author_id: int
    recipe_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Suggestions ----------

class RecipeSuggestRequest(BaseModel):
    """Requete pour le suggester de recettes base sur les ingredients disponibles."""

    ingredients: Annotated[list[str], Field(min_length=1, max_length=50)]
    tag_ids: list[int] | None = None
    cookbook_id: int | None = None
    max_prep_time: int | None = Field(default=None, ge=0, le=24*60)
    max_cook_time: int | None = Field(default=None, ge=0, le=24*60)
    limit: int = Field(default=10, ge=1, le=50)

    model_config = ConfigDict(extra="forbid")


class RecipeSuggestion(BaseModel):
    """Une suggestion de recette avec le detail du matching."""

    recipe: RecipeSummary
    match_score: float = Field(ge=0.0, le=1.0)
    matched_ingredients: list[str]
    missing_ingredients: list[str]
