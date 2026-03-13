"""add notice rule recipients and system channel

Revision ID: e8c1b2a3c4d5
Revises:
Create Date: 2026-03-13 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e8c1b2a3c4d5"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("notice_rules", schema=None) as batch_op:
        batch_op.add_column(sa.Column("recipient_type", sa.String(length=20), nullable=False, server_default="user"))
        batch_op.add_column(sa.Column("recipient_ids_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("include_sub_departments", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    with op.batch_alter_table("notice_rules", schema=None) as batch_op:
        batch_op.drop_column("include_sub_departments")
        batch_op.drop_column("recipient_ids_json")
        batch_op.drop_column("recipient_type")
