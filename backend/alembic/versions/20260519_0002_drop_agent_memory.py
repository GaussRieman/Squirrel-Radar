"""drop agent_memory table

Revision ID: 20260519_0002
Revises: 20260518_0001
Create Date: 2026-05-19
"""

from alembic import op
from sqlalchemy import inspect as sa_inspect

revision = "20260519_0002"
down_revision = "20260518_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    if "agent_memory" in inspector.get_table_names():
        op.drop_table("agent_memory")


def downgrade() -> None:
    pass  # table was deleted by design, no restore needed
