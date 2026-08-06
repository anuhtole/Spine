import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from spine.db.base import Base
from spine.db.types import GUID


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    proposed: Mapped[dict] = mapped_column(sa.JSON().with_variant(JSONB, "postgresql"), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False, server_default="pending")
    decision: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    audit_event_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    decided_at: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
