import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    agent_id: uuid.UUID
    goal: str = Field(..., min_length=1, max_length=4000)
    constraints: list[str] = Field(default_factory=list, max_length=64)
    expected_resources: list[str] = Field(default_factory=list, max_length=64)
    success_criteria: str | None = Field(default=None, max_length=4000)


class SessionResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    agent_id: uuid.UUID
    goal: str
    constraints: list[str]
    expected_resources: list[str]
    success_criteria: str | None
    status: str
    drift_score: float
    evaluation_count: int
    created_at: datetime
    ended_at: datetime | None


class SessionEndRequest(BaseModel):
    status: Literal["completed", "abandoned"] = "completed"


class SessionEndResponse(BaseModel):
    id: uuid.UUID
    status: str
    drift_score: float
    evaluation_count: int
    ended_at: datetime


class PlanEvaluationResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    audit_event_id: uuid.UUID
    agent_id: uuid.UUID
    org_id: uuid.UUID
    alignment: str
    confidence: float
    reasoning: str
    drift_contribution: float
    drift_score_after: float
    model_id: str
    approval_id: uuid.UUID | None
    created_at: datetime


class PlanVerdict(BaseModel):
    """Schema for the reviewer LLM's JSON response."""

    alignment: Literal["aligned", "drifted", "divergent"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1, max_length=2000)
    drift_contribution: float = Field(ge=0.0, le=1.0)
