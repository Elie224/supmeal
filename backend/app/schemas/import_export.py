"""Schemas de validation pour import/export."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from app.models.cookbook import CookbookRole


class IngredientImport(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: float | None = None
    unit: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=255)


class StepImport(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class RecipeImport(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    source_url: HttpUrl | None = None
    prep_time_minutes: int = Field(default=0, ge=0, le=24 * 60)
    cook_time_minutes: int = Field(default=0, ge=0, le=24 * 60)
    servings: int = Field(default=4, ge=1, le=50)
    difficulty: str | None = Field(default=None, max_length=20)
    cuisine_type: str | None = Field(default=None, max_length=80)
    image_url: HttpUrl | None = None
    ingredients: list[IngredientImport] = Field(default_factory=list, max_length=500)
    steps: list[StepImport] = Field(default_factory=list, max_length=500)
    tag_names: list[str] = Field(default_factory=list, max_length=100)


class CookbookImport(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    members: list[dict] = Field(default_factory=list)
    recipes: list[RecipeImport] = Field(default_factory=list, max_length=1000)


class SupmealUserExport(BaseModel):
    username: str
    email: EmailStr


class SupmealImportPayload(BaseModel):
    format: Literal["supmeal-json"] = "supmeal-json"
    version: int = 1
    user: SupmealUserExport | None = None
    recipes: list[RecipeImport] = Field(default_factory=list, max_length=2000)
    cookbooks: list[CookbookImport] = Field(default_factory=list, max_length=200)


class MealieUnit(BaseModel):
    name: str | None = None


class MealieIngredient(BaseModel):
    note: str | None = None
    quantity: float | str | None = None
    unit: MealieUnit | None = None


class MealieInstruction(BaseModel):
    text: str | None = None


class MealieTag(BaseModel):
    name: str | None = None


class MealieRecipe(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    description: str | None = None
    org_url: HttpUrl | None = Field(default=None, alias="orgURL")
    prep_time: str | int | None = Field(default=None, alias="prepTime")
    cook_time: str | int | None = Field(default=None, alias="cookTime")
    recipe_servings: int | None = Field(default=None, ge=1, le=50, alias="recipeServings")
    image: HttpUrl | None = None
    recipe_ingredient: list[MealieIngredient] = Field(default_factory=list, alias="recipeIngredient")
    recipe_instructions: list[MealieInstruction] = Field(default_factory=list, alias="recipeInstructions")
    tags: list[MealieTag] = Field(default_factory=list)


class MealieImportPayload(BaseModel):
    format: Literal["mealie"] = "mealie"
    recipes: list[MealieRecipe] = Field(default_factory=list, max_length=2000)


class CookbookInvitationMember(BaseModel):
    user_id: int
    role: CookbookRole


class SupmealCookbookExport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    description: str | None = None
    members: list[CookbookInvitationMember] = Field(default_factory=list)
    recipes: list[RecipeImport] = Field(default_factory=list)
