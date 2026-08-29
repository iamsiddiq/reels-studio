"""add progress_detail to source_videos

Revision ID: a1f3c9e7d2b4
Revises: d61bb4d9c965
Create Date: 2026-08-29 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1f3c9e7d2b4"
down_revision: Union[str, Sequence[str], None] = "d61bb4d9c965"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "source_videos",
        sa.Column("progress_detail", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("source_videos", "progress_detail")
