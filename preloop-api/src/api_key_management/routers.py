from datetime import datetime
from enum import Enum
from typing import Annotated, Dict, List, Optional

from fastapi import APIRouter, Depends, Form, Header, HTTPException, status
from pydantic import BaseModel, Field, Json

from src.api_key_management.models import VerifyApiKeyRequest
from src.api_key_management.utilities import (
    Hasher,
    api_key_creation,
    api_key_deletion,
    api_key_list,
    api_key_verify,
)
from src.auth.db import OrgUser, User
from src.auth.users import current_active_user
from src.common import check
from src.database import ApiKeys, Session

router = APIRouter()


class APIPath(str, Enum):
    """
    The different API paths for the API Key API are defined in this enum.
    """

    API_KEY_CREATE = "/api/api-key/create"
    API_KEY_DELETE = "/api/api-key/delete"
    API_KEY_LIST = "/api/api-key/list"
    API_KEY_VERIFY = "/api/api-key/verify"


@router.post(APIPath.API_KEY_CREATE, status_code=status.HTTP_201_CREATED)
async def create_api_key(user: User | OrgUser = Depends(check)):
    """
    API endpoint to create a new API key for a given user.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user_id = str(user.id)
    org_id = str(user.org_id)
    role = user.role
    api_key = api_key_creation(user_id, org_id, role)

    return api_key


@router.post(APIPath.API_KEY_DELETE, status_code=status.HTTP_200_OK)
async def delete_api_key(
    key_id: Annotated[str, Form()], user: User | OrgUser = Depends(check)
) -> dict:
    """
    API endpoint to delete an API key for a given user.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user_id = str(user.id)
    api_key_deletion(user_id, key_id)

    return {"message": "API key deleted successfully."}


@router.get(APIPath.API_KEY_LIST, status_code=status.HTTP_200_OK)
async def list_api_keys(user: User | OrgUser = Depends(check)) -> list[dict]:
    """
    API endpoint to list all the API keys for a given user.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user_id = str(user.id)
    api_keys = api_key_list(user_id)

    return api_keys


@router.post(APIPath.API_KEY_VERIFY, status_code=status.HTTP_200_OK)
async def verify_api_key(
    request: VerifyApiKeyRequest,
    user=Depends(check),
) -> Dict[str, bool]:
    """
    API endpoint to verify if the key and secret are valid.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    result = api_key_verify(user, request.key_id, request.secret)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid key or secret"
        )
    return {"result": result}
