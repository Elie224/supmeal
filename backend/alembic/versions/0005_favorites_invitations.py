"""Add per-user favorites and cookbook invitations

Revision ID: 0005_fav_invite
Revises: 0004_no_email_verify
Create Date: 2026-07-19 00:10:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_fav_invite"
down_revision: Union[str, None] = "0004_no_email_verify"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    invitation_status = sa.Enum(
        "pending",
        "accepted",
        "expired",
        "revoked",
        name="invitation_status",
    )
    invitation_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "recipe_favorites",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "recipe_id"),
    )
    op.create_index("ix_recipe_favorites_user_id", "recipe_favorites", ["user_id"], unique=False)
    op.create_index("ix_recipe_favorites_recipe_id", "recipe_favorites", ["recipe_id"], unique=False)

    # Migration de l ancien flag global vers un favori personnel du proprietaire.
    op.execute(
        """
        INSERT INTO recipe_favorites (user_id, recipe_id)
        SELECT owner_id, id
        FROM recipes
        WHERE is_favorite = TRUE AND owner_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    op.create_table(
        "cookbook_invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cookbook_id", sa.Integer(), nullable=False),
        sa.Column("invited_email", sa.String(length=255), nullable=False),
        sa.Column(
            "invited_role",
            postgresql.ENUM(
                "creator",
                "editor",
                "commentator",
                "reader",
                name="cookbook_role",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "accepted",
                "expired",
                "revoked",
                name="invitation_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cookbook_id"], ["cookbooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_cookbook_invitations_token"),
    )
    op.create_index("ix_cookbook_invitations_cookbook_id", "cookbook_invitations", ["cookbook_id"], unique=False)
    op.create_index("ix_cookbook_invitations_invited_email", "cookbook_invitations", ["invited_email"], unique=False)
    op.create_index("ix_cookbook_invitations_token", "cookbook_invitations", ["token"], unique=True)
    op.create_index("ix_cookbook_invitations_expires_at", "cookbook_invitations", ["expires_at"], unique=False)
    op.create_index("ix_cookbook_invitations_status", "cookbook_invitations", ["status"], unique=False)
    op.create_index("ix_cookbook_invitations_invited_by_user_id", "cookbook_invitations", ["invited_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cookbook_invitations_invited_by_user_id", table_name="cookbook_invitations")
    op.drop_index("ix_cookbook_invitations_status", table_name="cookbook_invitations")
    op.drop_index("ix_cookbook_invitations_expires_at", table_name="cookbook_invitations")
    op.drop_index("ix_cookbook_invitations_token", table_name="cookbook_invitations")
    op.drop_index("ix_cookbook_invitations_invited_email", table_name="cookbook_invitations")
    op.drop_index("ix_cookbook_invitations_cookbook_id", table_name="cookbook_invitations")
    op.drop_table("cookbook_invitations")

    op.drop_index("ix_recipe_favorites_recipe_id", table_name="recipe_favorites")
    op.drop_index("ix_recipe_favorites_user_id", table_name="recipe_favorites")
    op.drop_table("recipe_favorites")

    invitation_status = sa.Enum(
        "pending",
        "accepted",
        "expired",
        "revoked",
        name="invitation_status",
    )
    invitation_status.drop(op.get_bind(), checkfirst=True)
