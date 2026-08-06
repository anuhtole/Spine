import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from spine.db.base import Base
from spine.db.types import GUID


class ApprovalGrant(Base):
    """One-time allow for a specific agent action after human approval."""

    __tablename__ = "approval_grants"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    approval_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    target_resource: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)
    match_key: Mapped[str] = mapped_column(sa.String(512), nullable=False, index=True)
    decided_by: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    expires_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    revoked_at: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
