"""add cmdb topology templates table

Revision ID: d9e8f7a6b5c4
Revises: c3d4e5f6a7b8
Create Date: 2026-04-13 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d9e8f7a6b5c4"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "cmdb_topology_templates" in inspector.get_table_names():
        return

    op.create_table(
        "cmdb_topology_templates",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("seed_models", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("traverse_direction", sa.String(length=16), nullable=False, server_default="both"),
        sa.Column("allowed_relation_types", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("visible_model_keys", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("layers", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("layout_direction", sa.String(length=16), nullable=False, server_default="horizontal"),
        sa.Column("group_by", sa.String(length=32), nullable=False, server_default="idc"),
        sa.Column("aggregate_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("aggregate_threshold", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cmdb_topology_templates_updated_at", "cmdb_topology_templates", ["updated_at"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "cmdb_topology_templates" not in inspector.get_table_names():
        return

    index_names = {idx["name"] for idx in inspector.get_indexes("cmdb_topology_templates")}
    if "ix_cmdb_topology_templates_updated_at" in index_names:
        op.drop_index("ix_cmdb_topology_templates_updated_at", table_name="cmdb_topology_templates")
    op.drop_table("cmdb_topology_templates")
