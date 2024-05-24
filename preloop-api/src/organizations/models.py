from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class APIPaths(str, Enum):
    ORG_ACCOUNT_CREATE_REQUEST = "/api/organization-account/request"
    ORG_ACCOUNT_CREATE = "/api/organization-account/create"
    GET_SIMPLE_ORG_ID = "/api/organization-account/get-simple-org-id"


class OrgAPIGenericResponse(BaseModel):
    message: str
    details: Optional[Dict[str, Any]] = None
