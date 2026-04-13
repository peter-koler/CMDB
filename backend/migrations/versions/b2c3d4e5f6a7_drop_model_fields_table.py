"""drop model_fields table

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f3
Create Date: 2026-04-01 11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a7b8c9d0e1f3"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "model_fields" not in tables:
        return
    op.drop_table("model_fields")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "model_fields" in tables:
        return
    op.create_table(
        "model_fields",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("field_type", sa.String(length=50), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=True),
        sa.Column("is_unique", sa.Boolean(), nullable=True),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column("options", sa.Text(), nullable=True, server_default="[]"),
        sa.Column("validation_rules", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("reference_model_id", sa.Integer(), nullable=True),
        sa.Column("date_format", sa.String(length=50), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("config", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["model_id"], ["cmdb_models.id"]),
        sa.ForeignKeyConstraint(["reference_model_id"], ["cmdb_models.id"]),
        sa.ForeignKeyConstraint(["region_id"], ["model_regions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
