"""add foreign key constraints to existing tables

Revision ID: 0006_foreign_keys
Revises: 0005_users
Create Date: 2026-05-14
"""

from alembic import op

revision = "0006_foreign_keys"
down_revision = "0005_users"
branch_labels = None
depends_on = None

_FKS = [
    ("agents", "org_id", "organizations", "id", "fk_agents_org_id"),
    ("policies", "org_id", "organizations", "id", "fk_policies_org_id"),
    ("policies", "agent_id", "agents", "id", "fk_policies_agent_id"),
    ("audit_events", "org_id", "organizations", "id", "fk_audit_events_org_id"),
    ("audit_events", "agent_id", "agents", "id", "fk_audit_events_agent_id"),
    ("audit_events", "policy_id", "policies", "id", "fk_audit_events_policy_id"),
    ("api_keys", "org_id", "organizations", "id", "fk_api_keys_org_id"),
    ("webhooks", "org_id", "organizations", "id", "fk_webhooks_org_id"),
    ("approvals", "org_id", "organizations", "id", "fk_approvals_org_id"),
    ("approvals", "agent_id", "agents", "id", "fk_approvals_agent_id"),
]


def upgrade() -> None:
    for table, col, ref_table, ref_col, name in _FKS:
        op.create_foreign_key(name, table, ref_table, [col], [ref_col])


def downgrade() -> None:
    for table, _col, _ref_table, _ref_col, name in reversed(_FKS):
        op.drop_constraint(name, table, type_="foreignkey")
