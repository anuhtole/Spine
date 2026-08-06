"""simplify: drop monitor, behavior-history, policy-proposal tables + shadow columns

Removes the 8-behavioral-monitor system, shadow mode, and the policy-author
agent. After this, the only LLM call in Spine's request flow is the plan-bound
reviewer, and only when an intercept carries a session_id.

Revision ID: 0013_simplify_two_layer
Revises: 0012_policy_proposals
Create Date: 2026-06-22

Note: revision IDs must stay within 32 characters — Alembic stores them in
alembic_version.version_num, a VARCHAR(32). Postgres rejects anything longer;
SQLite silently accepts it, so tests will not catch an over-long ID.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_simplify_two_layer"
down_revision = "0012_policy_proposals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("policy_proposals")  # drops its indexes too
    op.drop_table("monitor_evaluations")  # drops its indexes + unique constraint
    op.drop_table("agent_behavior_history")
    op.drop_column("agents", "shadow_mode_override")
    op.drop_column("organizations", "shadow_mode_ends_at")
    op.drop_column("organizations", "shadow_mode")


def downgrade() -> None:
    # ── shadow columns (from 0011_shadow_mode) ──
    op.add_column(
        "organizations",
        sa.Column("shadow_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "organizations",
        sa.Column("shadow_mode_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column("shadow_mode_override", sa.Boolean(), nullable=True),
    )

    # ── agent_behavior_history (from 0007_monitor) ──
    op.create_table(
        "agent_behavior_history",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column(
            "action_sequence",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "pattern_flags",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
    )
    op.create_index("ix_agent_behavior_history_org_id", "agent_behavior_history", ["org_id"])
    op.create_index(
        "ux_agent_behavior_history_agent_id",
        "agent_behavior_history",
        ["agent_id"],
        unique=True,
    )

    # ── monitor_evaluations (from 0007_monitor + 0008 unique index) ──
    op.create_table(
        "monitor_evaluations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("audit_event_id", sa.String(length=36), nullable=False),
        sa.Column(
            "monitor_type",
            sa.String(length=64),
            nullable=False,
            server_default="behavioral",
        ),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["audit_event_id"], ["audit_events.id"]),
        sa.ForeignKeyConstraint(["approval_id"], ["approvals.id"]),
    )
    op.create_index("ix_monitor_evaluations_org_id", "monitor_evaluations", ["org_id"])
    op.create_index("ix_monitor_evaluations_agent_id", "monitor_evaluations", ["agent_id"])
    op.create_index("ix_monitor_evaluations_audit_event_id", "monitor_evaluations", ["audit_event_id"])
    op.create_index(
        "ux_monitor_evaluations_audit_event_type",
        "monitor_evaluations",
        ["audit_event_id", "monitor_type"],
        unique=True,
    )

    # ── policy_proposals (from 0012_policy_proposals) ──
    op.create_table(
        "policy_proposals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=True),
        sa.Column("rule_config", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("supporting_event_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("proposed_by_agent", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_policy_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_policy_proposals_org_id", "policy_proposals", ["org_id"])
    op.create_index("ix_policy_proposals_status", "policy_proposals", ["status"])
