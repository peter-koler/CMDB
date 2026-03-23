"""add escalation config to alert defines

Revision ID: f1a2b3c4d5e6
Revises: b9d0e1f2a3b4
Create Date: 2026-03-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "b9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("alert_defines")}
    if "escalation_config" in columns:
        return
    with op.batch_alter_table("alert_defines", schema=None) as batch_op:
        batch_op.add_column(sa.Column("escalation_config", sa.Text(), nullable=False, server_default=""))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("alert_defines")}
    if "escalation_config" not in columns:
        return
    with op.batch_alter_table("alert_defines", schema=None) as batch_op:
        batch_op.drop_column("escalation_config")
