"""Create knowledge sources and parse jobs tables"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20241025_03"
down_revision = "20241025_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create knowledge_sources table
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),  # UUID as string for SQLite
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="other"),
        sa.Column("connection_config", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("sync_frequency_minutes", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create parse_jobs table
    op.create_table(
        "parse_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),  # UUID as string for SQLite
        sa.Column("knowledge_source_id", sa.String(length=36), sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("progress_percentage", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("items_processed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_items", sa.Integer(), nullable=True),
        sa.Column("job_config", sa.JSON(), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index("ix_knowledge_sources_name", "knowledge_sources", ["name"])
    op.create_index("ix_parse_jobs_status", "parse_jobs", ["status"])
    op.create_index("ix_parse_jobs_knowledge_source_id", "parse_jobs", ["knowledge_source_id"])


def downgrade() -> None:
    op.drop_index("ix_parse_jobs_knowledge_source_id", table_name="parse_jobs")
    op.drop_index("ix_parse_jobs_status", table_name="parse_jobs")
    op.drop_index("ix_knowledge_sources_name", table_name="knowledge_sources")
    op.drop_table("parse_jobs")
    op.drop_table("knowledge_sources")
