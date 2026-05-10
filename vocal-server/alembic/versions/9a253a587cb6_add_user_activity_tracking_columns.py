"""add user activity tracking columns

Revision ID: 9a253a587cb6
Revises: fd55a51eef83
Create Date: 2026-05-10 10:00:15.047547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a253a587cb6'
down_revision: Union[str, Sequence[str], None] = 'fd55a51eef83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('last_endpoint', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'last_endpoint')
    op.drop_column('users', 'last_seen_at')
