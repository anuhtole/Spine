import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from spine.db.base import Base
from spine.db.types import GUID


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    action_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    target_resource: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)

    policy_decision: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", sa.JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    sequence: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False, server_default="0", index=True)
    prev_hash: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    event_hash: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)
    timestamp: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
