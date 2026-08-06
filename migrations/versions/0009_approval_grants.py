"""approval_grants: allow retry after human approve

Revision ID: 0009_approval_grants
Revises: 0008_monitor_multi_type
Create Date: 2026-05-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_approval_grants"
down_revision = "0008_monitor_multi_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_grants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("target_resource", sa.Text(), nullable=True),
        sa.Column("match_key", sa.String(length=512), nullable=False),
        sa.Column("decided_by", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approval_grants_org_id", "approval_grants", ["org_id"])
    op.create_index("ix_approval_grants_agent_id", "approval_grants", ["agent_id"])
    op.create_index("ix_approval_grants_match_key", "approval_grants", ["match_key"])
    op.create_index("ix_approval_grants_expires_at", "approval_grants", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_approval_grants_expires_at", table_name="approval_grants")
    op.drop_index("ix_approval_grants_match_key", table_name="approval_grants")
    op.drop_index("ix_approval_grants_agent_id", table_name="approval_grants")
    op.drop_index("ix_approval_grants_org_id", table_name="approval_grants")
    op.drop_table("approval_grants")
