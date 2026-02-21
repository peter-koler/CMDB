"""add trigger tables

Revision ID: d4e5f6g7h8i9
Revises: b3bf7a0c3253
Create Date: 2026-02-20 17:45:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6g7h8i9"
down_revision = "b3bf7a0c3253"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "trigger_execution_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trigger_id", sa.Integer(), nullable=False),
        sa.Column("source_ci_id", sa.Integer(), nullable=False),
        sa.Column("target_ci_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["trigger_id"], ["relation_triggers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_ci_id"], ["ci_instances.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_ci_id"], ["ci_instances.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_trigger_log_trigger_id", "trigger_execution_logs", ["trigger_id"]
    )
    op.create_index(
        "idx_trigger_log_created_at", "trigger_execution_logs", ["created_at"]
    )
    op.create_index("idx_trigger_log_status", "trigger_execution_logs", ["status"])

    op.create_table(
        "batch_scan_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("processed_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trigger_source", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["model_id"], ["cmdb_models.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_batch_scan_model_id", "batch_scan_tasks", ["model_id"])
    op.create_index("idx_batch_scan_status", "batch_scan_tasks", ["status"])
    op.create_index("idx_batch_scan_created_at", "batch_scan_tasks", ["created_at"])


def downgrade():
    op.drop_index("idx_batch_scan_created_at", "batch_scan_tasks")
    op.drop_index("idx_batch_scan_status", "batch_scan_tasks")
    op.drop_index("idx_batch_scan_model_id", "batch_scan_tasks")
    op.drop_table("batch_scan_tasks")

    op.drop_index("idx_trigger_log_status", "trigger_execution_logs")
    op.drop_index("idx_trigger_log_created_at", "trigger_execution_logs")
    op.drop_index("idx_trigger_log_trigger_id", "trigger_execution_logs")
    op.drop_table("trigger_execution_logs")
