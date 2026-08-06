"""shadow mode: org + agent override toggles

Revision ID: 0011_shadow_mode
Revises: 0010_plan_bound_monitoring
Create Date: 2026-05-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_shadow_mode"
down_revision = "0010_plan_bound_monitoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Per-org shadow mode toggle + auto-flip timestamp
    op.add_column(
        "organizations",
        sa.Column("shadow_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "organizations",
        sa.Column("shadow_mode_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Per-agent override: NULL = inherit org, true/false = explicit
    op.add_column(
        "agents",
        sa.Column("shadow_mode_override", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agents", "shadow_mode_override")
    op.drop_column("organizations", "shadow_mode_ends_at")
    op.drop_column("organizations", "shadow_mode")
