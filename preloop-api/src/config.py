import os

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings

from src.constants import Environment


class Config(BaseSettings):
    DATABASE_URL: PostgresDsn

    SITE_DOMAIN: str = "https://preloop.com/"

    ENVIRONMENT: Environment = Environment.PRODUCTION

    DATABASE_URL_ASYNC: PostgresDsn


settings = os.getenv("DATABASE_URL")
settings_async = os.getenv("DATABASE_URL_ASYNC")
preloop_datastore_url = os.getenv("PRELOOP_DATASTORE_URL")
