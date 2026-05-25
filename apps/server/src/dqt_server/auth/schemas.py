from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserCreateAdmin(BaseModel):
    email: EmailStr
    name: str = ""
    password: str = ""
    role: str = "viewer"
    oncall_eligible: bool = False


class UserPatch(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    oncall_eligible: bool | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    tenant_id: str
    is_active: bool
    oncall_eligible: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPromote(BaseModel):
    role: str
