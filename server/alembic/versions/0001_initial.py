"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-15 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions necessaires
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    # Enums
    user_role = postgresql.ENUM("user", "admin", name="user_role", create_type=True)
    auth_provider = postgresql.ENUM(
        "local", "google", "github", "microsoft", name="auth_provider", create_type=True
    )
    cookbook_role = postgresql.ENUM(
        "creator", "editor", "commentator", "reader", name="cookbook_role", create_type=True
    )
    user_role.create(op.get_bind(), checkfirst=True)
    auth_provider.create(op.get_bind(), checkfirst=True)
    cookbook_role.create(op.get_bind(), checkfirst=True)

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("username", sa.String(50), unique=True, index=True, nullable=False),
        sa.Column("full_name", sa.String(120), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("auth_provider", auth_provider, nullable=False, server_default="local"),
        sa.Column("provider_user_id", sa.String(255), nullable=True, index=True),
        sa.Column("role", user_role, nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("dietary_preferences", sa.String(2000), nullable=True),
        sa.Column("allergies", sa.String(2000), nullable=True),
        sa.Column("favorite_cuisines", sa.String(2000), nullable=True),
        sa.Column("default_servings", sa.Integer, nullable=False, server_default="4"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Tags
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(60), unique=True, index=True, nullable=False),
        sa.Column("category", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Cookbooks
    op.create_table(
        "cookbooks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(150), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Cookbook members
    op.create_table(
        "cookbook_members",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cookbook_id", sa.Integer, sa.ForeignKey("cookbooks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("role", cookbook_role, nullable=False, server_default="reader"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("cookbook_id", "user_id", name="uq_cookbook_member"),
    )

    # Recipes
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("prep_time_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cook_time_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("servings", sa.Integer, nullable=False, server_default="4"),
        sa.Column("difficulty", sa.String(20), nullable=True),
        sa.Column("cuisine_type", sa.String(80), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("is_favorite", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("cookbook_id", sa.Integer, sa.ForeignKey("cookbooks.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("search_vector", postgresql.TSVECTOR, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recipes_search", "recipes", ["search_vector"], unique=False, postgresql_using="gin")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recipes_title_trgm ON recipes USING gin (title gin_trgm_ops)"
    )

    # Recipe ingredients
    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    )

    # Recipe steps
    op.create_table(
        "recipe_steps",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    )

    # Recipe tags
    op.create_table(
        "recipe_tags",
        sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    # Meal plans
    op.create_table(
        "meal_plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("planned_date", sa.String(10), nullable=False, index=True),
        sa.Column("meal_slot", sa.String(20), nullable=False),
        sa.Column("servings", sa.Integer, nullable=False, server_default="4"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_meal_plans_user_date", "meal_plans", ["user_id", "planned_date"], unique=False)

    # Comments
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("author_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Shopping lists
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("start_date", sa.String(10), nullable=True),
        sa.Column("end_date", sa.String(10), nullable=True),
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "shopping_list_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("shopping_list_id", sa.Integer, sa.ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("is_checked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("source_recipe_id", sa.Integer, sa.ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True),
    )

    # Messages
    op.create_table(
        "cookbook_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cookbook_id", sa.Integer, sa.ForeignKey("cookbooks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("author_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )

    # Trigger : mise a jour auto de search_vector
    op.execute(
        """
        CREATE OR REPLACE FUNCTION supmeal_recipe_search_vector() RETURNS trigger AS $$
        DECLARE
            parts text;
        BEGIN
            SELECT string_agg(DISTINCT elem, ' ') INTO parts
            FROM (
                SELECT NEW.title AS elem
                UNION ALL SELECT COALESCE(NEW.description, '')
                UNION ALL SELECT COALESCE(NEW.cuisine_type, '')
                UNION ALL SELECT COALESCE(NEW.difficulty, '')
                UNION ALL SELECT name FROM recipe_ingredients WHERE recipe_id = NEW.id
                UNION ALL SELECT content FROM recipe_steps WHERE recipe_id = NEW.id
                UNION ALL SELECT t.name FROM tags t
                    JOIN recipe_tags rt ON rt.tag_id = t.id
                    WHERE rt.recipe_id = NEW.id
            ) sub(elem);
            NEW.search_vector := to_tsvector('french', COALESCE(parts, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_recipe_search_vector
        BEFORE INSERT OR UPDATE ON recipes
        FOR EACH ROW EXECUTE FUNCTION supmeal_recipe_search_vector();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_recipe_search_vector ON recipes")
    op.execute("DROP FUNCTION IF EXISTS supmeal_recipe_search_vector()")
    op.drop_table("cookbook_messages")
    op.drop_table("shopping_list_items")
    op.drop_table("shopping_lists")
    op.drop_table("comments")
    op.drop_table("meal_plans")
    op.drop_table("recipe_tags")
    op.drop_table("recipe_steps")
    op.drop_table("recipe_ingredients")
    op.execute("DROP INDEX IF EXISTS ix_recipes_title_trgm")
    op.drop_index("ix_recipes_search", table_name="recipes")
    op.drop_table("recipes")
    op.drop_table("cookbook_members")
    op.drop_table("cookbooks")
    op.drop_table("tags")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS cookbook_role")
    op.execute("DROP TYPE IF EXISTS auth_provider")
    op.execute("DROP TYPE IF EXISTS user_role")