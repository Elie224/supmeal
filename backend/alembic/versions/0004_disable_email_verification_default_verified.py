"""Disable email verification by default

Revision ID: 0004_no_email_verify
Revises: 0003_rm_ms_authprov
Create Date: 2026-07-19 00:00:01

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_no_email_verify"
down_revision: Union[str, None] = "0003_rm_ms_authprov"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET is_verified = TRUE WHERE is_verified = FALSE")
    op.execute("ALTER TABLE users ALTER COLUMN is_verified SET DEFAULT TRUE")


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN is_verified SET DEFAULT FALSE")
