import json
import uuid

from pydantic import BaseModel, Field, field_validator


class Correlation(BaseModel):
    # OpenTelemetry-style identifiers (optional)
    trace_id: str | None = Field(default=None, max_length=64)
    span_id: str | None = Field(default=None, max_length=32)
    request_id: str | None = Field(default=None, max_length=64)


class AgentAction(BaseModel):
    action_type: str = Field(..., min_length=1, max_length=100)
    target_resource: str | None = Field(default=None, max_length=2048)
    metadata: dict | None = None

    @field_validator("metadata")
    @classmethod
    def _limit_metadata_size(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        if len(value) > 64:
            raise ValueError("metadata may contain at most 64 keys")
        try:
            encoded = json.dumps(value, default=str)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must be JSON-serializable") from exc
        if len(encoded) > 8192:
            raise ValueError("metadata must be at most 8192 bytes when serialized")
        return value


class InterceptRequest(BaseModel):
    agent_id: uuid.UUID
    action: AgentAction
    correlation: Correlation | None = None
    session_id: uuid.UUID | None = None


class InterceptResponse(BaseModel):
    allowed: bool
    decision: str
    reason: str
    audit_event_id: uuid.UUID
    request_id: str
    approval_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    drift_score: float | None = None
