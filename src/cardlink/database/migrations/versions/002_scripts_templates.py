"""Add scripts and templates tables.

Revision ID: 002_scripts_templates
Revises: 001_initial
Create Date: 2024-01-15 00:00:00.000000

This migration adds tables for storing APDU scripts and templates:
- scripts: APDU scripts with commands and metadata
- templates: Parameterized script templates
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_scripts_templates"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create scripts and templates tables."""

    # =========================================================================
    # Scripts table
    # =========================================================================
    op.create_table(
        "scripts",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("commands", sa.JSON(), nullable=False, default=[]),
        sa.Column("tags", sa.JSON(), nullable=False, default=[]),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_index("idx_script_name", "scripts", ["name"])
    op.create_index("idx_script_created", "scripts", ["created_at"])
    op.create_index("idx_script_updated", "scripts", ["updated_at"])

    # =========================================================================
    # Templates table
    # =========================================================================
    op.create_table(
        "templates",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("commands", sa.JSON(), nullable=False, default=[]),
        sa.Column("parameters", sa.JSON(), nullable=False, default={}),
        sa.Column("tags", sa.JSON(), nullable=False, default=[]),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_index("idx_template_name", "templates", ["name"])
    op.create_index("idx_template_created", "templates", ["created_at"])
    op.create_index("idx_template_updated", "templates", ["updated_at"])


def downgrade() -> None:
    """Drop scripts and templates tables."""
    op.drop_table("templates")
    op.drop_table("scripts")
