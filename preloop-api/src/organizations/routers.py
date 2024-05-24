import uuid

import jwt
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi_users import exceptions
from fastapi_users.jwt import SecretType, decode_jwt, generate_jwt

import src.models as common_models
from src import build_environment, common, constants, database, emailer
from src.common import check as current_active_user
from src.organizations import models

router = APIRouter()
LOCAL_DEV_ENV_FLAG = build_environment.is_local_dev()

ORG_ACCOUNT_INVITE = "preloop:org-account-invite"
org_account_invite_token: SecretType = (
    "94322fac0ed006aae41025d78fb65b0936a115493b112585e533326ac685f231"
)
org_account_invite_token_lifetime_seconds: int = 86400
org_account_invite_token_audience: str = ORG_ACCOUNT_INVITE


class InvalidOrgAccountCreationToken(exceptions.FastAPIUsersException):
    pass


@router.post(
    models.APIPaths.ORG_ACCOUNT_CREATE_REQUEST,
    status_code=200,
    response_model=models.OrgAPIGenericResponse,
)
async def create_org_account_request(
    email: str = Body(..., embed=True), user=Depends(current_active_user)
):
    """Create an organization account request."""
    user_id = str(user.id)
    if user.role != "root":
        raise HTTPException(status_code=403, detail="User is not an admin")

    org_id = str(user.org_id)
    org_name = user.org_name
    first_name = user.first_name
    requesting_user_email = user.email

    with database.Session() as session:
        check_entry = org_id + constants.ORG_ACCOUNT_SPLIT_TOKEN + email
        is_exists = (
            session.query(database.AllUsers)
            .filter_by(email=check_entry, org_id=org_id)
            .first()
        )

        # get simple orgid
        simple_org_id = (
            session.query(database.Organizations.simple_org_id)
            .filter_by(org_id=org_id)
            .first()[0]
        )

    if is_exists:
        raise HTTPException(status_code=422, detail="User already exists")

    token_data = {
        "sub": user_id,
        "aud": org_account_invite_token_audience,
        "email": email,
        "org_id": org_id,
        "org_name": org_name,
        "first_name": first_name,
        "requesting_user_email": requesting_user_email,
        "simple_org_id": simple_org_id,
    }

    token = generate_jwt(
        token_data, org_account_invite_token, org_account_invite_token_lifetime_seconds
    )
    if not LOCAL_DEV_ENV_FLAG:
        org_account_creation = common_models.OrgAccountCreation(
            requestingUserFirstName=first_name,
            requestingUserEmail=user.email,
            registrationLink="https://www.preloop.com/register/invite/"
            + "?token="
            + token,
            organizationName=org_name,
        )

        email_model = common_models.Email(
            to=email,
            from_="noreply@preloop.com",
            emailType=common_models.EmailType.org_account_creation,
            emailProps=org_account_creation,
        )
        response = emailer.send_email(email_model)

    return {"message": "Invite successfully sent"}


@router.post(
    models.APIPaths.ORG_ACCOUNT_CREATE,
    status_code=200,
    response_model=models.OrgAPIGenericResponse,
)
async def create_org_account(token: str = Body(..., embed=True)):
    try:
        data = decode_jwt(
            token, org_account_invite_token, [org_account_invite_token_audience]
        )

    except jwt.PyJWTError:
        raise HTTPException(status_code=422, detail="Invalid token")

    try:
        email = data["email"]
        org_id = data["org_id"]
        org_name = data["org_name"]
        first_name = data["first_name"]
        simple_org_id = data["simple_org_id"]

    except KeyError:
        raise HTTPException(status_code=422, detail="Invalid token")

    with database.Session() as session:
        # check if account already exists
        check_entry = org_id + constants.ORG_ACCOUNT_SPLIT_TOKEN + email
        is_exists = (
            session.query(database.AllUsers)
            .filter_by(email=check_entry, org_id=org_id)
            .first()
        )
        if is_exists:
            raise HTTPException(status_code=422, detail="Invalid token")

    return {
        "message": "Invite Valid",
        "details": {
            "email": email,
            "org_id": org_id,
            "org_name": org_name,
            "first_name": first_name,
            "simple_org_id": simple_org_id,
        },
    }


@router.post(
    models.APIPaths.GET_SIMPLE_ORG_ID,
    status_code=200,
    response_model=models.OrgAPIGenericResponse,
)
async def get_simple_org_id(user=Depends(current_active_user)):
    with database.Session() as session:
        org_id = user.org_id
        simple_org_id = (
            session.query(database.Organizations.simple_org_id)
            .filter_by(org_id=org_id)
            .first()[0]
        )
    return {
        "message": "Success",
        "details": {"simple_org_id": simple_org_id, "org_id": org_id},
    }
