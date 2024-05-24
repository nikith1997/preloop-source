from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel


class Operations(str, Enum):
    DELETE_DATA_SOURCE = "delete_datasource"
    MODIFY_DATA_SOURCE = "modify_datasource"
    DELETE_FEATURE = "delete_feature"
    MODIFY_FEATURE = "modify_feature"
    DELETE_MODEL = "delete_model"
    MODIFY_MODEL = "modify_model"


class APIPaths(str, Enum):
    LIST_DATASOURCES = "/api/admin/list-datasources"
    LIST_FEATURES = "/api/admin/list-features"
    LIST_TEAMS = "/api/admin/list-teams"
    LIST_TEAM_DETAILS = "/api/admin/list-team-details"
    GET_USER_OBJECT = "/api/admin/get-user-object"


class AdminAPIGenericResponse(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | List[str] | None
