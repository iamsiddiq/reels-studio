"""initial

Revision ID: d61bb4d9c965
Revises:
Create Date: 2026-08-29 00:00:00.000000

NOTE: This migration was written by hand rather than generated via
`alembic revision --autogenerate`. The autogenerate command was run from
backend/ but could not reach a live Postgres instance matching
DATABASE_URL (postgresql://user:password@localhost:5432/shorts_reels_maker)
in this environment — a local Postgres server was running but rejected
those credentials (`password authentication failed for user "user"`).
The schema below was written to match app/models/ exactly (SourceVideo,
Clip, BRollAsset) and should be checked against a fresh
`alembic revision --autogenerate` once a real database is reachable.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d61bb4d9c965"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "source_videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_type",
            sa.Enum("youtube", "upload", name="sourcetype"),
            nullable=False,
        ),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "downloading",
                "processing",
                "completed",
                "failed",
                name="sourcevideostatus",
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("error_message", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_source_videos_id"), "source_videos", ["id"], unique=False
    )

    op.create_table(
        "clips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_video_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("video_path", sa.String(length=1024), nullable=False),
        sa.Column("caption_text", sa.Text(), nullable=True),
        sa.Column(
            "has_broll", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued", "processing", "completed", "failed", name="clipstatus"
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["source_video_id"], ["source_videos.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(op.f("ix_clips_id"), "clips", ["id"], unique=False)
    op.create_index(
        op.f("ix_clips_source_video_id"), "clips", ["source_video_id"], unique=False
    )

    op.create_table(
        "broll_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_broll_assets_id"), "broll_assets", ["id"], unique=False)
    op.create_index(
        op.f("ix_broll_assets_keyword"), "broll_assets", ["keyword"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_broll_assets_keyword"), table_name="broll_assets")
    op.drop_index(op.f("ix_broll_assets_id"), table_name="broll_assets")
    op.drop_table("broll_assets")

    op.drop_index(op.f("ix_clips_source_video_id"), table_name="clips")
    op.drop_index(op.f("ix_clips_id"), table_name="clips")
    op.drop_table("clips")

    op.drop_index(op.f("ix_source_videos_id"), table_name="source_videos")
    op.drop_table("source_videos")

    # Drop the Postgres ENUM types created implicitly by sa.Enum(...) above.
    postgresql.ENUM(name="clipstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="sourcevideostatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="sourcetype").drop(op.get_bind(), checkfirst=True)
