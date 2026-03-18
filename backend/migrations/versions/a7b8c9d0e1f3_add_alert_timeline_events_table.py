"""add alert timeline events table

Revision ID: a7b8c9d0e1f3
Revises: f1a2b3c4d5e6
Create Date: 2026-03-15 11:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f3"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "alert_timeline_events" in set(inspector.get_table_names()):
        return

    op.create_table(
        "alert_timeline_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("operator", sa.String(length=100), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_alert_timeline_events_alert_id",
        "alert_timeline_events",
        ["alert_id"],
        unique=False,
    )
    op.create_index(
        "idx_alert_timeline_events_time",
        "alert_timeline_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "idx_alert_timeline_events_event",
        "alert_timeline_events",
        ["event_type"],
        unique=False,
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "alert_timeline_events" not in set(inspector.get_table_names()):
        return
    op.drop_index("idx_alert_timeline_events_event", table_name="alert_timeline_events")
    op.drop_index("idx_alert_timeline_events_time", table_name="alert_timeline_events")
    op.drop_index("idx_alert_timeline_events_alert_id", table_name="alert_timeline_events")
    op.drop_table("alert_timeline_events")
