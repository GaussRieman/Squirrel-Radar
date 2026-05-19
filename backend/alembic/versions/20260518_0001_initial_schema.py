"""initial schema

Revision ID: 20260518_0001
Revises:
Create Date: 2026-05-18
"""

from alembic import op
import sqlalchemy as sa

revision = "20260518_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "indicator_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("interpretation", sa.Text(), nullable=False),
        sa.Column("risk_note", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_indicator_definitions_code", "indicator_definitions", ["code"])
    op.create_index("ix_indicator_definitions_category", "indicator_definitions", ["category"])

    op.create_table(
        "indicator_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("indicator_id", sa.Integer(), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("yoy", sa.Float(), nullable=True),
        sa.Column("mom", sa.Float(), nullable=True),
        sa.Column("trend_3m", sa.Float(), nullable=True),
        sa.Column("percentile_24m", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicator_definitions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("indicator_id", "month", name="uq_indicator_month"),
    )
    op.create_index("ix_indicator_data_month", "indicator_data", ["month"])

    op.create_table(
        "rule_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("matched", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id", "month", name="uq_rule_month"),
    )
    op.create_index("ix_rule_results_rule_id", "rule_results", ["rule_id"])
    op.create_index("ix_rule_results_month", "rule_results", ["month"])
    op.create_index("ix_rule_results_module", "rule_results", ["module"])

    op.create_table(
        "cycle_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("headline", sa.String(length=256), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("modules", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("watch_tasks", sa.JSON(), nullable=False),
        sa.Column("agent_brief", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("month"),
    )
    op.create_index("ix_cycle_snapshots_month", "cycle_snapshots", ["month"])


def downgrade() -> None:
    op.drop_index("ix_cycle_snapshots_month", table_name="cycle_snapshots")
    op.drop_table("cycle_snapshots")
    op.drop_index("ix_rule_results_module", table_name="rule_results")
    op.drop_index("ix_rule_results_month", table_name="rule_results")
    op.drop_index("ix_rule_results_rule_id", table_name="rule_results")
    op.drop_table("rule_results")
    op.drop_index("ix_indicator_data_month", table_name="indicator_data")
    op.drop_table("indicator_data")
    op.drop_index("ix_indicator_definitions_category", table_name="indicator_definitions")
    op.drop_index("ix_indicator_definitions_code", table_name="indicator_definitions")
    op.drop_table("indicator_definitions")
