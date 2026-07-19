"""Remove microsoft value from auth_provider enum

Revision ID: 0003_rm_ms_authprov
Revises: 0002_mealplan_cookbook_scope
Create Date: 2026-07-19 00:00:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_rm_ms_authprov"
down_revision: Union[str, None] = "0002_mealplan_cookbook_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remap legacy values before shrinking enum.
    op.execute("UPDATE users SET auth_provider = 'local' WHERE auth_provider = 'microsoft'")

    # Drop default before enum type swap to avoid cast issues.
    op.execute("ALTER TABLE users ALTER COLUMN auth_provider DROP DEFAULT")
    op.execute("ALTER TYPE auth_provider RENAME TO auth_provider_old")
    op.execute("CREATE TYPE auth_provider AS ENUM ('local', 'google', 'github')")
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN auth_provider TYPE auth_provider
        USING auth_provider::text::auth_provider
        """
    )
    op.execute("ALTER TABLE users ALTER COLUMN auth_provider SET DEFAULT 'local'")
    op.execute("DROP TYPE auth_provider_old")


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN auth_provider DROP DEFAULT")
    op.execute("ALTER TYPE auth_provider RENAME TO auth_provider_old")
    op.execute("CREATE TYPE auth_provider AS ENUM ('local', 'google', 'github', 'microsoft')")
    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN auth_provider TYPE auth_provider
        USING auth_provider::text::auth_provider
        """
    )
    op.execute("ALTER TABLE users ALTER COLUMN auth_provider SET DEFAULT 'local'")
    op.execute("DROP TYPE auth_provider_old")
