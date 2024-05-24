from enum import Enum

from pydantic import BaseModel


class Visibility(Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class VerifyApiKeyRequest(BaseModel):
    """
    The request body for verifying an API key and secret.
    """

    key_id: str
    secret: str
