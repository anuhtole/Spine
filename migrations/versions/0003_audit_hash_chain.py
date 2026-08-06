"""audit hash chain

Revision ID: 0003_audit_hash_chain
Revises: 0002_api_keys
Create Date: 2026-04-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_audit_hash_chain"
down_revision = "0002_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_events", sa.Column("sequence", sa.BigInteger(), server_default="0", nullable=False))
    op.add_column("audit_events", sa.Column("prev_hash", sa.String(length=64), nullable=True))
    op.add_column("audit_events", sa.Column("event_hash", sa.String(length=64), nullable=True))

    op.create_index("ix_audit_events_sequence", "audit_events", ["sequence"])
    op.create_index("ix_audit_events_event_hash", "audit_events", ["event_hash"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_event_hash", table_name="audit_events")
    op.drop_index("ix_audit_events_sequence", table_name="audit_events")

    op.drop_column("audit_events", "event_hash")
    op.drop_column("audit_events", "prev_hash")
    op.drop_column("audit_events", "sequence")
