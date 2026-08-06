import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    org_id: uuid.UUID
    action_type: str
    target_resource: str | None
    policy_decision: str | None
    policy_id: uuid.UUID | None
    metadata: dict | None
    timestamp: datetime
