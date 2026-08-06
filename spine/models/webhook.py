import secrets
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from spine.db.base import Base
from spine.db.types import GUID


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    url: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    # 32 bytes hex = 64 chars; used for HMAC-SHA256 of webhook body
    hmac_key: Mapped[str] = mapped_column(sa.String(64), nullable=False)

    name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    events: Mapped[list | None] = mapped_column(sa.JSON().with_variant(JSONB, "postgresql"), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, server_default=sa.true())
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    @staticmethod
    def new_hmac_key() -> str:
        return secrets.token_hex(32)
