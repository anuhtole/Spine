import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class MemberCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")


class MemberUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|member|viewer)$")


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str
    role: str
    created_at: datetime
