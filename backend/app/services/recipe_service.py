"""Service central pour creation/mise a jour des recettes."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipe import Recipe, RecipeFavorite, RecipeIngredient, RecipeStep, RecipeTag, Tag


def _to_int(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


async def rebuild_search_vector(db: AsyncSession, recipe_id: int) -> None:
    result = await db.execute(
        select(Recipe).where(Recipe.id == recipe_id)
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        return

    ing_result = await db.execute(
        select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id).order_by(RecipeIngredient.position)
    )
    ingredients = ing_result.scalars().all()

    step_result = await db.execute(
        select(RecipeStep).where(RecipeStep.recipe_id == recipe_id).order_by(RecipeStep.position)
    )
    steps = step_result.scalars().all()

    tag_result = await db.execute(
        select(Tag)
        .join(RecipeTag, RecipeTag.tag_id == Tag.id)
        .where(RecipeTag.recipe_id == recipe_id)
    )
    tags = tag_result.scalars().all()

    parts = [
        recipe.title or "",
        recipe.description or "",
        recipe.cuisine_type or "",
        recipe.difficulty or "",
    ]
    parts.extend(i.name for i in ingredients)
    parts.extend(s.content for s in steps)
    parts.extend(t.name for t in tags)

    await db.execute(
        text("UPDATE recipes SET search_vector = to_tsvector('french', :txt) WHERE id = :rid"),
        {"txt": " ".join(parts), "rid": recipe_id},
    )


async def create_recipe(
    db: AsyncSession,
    *,
    owner_id: int,
    title: str,
    description: str | None = None,
    source_url: str | None = None,
    prep_time_minutes: int = 0,
    cook_time_minutes: int = 0,
    servings: int = 4,
    difficulty: str | None = None,
    cuisine_type: str | None = None,
    image_url: str | None = None,
    is_public: bool = False,
    cookbook_id: int | None = None,
    ingredients: Sequence[dict[str, Any]] = (),
    steps: Sequence[dict[str, Any]] = (),
    tag_ids: Sequence[int] = (),
    tag_names: Sequence[str] = (),
    favorite_user_id: int | None = None,
) -> Recipe:
    recipe = Recipe(
        title=title,
        description=description,
        source_url=source_url,
        prep_time_minutes=_to_int(prep_time_minutes, 0),
        cook_time_minutes=_to_int(cook_time_minutes, 0),
        servings=_to_int(servings, 4),
        difficulty=difficulty,
        cuisine_type=cuisine_type,
        image_url=image_url,
        is_public=is_public,
        owner_id=owner_id,
        cookbook_id=cookbook_id,
    )
    db.add(recipe)
    await db.flush()

    for i, ing in enumerate(ingredients):
        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                name=str(ing.get("name", "")),
                quantity=ing.get("quantity"),
                unit=ing.get("unit"),
                note=ing.get("note"),
                position=int(ing.get("position", i)),
            )
        )

    for i, step in enumerate(steps):
        content = str(step.get("content", "")).strip()
        if not content:
            continue
        db.add(
            RecipeStep(
                recipe_id=recipe.id,
                content=content,
                position=int(step.get("position", i)),
            )
        )

    if tag_ids:
        tag_result = await db.execute(select(Tag).where(Tag.id.in_(list(tag_ids))))
        for tag in tag_result.scalars().all():
            db.add(RecipeTag(recipe_id=recipe.id, tag_id=tag.id))

    for raw_name in tag_names:
        name = str(raw_name).strip().lower()
        if not name:
            continue
        existing_tag = await db.execute(select(Tag).where(Tag.name == name))
        tag = existing_tag.scalar_one_or_none()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            await db.flush()
        db.add(RecipeTag(recipe_id=recipe.id, tag_id=tag.id))

    if favorite_user_id is not None:
        db.add(RecipeFavorite(user_id=favorite_user_id, recipe_id=recipe.id))

    await rebuild_search_vector(db, recipe.id)
    return recipe


async def update_recipe(
    db: AsyncSession,
    *,
    recipe: Recipe,
    fields: dict[str, Any],
    ingredients: list[dict[str, Any]] | None,
    steps: list[dict[str, Any]] | None,
    tag_ids: list[int] | None,
) -> Recipe:
    for key, value in fields.items():
        setattr(recipe, key, value)

    if ingredients is not None:
        await db.execute(RecipeIngredient.__table__.delete().where(RecipeIngredient.recipe_id == recipe.id))
        for i, ing in enumerate(ingredients):
            db.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    name=str(ing.get("name", "")),
                    quantity=ing.get("quantity"),
                    unit=ing.get("unit"),
                    note=ing.get("note"),
                    position=int(ing.get("position", i)),
                )
            )

    if steps is not None:
        await db.execute(RecipeStep.__table__.delete().where(RecipeStep.recipe_id == recipe.id))
        for i, step in enumerate(steps):
            content = str(step.get("content", "")).strip()
            if not content:
                continue
            db.add(
                RecipeStep(
                    recipe_id=recipe.id,
                    content=content,
                    position=int(step.get("position", i)),
                )
            )

    if tag_ids is not None:
        await db.execute(RecipeTag.__table__.delete().where(RecipeTag.recipe_id == recipe.id))
        for tid in tag_ids:
            db.add(RecipeTag(recipe_id=recipe.id, tag_id=tid))

    await db.flush()
    await rebuild_search_vector(db, recipe.id)
    return recipe
