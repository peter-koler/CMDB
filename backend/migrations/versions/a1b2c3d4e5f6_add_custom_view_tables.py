"""add custom view tables

Revision ID: a1b2c3d4e5f6
Revises: d4e5f6g7h8i9
Create Date: 2026-02-24 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "d4e5f6g7h8i9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "custom_views",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True, server_default="AppstoreOutlined"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("idx_custom_views_code", "custom_views", ["code"])
    op.create_index("idx_custom_views_active", "custom_views", ["is_active"])

    op.create_table(
        "custom_view_nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("view_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("filter_config", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["view_id"], ["custom_views.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["custom_view_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_custom_view_nodes_view", "custom_view_nodes", ["view_id"])
    op.create_index("idx_custom_view_nodes_parent", "custom_view_nodes", ["parent_id"])

    op.create_table(
        "custom_view_node_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["node_id"], ["custom_view_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id", "role_id", name="uq_node_role"),
    )
    op.create_index("idx_custom_view_node_permissions_node", "custom_view_node_permissions", ["node_id"])
    op.create_index("idx_custom_view_node_permissions_role", "custom_view_node_permissions", ["role_id"])


def downgrade():
    op.drop_index("idx_custom_view_node_permissions_role", "custom_view_node_permissions")
    op.drop_index("idx_custom_view_node_permissions_node", "custom_view_node_permissions")
    op.drop_table("custom_view_node_permissions")

    op.drop_index("idx_custom_view_nodes_parent", "custom_view_nodes")
    op.drop_index("idx_custom_view_nodes_view", "custom_view_nodes")
    op.drop_table("custom_view_nodes")

    op.drop_index("idx_custom_views_active", "custom_views")
    op.drop_index("idx_custom_views_code", "custom_views")
    op.drop_table("custom_views")
