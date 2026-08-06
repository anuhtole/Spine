import uuid

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    agent_id: uuid.UUID | None = Field(default=None)
    name: str = Field(..., min_length=1, max_length=255)
    rule_type: str | None = Field(default=None, max_length=50)
    rule_config: dict = Field(default_factory=dict)
    compliance_framework: str | None = Field(default=None, max_length=50)


class PolicyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    rule_type: str | None = Field(default=None, max_length=50)
    rule_config: dict | None = Field(default=None)
    compliance_framework: str | None = Field(default=None, max_length=50)
    is_active: bool | None = Field(default=None)


class PolicyResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    agent_id: uuid.UUID | None
    name: str
    rule_type: str | None
    rule_config: dict
    compliance_framework: str | None
    is_active: bool
