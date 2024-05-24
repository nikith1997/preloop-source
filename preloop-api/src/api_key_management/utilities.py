"""
This module contains classes and methods that 
provide API key functionality to the Preloop API.
"""
import logging
import os
import secrets
import string
import uuid

from cryptography.fernet import Fernet
from fastapi import Header
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import and_

import src.api_key_management.models as models
from src.database import ApiKeys, Session

log = logging.getLogger("uvicorn")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserClass(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    role: str


class Hasher:
    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        return pwd_context.hash(password)


def generate_secrets():
    """
    This function generates an API key id and a secret.

    Inputs:
        None

    Return Dict:
        key_id (str): The key id of the API key.
        secret (str): The secret of the API key.
    """
    alphabet = string.ascii_letters + string.digits
    keys = {}
    keys["key_id"] = "".join(secrets.choice(alphabet) for i in range(15))
    keys["secret"] = "".join(secrets.choice(alphabet) for i in range(20))

    return keys


def api_key_creation(
    user_id: str,
    org_id: str,
    role: str,
    visibility: models.Visibility = models.Visibility.EXTERNAL,
):
    """
    This method creates a new API key for a given user.

    Inputs:
        user_id (str): The user id of the user for whom the API key is being created.
        org_id (str): The org id of the user for whom the API key is being created.
        role (str): The role of the user for whom the API key is being created.

    Returns:
        key_id (str): The key id of the API key.
        secret (str): The secret of the API key.
    """
    keys = generate_secrets()
    key_id = keys["key_id"]
    secret = keys["secret"]
    hashed_secret = Hasher.get_password_hash(secret)
    encrypted_secret = None

    if visibility == models.Visibility.INTERNAL:
        encryption_key = os.getenv("PRELOOP_API_KEY_INTERNAL_SECRET_ENCRYPTION_KEY")
        fernet_encrypter = Fernet(encryption_key)
        encrypted_secret = fernet_encrypter.encrypt(secret.encode())

    with Session.begin() as session:
        try:
            new_key = ApiKeys(
                user_id=user_id,
                key_id=key_id,
                org_id=org_id,
                role=role,
                hashed_secret=hashed_secret,
                visibility=visibility.value,
                encrypted_secret=encrypted_secret,
            )
            session.add(new_key)

        except Exception as e:
            raise Exception("Error inserting API key into database.")

    return keys


def api_key_deletion(user_id: str, key_id: str) -> None:
    """
    This method deletes an API key for a given user.

    Inputs:
        user_id (str): The user id of the user for whom the API key is being deleted.
        key_id (str): The key id of the API key to be deleted.

    Returns:
        None
    """
    with Session.begin() as session:
        try:
            session.query(ApiKeys).filter(
                and_(
                    ApiKeys.user_id == user_id,
                    ApiKeys.key_id == key_id,
                    ApiKeys.visibility == models.Visibility.EXTERNAL.value,
                )
            ).delete()
        except Exception as e:
            raise Exception("Error deleting API key from database.")

    return


def api_key_list(user_id: str) -> list[dict]:
    """
    Returns the list of currently active API keys for a given user.
    Only returns the key id and the creation date.
    """
    with Session.begin() as session:
        try:
            # query to return the creation date and key id for a given user
            api_keys = (
                session.query(ApiKeys.key_id, ApiKeys.creation_date)
                .filter(
                    ApiKeys.user_id == user_id,
                    ApiKeys.visibility == models.Visibility.EXTERNAL.value,
                )
                .all()
            )
            keys = [{"key_id": row[0], "creation_date": row[1]} for row in api_keys]

        except Exception as e:
            raise e

    return keys


def auth_api_key(secret: str = Header(None), key_id: str = Header(None)):
    """
    Function to get the user id from the API key.
    """
    if not secret or not key_id:
        return None

    with Session.begin() as session:
        try:
            result = session.query(ApiKeys).filter(ApiKeys.key_id == key_id).one()
            hashed_password = result.hashed_secret
            if Hasher().verify_password(secret, hashed_password):
                return UserClass(
                    id=result.user_id, org_id=result.org_id, role=result.role
                )
            else:
                return None
        except Exception as e:
            return None


def get_internal_api_key(user_id: uuid.UUID):
    with Session.begin() as session:
        try:
            api_key = (
                session.query(ApiKeys.key_id, ApiKeys.encrypted_secret)
                .filter(
                    ApiKeys.user_id == user_id,
                    ApiKeys.visibility == models.Visibility.INTERNAL.value,
                )
                .first()
            )
        except Exception as e:
            raise ValueError(str(e))
    try:
        encryption_key = os.getenv("PRELOOP_API_KEY_INTERNAL_SECRET_ENCRYPTION_KEY")
        fernet_decrypter = Fernet(encryption_key)
        decrypted_api_key = {
            "key_id": api_key[0],
            "secret": fernet_decrypter.decrypt(api_key[1]).decode(),
        }
        return decrypted_api_key
    except Exception as e:
        raise ValueError(str(e))


def api_key_verify(user: UserClass, key_id: str, secret: str):
    with Session.begin() as session:
        try:
            api_keys = (
                session.query(ApiKeys)
                .filter(
                    ApiKeys.org_id == user.org_id,
                    ApiKeys.visibility == models.Visibility.EXTERNAL.value,
                    ApiKeys.key_id == key_id,
                )
                .one()
            )
        except Exception as e:
            return False
    if Hasher().verify_password(secret, api_keys.hashed_secret):
        return True
    else:
        return False
