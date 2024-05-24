import uuid
from enum import Enum
from typing import Optional

from fastapi_users import schemas


class OrgRoles(str, Enum):
    ROOT = "root"
    ORG_USER = "org_user"


class UserRead(schemas.BaseUser[uuid.UUID]):
    first_name: str
    last_name: str
    country: str
    role: OrgRoles
    org_id: uuid.UUID
    org_name: str


class UserCreate(schemas.BaseUserCreate):
    first_name: str
    last_name: str
    country: str
    role: OrgRoles
    org_name: str


class UserUpdate(schemas.BaseUserUpdate):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    country: Optional[str] = None
    role: Optional[OrgRoles] = None
    org_name: Optional[str] = None


class OrgUserRead(schemas.BaseUser[uuid.UUID]):
    first_name: str
    last_name: str
    org_id: uuid.UUID
    org_name: str
    role: OrgRoles


class OrgUserCreate(schemas.BaseUserCreate):
    first_name: str
    last_name: str
    org_id: uuid.UUID
    org_name: str
    role: OrgRoles


class OrgUserUpdate(schemas.BaseUserUpdate):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    org_id: Optional[uuid.UUID] = None
    org_name: Optional[str] = None
    role: Optional[OrgRoles] = None
