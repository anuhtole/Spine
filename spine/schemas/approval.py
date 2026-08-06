import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from spine.schemas.intercept import InterceptRequest


class ApprovalCreate(BaseModel):
    # snapshot of a proposed action for human review
    agent_id: uuid.UUID
    proposed: InterceptRequest


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    agent_id: uuid.UUID
    status: str
    decision: str | None
    decided_by: str | None
    audit_event_id: uuid.UUID | None
    proposed: dict[str, Any]


class ApprovalDecision(BaseModel):
    action: Literal["approve", "reject"]
    decided_by: str = Field(..., min_length=1, max_length=255)
