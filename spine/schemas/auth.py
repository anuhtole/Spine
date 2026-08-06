import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserInfo(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    org_id: uuid.UUID
    org_name: str
    role: str


class LoginResponse(BaseModel):
    token: str
    user: UserInfo


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
