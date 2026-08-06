"""plan-bound monitoring: sessions + plan_evaluations + audit_events.session_id

Revision ID: 0010_plan_bound_monitoring
Revises: 0009_approval_grants
Create Date: 2026-05-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_plan_bound_monitoring"
down_revision = "0009_approval_grants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("expected_resources", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("success_criteria", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("drift_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("evaluation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sessions_org_id", "sessions", ["org_id"])
    op.create_index("ix_sessions_agent_id", "sessions", ["agent_id"])
    op.create_index("ix_sessions_status", "sessions", ["status"])

    op.create_table(
        "plan_evaluations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("audit_event_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("alignment", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("drift_contribution", sa.Float(), nullable=False),
        sa.Column("drift_score_after", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("model_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("approval_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("session_id", "audit_event_id", name="uq_plan_eval_session_audit"),
    )
    op.create_index("ix_plan_evaluations_session_id", "plan_evaluations", ["session_id"])
    op.create_index("ix_plan_evaluations_audit_event_id", "plan_evaluations", ["audit_event_id"])
    op.create_index("ix_plan_evaluations_org_id", "plan_evaluations", ["org_id"])
    op.create_index("ix_plan_evaluations_agent_id", "plan_evaluations", ["agent_id"])

    op.add_column("audit_events", sa.Column("session_id", sa.String(length=36), nullable=True))
    op.create_index("ix_audit_events_session_id", "audit_events", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_session_id", table_name="audit_events")
    op.drop_column("audit_events", "session_id")

    op.drop_index("ix_plan_evaluations_agent_id", table_name="plan_evaluations")
    op.drop_index("ix_plan_evaluations_org_id", table_name="plan_evaluations")
    op.drop_index("ix_plan_evaluations_audit_event_id", table_name="plan_evaluations")
    op.drop_index("ix_plan_evaluations_session_id", table_name="plan_evaluations")
    op.drop_table("plan_evaluations")

    op.drop_index("ix_sessions_status", table_name="sessions")
    op.drop_index("ix_sessions_agent_id", table_name="sessions")
    op.drop_index("ix_sessions_org_id", table_name="sessions")
    op.drop_table("sessions")
