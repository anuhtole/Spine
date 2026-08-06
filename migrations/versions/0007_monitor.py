"""monitor: monitor_evaluations + agent_behavior_history

Revision ID: 0007_monitor
Revises: 0006_foreign_keys
Create Date: 2026-05-17
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_monitor"
down_revision = "0006_foreign_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monitor_evaluations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("audit_event_id", sa.String(length=36), nullable=False),
        sa.Column("monitor_type", sa.String(length=64), nullable=False, server_default="behavioral"),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_monitor_evaluations_org_id", "monitor_evaluations", ["org_id"])
    op.create_index("ix_monitor_evaluations_agent_id", "monitor_evaluations", ["agent_id"])
    op.create_index("ix_monitor_evaluations_audit_event_id", "monitor_evaluations", ["audit_event_id"])

    op.create_table(
        "agent_behavior_history",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("action_sequence", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("pattern_flags", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_agent_behavior_history_org_id", "agent_behavior_history", ["org_id"])
    op.create_index(
        "ux_agent_behavior_history_agent_id",
        "agent_behavior_history",
        ["agent_id"],
        unique=True,
    )

    op.create_foreign_key(
        "fk_monitor_evaluations_org_id",
        "monitor_evaluations",
        "organizations",
        ["org_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_monitor_evaluations_agent_id",
        "monitor_evaluations",
        "agents",
        ["agent_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_monitor_evaluations_audit_event_id",
        "monitor_evaluations",
        "audit_events",
        ["audit_event_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_monitor_evaluations_approval_id",
        "monitor_evaluations",
        "approvals",
        ["approval_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_agent_behavior_history_org_id",
        "agent_behavior_history",
        "organizations",
        ["org_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_agent_behavior_history_agent_id",
        "agent_behavior_history",
        "agents",
        ["agent_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_agent_behavior_history_agent_id", "agent_behavior_history", type_="foreignkey")
    op.drop_constraint("fk_agent_behavior_history_org_id", "agent_behavior_history", type_="foreignkey")
    op.drop_index("ux_agent_behavior_history_agent_id", table_name="agent_behavior_history")
    op.drop_index("ix_agent_behavior_history_org_id", table_name="agent_behavior_history")
    op.drop_table("agent_behavior_history")

    op.drop_constraint("fk_monitor_evaluations_approval_id", "monitor_evaluations", type_="foreignkey")
    op.drop_constraint("fk_monitor_evaluations_audit_event_id", "monitor_evaluations", type_="foreignkey")
    op.drop_constraint("fk_monitor_evaluations_agent_id", "monitor_evaluations", type_="foreignkey")
    op.drop_constraint("fk_monitor_evaluations_org_id", "monitor_evaluations", type_="foreignkey")
    op.drop_index("ix_monitor_evaluations_audit_event_id", table_name="monitor_evaluations")
    op.drop_index("ix_monitor_evaluations_agent_id", table_name="monitor_evaluations")
    op.drop_index("ix_monitor_evaluations_org_id", table_name="monitor_evaluations")
    op.drop_table("monitor_evaluations")
