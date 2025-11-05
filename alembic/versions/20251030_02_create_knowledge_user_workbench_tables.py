"""Create knowledge_queries and knowledge_notes tables

Revision ID: 20251030_02
Revises: 20241030_01
Create Date: 2025-10-30
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "20251030_02"
down_revision = "20241030_01"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return table_name in insp.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return any(idx.get("name") == index_name for idx in insp.get_indexes(table_name))


def upgrade() -> None:
    # knowledge_queries
    if not _table_exists("knowledge_queries"):
        op.create_table(
            "knowledge_queries",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=True),
            sa.Column("source_id", sa.String(length=36), sa.ForeignKey("knowledge_sources.id", ondelete="SET NULL"), nullable=True),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("answer_summary", sa.Text(), nullable=True),
            sa.Column("code_snippets", sa.JSON(), nullable=True),
            sa.Column("mode", sa.String(length=32), nullable=False, server_default="hybrid"),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="success"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _index_exists("knowledge_queries", "ix_knowledge_queries_source_created"):
        op.create_index(
            "ix_knowledge_queries_source_created",
            "knowledge_queries",
            ["source_id", "created_at"],
        )
    if not _index_exists("knowledge_queries", "ix_knowledge_queries_user_created"):
        op.create_index(
            "ix_knowledge_queries_user_created",
            "knowledge_queries",
            ["user_id", "created_at"],
        )

    # knowledge_notes
    if not _table_exists("knowledge_notes"):
        op.create_table(
            "knowledge_notes",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("source_id", sa.String(length=36), sa.ForeignKey("knowledge_sources.id", ondelete="SET NULL"), nullable=True),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("answer_summary", sa.Text(), nullable=False),
            sa.Column("code_snippets", sa.JSON(), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _index_exists("knowledge_notes", "ix_knowledge_notes_user"):
        op.create_index("ix_knowledge_notes_user", "knowledge_notes", ["user_id"])    


def downgrade() -> None:
    if _index_exists("knowledge_notes", "ix_knowledge_notes_user"):
        op.drop_index("ix_knowledge_notes_user", table_name="knowledge_notes")
    if _table_exists("knowledge_notes"):
        op.drop_table("knowledge_notes")
    if _index_exists("knowledge_queries", "ix_knowledge_queries_user_created"):
        op.drop_index("ix_knowledge_queries_user_created", table_name="knowledge_queries")
    if _index_exists("knowledge_queries", "ix_knowledge_queries_source_created"):
        op.drop_index("ix_knowledge_queries_source_created", table_name="knowledge_queries")
    if _table_exists("knowledge_queries"):
        op.drop_table("knowledge_queries")
