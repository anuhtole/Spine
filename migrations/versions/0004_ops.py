"""ops: webhooks + idempotency + approvals

Revision ID: 0004_ops
Revises: 0003_audit_hash_chain
Create Date: 2026-04-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_ops"
down_revision = "0003_audit_hash_chain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_idempotency_org", "idempotency_keys", ["org_id"])
    op.create_index(
        "ux_idempotency_unique",
        "idempotency_keys",
        ["org_id", "idempotency_key"],
        unique=True,
    )

    op.create_table(
        "webhooks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        # HMAC key material (treat as sensitive)
        sa.Column("hmac_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("events", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_webhooks_org_id", "webhooks", ["org_id"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("agent_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("proposed", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("decided_by", sa.String(length=255), nullable=True),
        sa.Column("audit_event_id", sa.String(length=36), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("approvals")
    op.drop_index("ix_webhooks_org_id", table_name="webhooks")
    op.drop_table("webhooks")
    op.drop_index("ux_idempotency_unique", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_org", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
