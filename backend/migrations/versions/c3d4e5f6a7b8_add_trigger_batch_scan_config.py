"""add trigger batch scan config

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-01 19:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "relation_triggers",
        sa.Column("batch_scan_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "relation_triggers",
        sa.Column("batch_scan_cron", sa.String(length=100), nullable=True),
    )
    op.alter_column("relation_triggers", "batch_scan_enabled", server_default=None)


def downgrade():
    op.drop_column("relation_triggers", "batch_scan_cron")
    op.drop_column("relation_triggers", "batch_scan_enabled")
