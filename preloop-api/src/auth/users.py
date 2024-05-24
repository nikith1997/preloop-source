import logging
import uuid
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport
from fastapi_users.authentication.strategy.db import (
    AccessTokenDatabase,
    DatabaseStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.schema import CreateSchema

from src import build_environment, common, constants, emailer, models
from src.api_key_management.models import Visibility
from src.api_key_management.utilities import api_key_creation
from src.auth.db import (
    AccessToken,
    OrgAccessToken,
    OrgUser,
    User,
    get_access_token_db,
    get_org_access_token_db,
    get_org_user_db,
    get_user_db,
)
from src.database import AllUsers, ApiKeys, Organizations, Session

log = logging.getLogger("uvicorn")

SECRET = "94322fac0ed006aae41025d78fb65b0936a115493b112585e533326ac685f231"
ORG_ACCOUNT_SPLIT = constants.ORG_ACCOUNT_SPLIT_TOKEN
LOCAL_DEV_ENV_FLAG = build_environment.is_local_dev()

# For org users, the simple organization id and the email are separated by a set of characters "##$#$$"


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        # Create feature schema for user for storing feature data
        with Session.begin() as connection:
            suffix = str(user.id).replace("-", "_")
            feature_schema = "features_" + suffix

            schemas = [feature_schema]
            for schema in schemas:
                connection.execute(CreateSchema(schema))

            # create entry in all users table
            simple_org_id = common.generate_org_id()

            user_entry = AllUsers(
                user_id=user.id,
                email=user.email,
                org_id=user.org_id,
                role=user.role,
                simple_org_id=simple_org_id,
            )
            connection.add(user_entry)

            # create organization entry
            org_entry = Organizations(
                org_id=user.org_id,
                org_name=user.org_name,
                org_owner=user.id,
                simple_org_id=simple_org_id,
            )
            connection.add(org_entry)

        # Create internal API keys for user
        api_key_creation(
            user_id=user.id,
            org_id=user.org_id,
            role=user.role,
            visibility=Visibility.INTERNAL,
        )

        if not LOCAL_DEV_ENV_FLAG:
            email_address = user.email

            # send the user a welcome email
            email_props = models.RegisteredUser(
                userFirstName=user.first_name,
            )
            email_body = models.Email(
                to=email_address,
                from_="noreply@preloop.com",
                emailType="registeredUser",
                emailProps=email_props,
            )
            response = emailer.send_email(email_body)

        return

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        if not LOCAL_DEV_ENV_FLAG:
            user_first_name = user.first_name
            verification_token = token
            url = (
                "https://www.preloop.com/reset-password/"
                + "?role=root"
                + "&token="
                + verification_token
            )
            email_props = models.PasswordReset(
                userFirstName=user_first_name,
                resetPasswordLink=url,
            )
            email_body = models.Email(
                to=user.email,
                from_="noreply@preloop.com",
                emailType="passwordReset",
                emailProps=email_props,
            )
            response = emailer.send_email(email_body)

        return

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        if not LOCAL_DEV_ENV_FLAG:
            email = user.email
            verification_token = token
            url = (
                "https://www.preloop.com/verify-email/"
                + "?role=root"
                + "&token="
                + verification_token
            )
            email_props = models.VerifyEmail(
                userFirstName=user.first_name,
                verificationLink=url,
                verificationType="root-account",
                organizationName=user.org_name,
            )
            email_body = models.Email(
                to=email,
                from_="noreply@preloop.com",
                emailType="emailVerification",
                emailProps=email_props,
            )
            response = emailer.send_email(email_body)

        return


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_database_strategy(
    access_token_db: AccessTokenDatabase[AccessToken] = Depends(get_access_token_db),
) -> DatabaseStrategy:
    return DatabaseStrategy(access_token_db, lifetime_seconds=1209600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_database_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(
    active=True, optional=True, verified=True
)


class OrgUserManager(UUIDIDMixin, BaseUserManager[OrgUser, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: OrgUser, request: Optional[Request] = None):

        # Create feature schema for user for storing feature data
        with Session.begin() as connection:
            simple_org_id = (
                connection.query(Organizations.simple_org_id, Organizations.org_id)
                .filter_by(org_id=user.org_id)
                .first()[0]
            )

            # create entry in all users table
            user_entry = AllUsers(
                user_id=user.id,
                email=user.email,
                org_id=user.org_id,
                role=user.role,
                simple_org_id=simple_org_id,
            )
            connection.add(user_entry)

        # Create internal API keys for user
        api_key_creation(
            user_id=user.id,
            org_id=user.org_id,
            role=user.role,
            visibility=Visibility.INTERNAL,
        )

    async def on_after_forgot_password(
        self, user: OrgUser, token: str, request: Optional[Request] = None
    ):
        if not LOCAL_DEV_ENV_FLAG:
            user_first_name = user.first_name
            verification_token = token
            url = (
                "https://www.preloop.com/reset-password/"
                + "?role=org"
                + "&token="
                + verification_token
            )
            email_props = models.PasswordReset(
                userFirstName=user_first_name,
                resetPasswordLink=url,
            )
            email_body = models.Email(
                to=user.email.split(ORG_ACCOUNT_SPLIT)[1],
                from_="noreply@preloop.com",
                emailType="passwordReset",
                emailProps=email_props,
            )
            response = emailer.send_email(email_body)

        return

    async def on_after_request_verify(
        self, user: OrgUser, token: str, request: Optional[Request] = None
    ):
        if not LOCAL_DEV_ENV_FLAG:
            email = user.email.split(ORG_ACCOUNT_SPLIT)[1]
            verification_token = token
            url = (
                "https://www.preloop.com/verify-email/"
                + "?role=org"
                + "&token="
                + verification_token
            )
            email_props = models.VerifyEmail(
                userFirstName=user.first_name,
                verificationLink=url,
                verificationType="org-account",
                organizationName=user.org_name,
            )
            email_body = models.Email(
                to=email,
                from_="noreply@preloop.com",
                emailType="emailVerification",
                emailProps=email_props,
            )
            response = emailer.send_email(email_body)

        return


async def get_org_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_org_user_db),
):
    yield OrgUserManager(user_db)


org_bearer_transport = BearerTransport(tokenUrl="org_auth/jwt/login")


def get_org_database_strategy(
    access_token_db: AccessTokenDatabase[OrgAccessToken] = Depends(
        get_org_access_token_db
    ),
) -> DatabaseStrategy:
    return DatabaseStrategy(access_token_db, lifetime_seconds=1209600)


org_auth_backend = AuthenticationBackend(
    name="jwt_org",
    transport=org_bearer_transport,
    get_strategy=get_org_database_strategy,
)

fastapi_org_users = FastAPIUsers[OrgUser, uuid.UUID](
    get_org_user_manager, [org_auth_backend]
)

current_active_org_user = fastapi_org_users.current_user(
    active=True, optional=True, verified=True
)
