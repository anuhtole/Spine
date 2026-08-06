import hashlib
import hmac
import secrets
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from spine.db.base import Base
from spine.db.types import GUID


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    # Stored as hex sha256 of the raw key
    key_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True, index=True)

    name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    revoked_at: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    @staticmethod
    def new_raw_key(prefix: str = "spine_") -> str:
        return f"{prefix}{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_raw_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def constant_time_equals(a: str, b: str) -> bool:
        return hmac.compare_digest(a, b)
