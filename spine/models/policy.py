import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from spine.db.base import Base
from spine.db.types import GUID


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True, index=True)

    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    rule_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)

    rule_config: Mapped[dict] = mapped_column(sa.JSON().with_variant(JSONB, "postgresql"), nullable=False)
    compliance_framework: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)

    is_active: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, server_default=sa.true())
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
