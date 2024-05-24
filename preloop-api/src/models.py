from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr


class EmailType(str, Enum):
    password_reset = "passwordReset"
    added_to_team = "addToTeamVerification"
    registered_user = "registeredUser"
    org_account_creation = "orgAccountCreation"
    verify_email = "emailVerification"


class PasswordReset(BaseModel):
    userFirstName: str
    resetPasswordLink: str


class AddedToTeam(BaseModel):
    userFirstNameInvitee: str
    verificationLink: str
    teamName: str
    userFirstNameInviter: str


class RegisteredUser(BaseModel):
    userFirstName: str


class OrgAccountCreation(BaseModel):
    requestingUserFirstName: str
    requestingUserEmail: str
    registrationLink: str
    organizationName: str


class VerifyEmail(BaseModel):
    userFirstName: str
    verificationLink: str
    verificationType: str
    organizationName: str


EmailProps = (
    PasswordReset | AddedToTeam | RegisteredUser | OrgAccountCreation | VerifyEmail
)


class Email(BaseModel):
    to: str
    from_: str
    emailType: EmailType
    emailProps: EmailProps
