import hashlib
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from spine.db.base import Base
from spine.db.types import GUID


def fingerprint_json(obj: dict) -> str:
    # stable fingerprint for idempotency replay protection
    import json

    s = json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (sa.UniqueConstraint("org_id", "idempotency_key", name="ux_idempotency_unique"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)

    status_code: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    response_json: Mapped[dict] = mapped_column(sa.JSON(), nullable=False)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
