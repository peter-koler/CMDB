"""add notice rule ids to alert defines

Revision ID: b9d0e1f2a3b4
Revises: e8c1b2a3c4d5
Create Date: 2026-03-13 19:26:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b9d0e1f2a3b4"
down_revision = "e8c1b2a3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("alert_defines", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("notice_rule_ids_json", sa.Text(), nullable=False, server_default="[]")
        )
    op.execute(
        "UPDATE alert_defines SET notice_rule_ids_json = '[' || notice_rule_id || ']' "
        "WHERE notice_rule_id IS NOT NULL AND notice_rule_id > 0"
    )


def downgrade() -> None:
    with op.batch_alter_table("alert_defines", schema=None) as batch_op:
        batch_op.drop_column("notice_rule_ids_json")
