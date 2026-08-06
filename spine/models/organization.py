import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from spine.db.base import Base
from spine.db.types import GUID


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    plan: Mapped[str] = mapped_column(sa.String(50), nullable=False, server_default="starter")

    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
