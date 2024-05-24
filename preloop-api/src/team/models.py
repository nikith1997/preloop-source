import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class APIPaths(str, Enum):
    """
    The different API paths for the team API are defined in this
    enum. There are 5 main endpoints that all start with the parent
    word team:

    team/create: Used to create a new team.
    team/list: List all the teams that are available for a given account.
    team/describe: Used to describe a given team.
    team/delete: Used to delete a given team.
    team/modify: Used to modify a given team.
    """

    TEAM_CREATE = "/api/team/create"
    TEAM_LIST = "/api/team/list"
    TEAM_DELETE = "/api/team/delete"
    TEAM_MODIFY = "/api/team/modify"
    TEAM_ADD_MEMBERS = "/api/team-members/add"
    TEAM_REMOVE_MEMBERS = "/api/team-members/remove"
    TEAM_DETAILS = "/api/team/details"
    USER_ID_FROM_EMAIL = "/api/team/id-from-email"
    ACCEPT_TEAM_INVITE = "/api/team/accept-invite"
    LIST_ORG_USERS = "/api/team/list-org-users"


class TeamModel(BaseModel):
    team_name: str
    team_description: Optional[str] = None


class TeamModify(BaseModel):
    team_name: Optional[str] = None
    team_description: Optional[str] = None


class TeamMemberModel(BaseModel):
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    is_accepted: bool


class CreateTeamInput(BaseModel):
    team_id: uuid.UUID
    team_members: List[uuid.UUID]


class ListTeamsInput(BaseModel):
    team_id: uuid.UUID


class TeamAPIGenericResponse(BaseModel):
    message: str
    details: Optional[Dict[str, Any] | List[Any]] = None


class TeamMemberAddition(BaseModel):
    added_members: List[uuid.UUID] | None
    members_not_added: List[uuid.UUID] | None


class TeamMemberRemoval(BaseModel):
    removed_members: List[uuid.UUID] | None
    members_not_removed: List[uuid.UUID] | None


class TeamDeleteInput(BaseModel):
    team_id: uuid.UUID
