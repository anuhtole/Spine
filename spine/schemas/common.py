import uuid

from pydantic import BaseModel, Field


class UUIDResponse(BaseModel):
    id: uuid.UUID = Field(...)
