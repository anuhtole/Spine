import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from spine.db.base import Base
from spine.db.types import GUID


class PlanEvaluation(Base):
    """One reviewer verdict for one (session, audit_event) pair.

    The reviewer is context-isolated: it sees only the session plan,
    the action_type+target_resource of the current event, and a summarized
    history of prior plan_evaluations in this session. It never sees the
    worker agent's prompts, tool outputs, or file contents.
    """

    __tablename__ = "plan_evaluations"
    __table_args__ = (sa.UniqueConstraint("session_id", "audit_event_id", name="uq_plan_eval_session_audit"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    audit_event_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)

    # aligned | drifted | divergent
    alignment: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(sa.Float(), nullable=False)
    reasoning: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    drift_contribution: Mapped[float] = mapped_column(sa.Float(), nullable=False)
    drift_score_after: Mapped[float] = mapped_column(sa.Float(), nullable=False, server_default="0.0")
    model_id: Mapped[str] = mapped_column(sa.String(128), nullable=False, server_default="")
    approval_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)

    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
