"""Remove legacy recipes.is_favorite column.

Revision ID: 0006_remove_recipe_is_favorite
Revises: 0005_favorites_invitations
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0006_remove_recipe_is_favorite"
down_revision = "0005_favorites_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.drop_column("is_favorite")


def downgrade() -> None:
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.add_column(sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.alter_column("is_favorite", server_default=None)
