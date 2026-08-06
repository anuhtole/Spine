"""monitor: unique evaluation per audit_event_id + monitor_type

Revision ID: 0008_monitor_multi_type
Revises: 0007_monitor
Create Date: 2026-05-17
"""

from alembic import op

revision = "0008_monitor_multi_type"
down_revision = "0007_monitor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ux_monitor_evaluations_audit_event_type",
        "monitor_evaluations",
        ["audit_event_id", "monitor_type"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_monitor_evaluations_audit_event_type", table_name="monitor_evaluations")
