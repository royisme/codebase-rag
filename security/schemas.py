"""认证与授权相关的 Pydantic 模型。"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi_users import schemas
from pydantic import BaseModel


class UserRead(schemas.BaseUser[uuid.UUID]):
    full_name: Optional[str] = None
    role: str


class UserCreate(schemas.BaseUserCreate):
    full_name: Optional[str] = None
    role: str = "viewer"


class UserUpdate(schemas.BaseUserUpdate):
    full_name: Optional[str] = None
    role: Optional[str] = None


class RoleSchema(BaseModel):
    name: str
    description: str
    permissions: list[str]


class PolicySchema(BaseModel):
    id: int
    subject: str
    domain: str
    resource: str
    action: str


class PolicyCreateRequest(BaseModel):
    subject: str
    domain: str
    resource: str
    action: str


class PolicyUpdateRequest(BaseModel):
    subject: Optional[str] = None
    domain: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
