import logging
import os
import secrets
import string
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import create_engine

from src.api_key_management.utilities import auth_api_key
from src.auth.users import current_active_org_user, current_active_user

log = logging.getLogger("uvicorn")


def are_credentials_valid(engine_url):
    """
    Check if the provided SQLAlchemy engine URL has valid credentials.

    :param engine_url: SQLAlchemy engine URL
    :return: True if credentials are valid, False otherwise
    """
    engine = create_engine(engine_url)
    try:
        # Try to connect to the database
        connection = engine.connect()
    except Exception as e:
        return False
    else:
        connection.close()
        return True


async def check(
    jwt_result=Depends(current_active_user),
    key_result=Depends(auth_api_key),
    jwt_org_result=Depends(current_active_org_user),
):
    if key_result:
        return key_result

    elif jwt_result:
        return jwt_result

    elif jwt_org_result:
        return jwt_org_result

    elif not (key_result or jwt_result or jwt_org_result):
        raise HTTPException(status_code=401, detail="Not authenticated")


def generate_random_string() -> str:
    """
    Generate a random string of a given length.

    :param length: Length of the random string to generate
    :return: Random string
    """
    return secrets.token_urlsafe(20)


def generate_org_id() -> str:
    """
    Generate a random number of length 11
    """
    return "".join(secrets.choice(string.digits) for _ in range(11))
