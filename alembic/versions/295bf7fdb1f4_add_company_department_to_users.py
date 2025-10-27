"""add_company_department_to_users"""

from alembic import op
import sqlalchemy as sa


revision = "295bf7fdb1f4"
down_revision = "20241025_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("company", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("department", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "department")
    op.drop_column("users", "company")
