import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from spine.db.base import Base
from spine.db.types import GUID


class Session(Base):
    """An agent task session with a declared plan.

    Plan-bound monitoring: every intercept that carries a session_id is
    evaluated by the plan reviewer against the goal/constraints declared here.
    """

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    goal: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    constraints: Mapped[list] = mapped_column(
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="[]",
    )
    expected_resources: Mapped[list] = mapped_column(
        sa.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        server_default="[]",
    )
    success_criteria: Mapped[str | None] = mapped_column(sa.Text(), nullable=True)

    # active | completed | abandoned
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False, server_default="active", index=True)
    drift_score: Mapped[float] = mapped_column(sa.Float(), nullable=False, server_default="0.0")
    evaluation_count: Mapped[int] = mapped_column(sa.Integer(), nullable=False, server_default="0")

    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    ended_at: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
