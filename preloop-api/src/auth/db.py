import uuid
from typing import TYPE_CHECKING, AsyncGenerator, Generic

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from fastapi_users.models import ID
from fastapi_users_db_sqlalchemy.access_token import (
    SQLAlchemyAccessTokenDatabase,
    SQLAlchemyBaseAccessTokenTable,
    SQLAlchemyBaseAccessTokenTableUUID,
)
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import Column, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from src.config import settings_async
from src.constants import DB_NAMING_CONVENTION

DATABASE_URL = str(settings_async)


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    role = Column(String, nullable=False)
    org_id = Column(
        UUID(as_uuid=True), nullable=False, server_default=text("gen_random_uuid()")
    )
    org_name = Column(String, nullable=False)


class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, Base):
    pass


class OrgUser(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "org_user"

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    org_id = Column(UUID(as_uuid=True), nullable=False)
    org_name = Column(String, nullable=False)
    role = Column(String, nullable=False)


# customized SQLAlchemyBaseTokenTableUUID
class SQLAlchemyBaseAccessTokenTableUUIDOrg(SQLAlchemyBaseAccessTokenTable[uuid.UUID]):
    if TYPE_CHECKING:  # pragma: no cover
        user_id: uuid.UUID
    else:

        @declared_attr
        def user_id(cls) -> Mapped[GUID]:
            return mapped_column(
                GUID, ForeignKey("org_user.id", ondelete="cascade"), nullable=False
            )


class OrgAccessToken(SQLAlchemyBaseAccessTokenTableUUIDOrg, Base):
    __tablename__ = "orgaccesstoken"


engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


async def get_access_token_db(
    session: AsyncSession = Depends(get_async_session),
):
    yield SQLAlchemyAccessTokenDatabase(session, AccessToken)


async def get_org_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, OrgUser)


async def get_org_access_token_db(
    session: AsyncSession = Depends(get_async_session),
):
    yield SQLAlchemyAccessTokenDatabase(session, OrgAccessToken)
