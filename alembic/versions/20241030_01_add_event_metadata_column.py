"""Add event_metadata column to audit_events."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "20241030_01"
down_revision = "295bf7fdb1f4"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return column_name in [column["name"] for column in inspector.get_columns(table_name)]


def upgrade() -> None:
    if not _column_exists("audit_events", "event_metadata"):
        op.add_column("audit_events", sa.Column("event_metadata", sa.JSON(), nullable=True))

    if _column_exists("audit_events", "metadata"):
        bind = op.get_bind()
        bind.execute(text("UPDATE audit_events SET event_metadata = metadata WHERE metadata IS NOT NULL"))


def downgrade() -> None:
    if _column_exists("audit_events", "event_metadata") and _column_exists("audit_events", "metadata"):
        bind = op.get_bind()
        bind.execute(text("UPDATE audit_events SET metadata = event_metadata WHERE event_metadata IS NOT NULL"))

    if _column_exists("audit_events", "event_metadata"):
        op.drop_column("audit_events", "event_metadata")
