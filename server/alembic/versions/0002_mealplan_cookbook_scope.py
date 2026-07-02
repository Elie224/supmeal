"""Add cookbook scope to meal plans

Revision ID: 0002_mealplan_cookbook_scope
Revises: 0001_initial
Create Date: 2026-07-02 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_mealplan_cookbook_scope"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meal_plans", sa.Column("cookbook_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_meal_plans_cookbook_id_cookbooks",
        "meal_plans",
        "cookbooks",
        ["cookbook_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_meal_plans_cookbook_id", "meal_plans", ["cookbook_id"], unique=False)
    op.create_index(
        "ix_meal_plans_cookbook_date",
        "meal_plans",
        ["cookbook_id", "planned_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_meal_plans_cookbook_date", table_name="meal_plans")
    op.drop_index("ix_meal_plans_cookbook_id", table_name="meal_plans")
    op.drop_constraint("fk_meal_plans_cookbook_id_cookbooks", "meal_plans", type_="foreignkey")
    op.drop_column("meal_plans", "cookbook_id")
