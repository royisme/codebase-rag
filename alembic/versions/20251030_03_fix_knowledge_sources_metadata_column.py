"""Add source_metadata column to knowledge_sources and backfill from metadata if present.

Revision ID: 20251030_03
Revises: 20251030_02
Create Date: 2025-10-31
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = "20251030_03"
down_revision = "20251030_02"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return any(c.get("name") == column for c in insp.get_columns(table))


def upgrade() -> None:
    # Add source_metadata if missing
    if not _column_exists("knowledge_sources", "source_metadata"):
        op.add_column("knowledge_sources", sa.Column("source_metadata", sa.JSON(), nullable=True))

    # Backfill from legacy 'metadata' column if it exists
    if _column_exists("knowledge_sources", "metadata") and _column_exists("knowledge_sources", "source_metadata"):
        bind = op.get_bind()
        bind.execute(text("UPDATE knowledge_sources SET source_metadata = metadata WHERE metadata IS NOT NULL AND source_metadata IS NULL"))


def downgrade() -> None:
    # Only drop the new column; do not attempt to restore legacy data
    if _column_exists("knowledge_sources", "source_metadata"):
        op.drop_column("knowledge_sources", "source_metadata")
