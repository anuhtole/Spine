import uuid

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    framework: str | None = Field(default=None, max_length=50)


class AgentResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    framework: str | None
    is_active: bool
