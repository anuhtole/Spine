import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    plan: str | None = Field(default=None, max_length=50)


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    plan: str


class ApiKeyCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255)


class ApiKeyCreatedResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str | None
    raw_key: str


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str | None
    created_at: datetime
    revoked_at: datetime | None
    is_active: bool
