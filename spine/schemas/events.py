from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

SpineStreamEventType = Literal[
    "connected",
    "audit",
    "approval",
    "heartbeat",
    "plan_evaluation",
    "plan_drift",
]


class SpineStreamEvent(BaseModel):
    type: SpineStreamEventType
    org_id: uuid.UUID
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
