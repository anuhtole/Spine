import uuid

from pydantic import AnyHttpUrl, BaseModel, Field


class WebhookCreate(BaseModel):
    url: AnyHttpUrl
    name: str | None = Field(default=None, max_length=255)
    # Example: ["decision:blocked", "decision:flagged"] or empty for all
    events: list[str] | None = None


class WebhookResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    url: str
    name: str | None
    events: list[str] | None
    is_active: bool


class WebhookCreatedResponse(WebhookResponse):
    hmac_key: str
