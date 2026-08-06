"""policy_proposals: agent-authored allow-policies awaiting human review

Revision ID: 0012_policy_proposals
Revises: 0011_shadow_mode
Create Date: 2026-05-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_policy_proposals"
down_revision = "0011_shadow_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_index("ix_policy_proposals_status", table_name="policy_proposals")
    op.drop_index("ix_policy_proposals_org_id", table_name="policy_proposals")
    op.drop_table("policy_proposals")
