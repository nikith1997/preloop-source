"""Classes and methods to provide functionality to the team endpoint."""
import datetime
import logging
import uuid
from typing import Any, Dict, List, Optional

import jwt
from fastapi_users import exceptions
from fastapi_users.jwt import SecretType, decode_jwt, generate_jwt
from pydantic import ValidationError
from sqlalchemy import and_, create_engine, exc, func, funcfilter, or_, text

import src.team.models as team_models
from src import build_environment, common, constants, database, emailer, models
from src.auth.db import OrgUser, User

log = logging.getLogger("uvicorn")
TEAM_TOKEN_AUDIENCE = "preloop:team"
LOCAL_DEV_ENV_FLAG = build_environment.is_local_dev()

team_addition_verify_token: SecretType = (
    "94322fac0ed006aae41025d78fb65b0936a115493b112585e533326ac685f231"
)
team_addition_verify_token_lifetime_seconds: int = 86400
team_addition_verify_token_audience: str = TEAM_TOKEN_AUDIENCE


class InvalidTeamAdditionToken(exceptions.FastAPIUsersException):
    pass


class TeamCore:
    """
    This class encapsulates all the important logic required for the teams
    functionality that is provided by Preloop.
    """

    def __init__(self, user_id: uuid.UUID, org_id: uuid.UUID, role: str) -> None:
        """Initialize the TeamCore class."""
        self.user_id = user_id
        self.org_id = org_id
        self.role = role

    def create_team(self, team_name: str, team_description: str) -> str:
        """Create a team."""
        with database.Session.begin() as session:
            # see if team name exists in the org
            team_exists = (
                session.query(database.Team.id)
                .filter(
                    and_(
                        database.Team.team_name == team_name,
                        database.Organizations.org_id == self.org_id,
                    )
                )
                .count()
            )

            if team_exists > 0:
                raise ValueError(
                    "Your organization already has a team with that name. Please choose another name."
                )

            try:
                new_team = database.Team(
                    team_name=team_name,
                    team_description=team_description,
                    team_owner=self.user_id,
                    org_id=self.org_id,
                )
                session.add(new_team)
                session.flush()
                session.refresh(new_team)
                team_id = new_team.id

                team_owner = database.TeamMember(
                    team_id=team_id,
                    user_id=self.user_id,
                    team_role="owner",
                    is_accepted=True,
                )
                session.add(team_owner)
                return team_id

            except exc.SQLAlchemyError as e:
                raise ValueError(f"Team could not be created.")

            except ValidationError as e:
                raise ValueError(f"Team could not be created.")

    def list_teams(self, team_id: Optional[uuid.UUID] = None) -> List[Dict[Any, Any]]:
        """
        List all the teams that the user is a part of. In the case of a root user
        of an org, just list all the teams that exist in the org.
        """
        with database.Session.begin() as session:
            if self.role == "root":
                query_results = (
                    session.query(
                        database.Team.id,
                        database.Team.team_name,
                        database.Team.team_description,
                        database.Team.creation_date,
                        func.count(database.TeamMember.user_id).label("member_count"),
                    )
                    .join(
                        database.TeamMember,
                        database.Team.id == database.TeamMember.team_id,
                    )
                    .join(
                        database.AllUsers,
                        database.TeamMember.user_id == database.AllUsers.user_id,
                    )
                    .filter(database.Team.org_id == self.org_id)
                    .group_by(database.Team.id)
                    .all()
                )

                if not query_results:
                    return []

                teams_list = []
                for row in teams_list:
                    teams_list.append(
                        {
                            "team_id": row[0],
                            "team_name": row[1],
                            "team_description": row[2],
                            "creation_date": row[3],
                            "member_count": row[4],
                        }
                    )
                return teams_list

            else:
                if team_id is not None:
                    query_results = (
                        session.query(
                            database.Team.id,
                            database.Team.team_name,
                            database.Team.team_description,
                            database.Team.creation_date,
                            database.TeamMember.team_role,
                        )
                        .join(
                            database.TeamMember,
                            database.Team.id == database.TeamMember.team_id,
                        )
                        .join(
                            database.AllUsers,
                            database.TeamMember.user_id == database.AllUsers.user_id,
                        )
                        .filter(
                            and_(
                                database.TeamMember.user_id == self.user_id,
                                database.Team.id == team_id,
                            )
                        )
                        .all()
                    )
                    if len(query_results) == 0:
                        raise ValueError(f"Team ID {team_id} does not exist")
                else:
                    query_results = (
                        session.query(
                            database.Team.id,
                            database.Team.team_name,
                            database.Team.team_description,
                            database.Team.creation_date,
                            database.TeamMember.team_role,
                        )
                        .join(
                            database.TeamMember,
                            database.Team.id == database.TeamMember.team_id,
                        )
                        .join(
                            database.AllUsers,
                            database.TeamMember.user_id == database.AllUsers.user_id,
                        )
                        .filter(database.TeamMember.user_id == self.user_id)
                        .all()
                    )

                if not query_results:
                    return []

                teams_list = []

                for row in query_results:
                    teams_list.append(
                        {
                            "team_id": row[0],
                            "team_name": row[1],
                            "team_description": row[2],
                            "creation_date": row[3],
                            "team_role": row[4],
                        }
                    )

                return teams_list

    def create_team_verify_token(
        self, user_ids: List[uuid.UUID], team_id: uuid.UUID
    ) -> List[Dict[Any, Any]]:
        """Send an email to accept invitation to team."""
        with database.Session.begin() as session:
            for user_id in user_ids:
                user_search = (
                    session.query(database.AllUsers)
                    .filter(database.AllUsers.user_id == user_id)
                    .first()
                )

                if user_search is None:
                    raise ValueError("User not found.")

                if user_search.role == "org_user":
                    user = session.query(OrgUser).filter(OrgUser.id == user_id).first()
                    email = user.email.split(constants.ORG_ACCOUNT_SPLIT_TOKEN)[1]

                elif user_search.role == "root":
                    raise ValueError("Root user cannot be added to a team.")

                # get inviter name
                if self.role == "org_user":
                    inviter = (
                        session.query(OrgUser)
                        .filter(OrgUser.id == self.user_id)
                        .first()
                    )
                    inviter_first_name = inviter.first_name

                else:
                    inviter = (
                        session.query(User).filter(User.id == self.user_id).first()
                    )
                    inviter_first_name = inviter.first_name

                # get team name
                team_name = (
                    session.query(database.Team)
                    .filter(database.Team.id == team_id)
                    .first()
                    .team_name
                )

                if user.is_verified == False:
                    raise ValueError("User is not verified.")

                token_data = {
                    "sub": str(user.id),
                    "email": email,
                    "aud": team_addition_verify_token_audience,
                    "org_id": str(user.org_id),
                    "team_id": str(team_id),
                    "user_role": user.role,
                }

                token = generate_jwt(
                    token_data,
                    team_addition_verify_token,
                    team_addition_verify_token_lifetime_seconds,
                )

                if not LOCAL_DEV_ENV_FLAG:
                    user_first_name_invitee = user.first_name
                    user_first_name_inviter = inviter_first_name
                    team_name_email = team_name
                    verification_link = (
                        "https://www.preloop.com/verify-team/"
                        + "?user-type="
                        + str(user.role)
                        + "&token="
                        + token
                    )

                    email_props = models.AddedToTeam(
                        userFirstNameInvitee=user_first_name_invitee,
                        verificationLink=verification_link,
                        teamName=team_name_email,
                        userFirstNameInviter=user_first_name_inviter,
                    )

                    email_body = models.Email(
                        to=email,
                        from_="noreply@preloop.com",
                        emailType=models.EmailType.added_to_team,
                        emailProps=email_props,
                    )
                    response = emailer.send_email(email_body)

        return {"message": "Team invite sent."}

    def add_members_to_team(
        self, team_id: uuid.UUID, user_ids: List[uuid.UUID], role: str
    ) -> team_models.TeamMemberAddition:
        """Add members to a team.Only the team owner can add members to
        the team. If a team already has a member, than return an error.
        Additionally, if the team owner tries to add himself to the team,
        then return an error. Distinct error messages are returned for all
        specific occurrences of errors.
        """
        with database.Session.begin() as session:
            try:
                team_details = (
                    session.query(database.Team.team_owner)
                    .filter(database.Team.id == team_id)
                    .first()
                )

                if team_details is None:
                    raise ValueError("Team not found.")

                team_owner = team_details.team_owner

                if team_owner == self.user_id:

                    added_members = []
                    members_not_added = []

                    for user_add in user_ids:
                        try:
                            added_members.append(user_add)
                            new_member = database.TeamMember(
                                team_id=team_id,
                                user_id=user_add,
                                team_role=role,
                                is_accepted=False,
                            )
                            session.add(new_member)
                            added_members.append(user_add)

                        except:
                            members_not_added.append(user_add)
                            session.rollback()

                    if added_members == []:
                        added_members = None

                    if members_not_added == []:
                        members_not_added = None

                    if added_members is not None:
                        self.create_team_verify_token(added_members, team_id)

                    return team_models.TeamMemberAddition(
                        added_members=added_members, members_not_added=members_not_added
                    )

                else:
                    raise ValueError("Only the team owner can add members to the team.")

            except exc.SQLAlchemyError as e:
                raise ValueError("Team member(s) could not be added.")

            except ValidationError as e:
                raise ValueError("Team member(s) could not be added.")

    def remove_members_from_team(
        self, team_id: uuid.UUID, user_ids: List[uuid.UUID]
    ) -> team_models.TeamMemberRemoval:
        """Remove members from a team. Only the team owner can remove members
        from the team. If the team owner tries to remove himself from the team,
        then return an error. Distinct error messages are returned for all
        specific occurrences of errors.
        """
        with database.Session.begin() as session:
            removed_members = []
            members_not_removed = []

            try:
                team_owner = (
                    session.query(database.Team.team_owner)
                    .filter(database.Team.id == team_id)
                    .first()
                )

                if team_owner is None:
                    raise ValueError("Team not found.")

                elif team_owner[0] == self.user_id:
                    for user_remove in user_ids:
                        delete_count = (
                            session.query(database.TeamMember)
                            .filter(
                                database.TeamMember.team_id == team_id,
                                database.TeamMember.user_id == user_remove,
                            )
                            .delete()
                        )
                        if delete_count == 0:
                            members_not_removed.append(user_remove)

                        else:
                            removed_members.append(user_remove)

                        session.commit()
                    if removed_members == []:
                        removed_members = None

                    if members_not_removed == []:
                        members_not_removed = None

                    return team_models.TeamMemberRemoval(
                        removed_members=removed_members,
                        members_not_removed=members_not_removed,
                    )

                else:
                    raise ValueError(
                        "Only the team owner can remove members from the team."
                    )

            except exc.SQLAlchemyError as e:
                raise ValueError("Team member could not be removed.")

            except ValidationError as e:
                raise ValueError("Team member could not be removed.")

    def delete_team(self, team_id: uuid.UUID) -> None:
        """Delete a team. Once a team is deleted, clean up the team members
        table to remove all the members of this old team.
        """
        with database.Session.begin() as session:
            try:
                team_owner = (
                    session.query(database.Team.team_owner)
                    .filter(database.Team.id == team_id)
                    .first()
                )

                if team_owner is None or team_owner[0] != self.user_id:
                    if self.role != "root":
                        raise ValueError("Unauthorized.")

                session.query(database.TeamMember).filter(
                    database.TeamMember.team_id == team_id
                ).delete()

                session.query(database.Team).filter(
                    database.Team.id == team_id
                ).delete()

            except exc.SQLAlchemyError as e:
                log.error(str(e), exc_info=True)

            except ValidationError as e:
                log.error(str(e), exc_info=True)

    def modify_team(
        self, team_id: uuid.UUID, modify_params: team_models.TeamModify
    ) -> None:
        """Modify a team. Only the team owner can modify the team."""
        with database.Session.begin() as session:
            params_to_modify = modify_params.model_dump(exclude_none=True)

            if "team_name" in params_to_modify:
                team_exists = (
                    session.query(database.Team.id)
                    .filter(
                        and_(
                            database.Team.team_name == params_to_modify["team_name"],
                            database.TeamMember.user_id == self.user_id,
                            database.Team.org_id == self.org_id,
                        )
                    )
                    .count()
                )

                if team_exists > 0:
                    raise ValueError(
                        "Your organization already has a team with that name. Please choose another name."
                    )

            try:
                team_owner = (
                    session.query(database.Team.team_owner)
                    .filter(database.Team.id == team_id)
                    .first()
                )

                if team_owner is None or team_owner[0] != self.user_id:
                    if self.role != "root":
                        raise ValueError("Unauthorized.")

                session.query(database.Team).filter(database.Team.id == team_id).update(
                    params_to_modify
                )

            except exc.SQLAlchemyError as e:
                log.error(e, exc_info=True)
                raise ValueError("Team could not be modified.")

            except ValidationError as e:
                log.error(e, exc_info=True)
                raise ValueError("Team could not be modified.")

    def _get_user_ids_of_team_members_other_than_self(self):
        """Get user ids of all members of teams user is a part of."""
        with database.Session.begin() as session:
            team_ids = (
                session.query(database.Team.id)
                .join(
                    database.TeamMember, database.Team.id == database.TeamMember.team_id
                )
                .filter(database.TeamMember.user_id == self.user_id)
                .all()
            )

            team_ids = [team_id[0] for team_id in team_ids]

            if team_ids == []:
                return []

            team_names_and_user_ids = (
                session.query(database.Team.team_name, database.TeamMember.user_id)
                .join(
                    database.TeamMember, database.Team.id == database.TeamMember.team_id
                )
                .filter(
                    and_(
                        database.TeamMember.user_id != self.user_id,
                        database.TeamMember.team_id.in_(team_ids),
                    )
                )
                .all()
            )

            team_name_user_id_dict = {}
            for row in team_names_and_user_ids:
                if row[0] in team_name_user_id_dict:
                    team_name_user_id_dict[row[0]].append(row[1])

                else:
                    team_name_user_id_dict[row[0]] = [row[1]]

            return team_name_user_id_dict

    def get_shared_datasource_ids(self) -> Dict[str, List[uuid.UUID]]:
        """Get the ids of all datasources that are owned by user ids in the teams that the user is a
        part of, other than their own. Should return a dictionary of team name, and list of datasource ids
        that are part of the team."""
        with database.Session.begin() as session:
            team_name_user_id_dict = (
                self._get_user_ids_of_team_members_other_than_self()
            )
            team_name_datasource_id_dict = {}
            for team_name, user_ids in team_name_user_id_dict.items():
                datasource_ids = (
                    session.query(database.Datasource.id)
                    .filter(database.Datasource.user_id.in_(user_ids))
                    .all()
                )

                datasource_ids = [datasource_id[0] for datasource_id in datasource_ids]
                team_name_datasource_id_dict[team_name] = datasource_ids

            return team_name_datasource_id_dict

    def get_shared_feature_ids(self) -> Dict[str, List[uuid.UUID]]:
        """Get the ids of all features that are owned by user ids in the teams that the user is a
        part of, other than their own. Should return a dictionary of team name, and list of feature ids
        that are part of the team."""
        with database.Session.begin() as session:
            team_name_user_id_dict = (
                self._get_user_ids_of_team_members_other_than_self()
            )
            team_name_feature_id_dict = {}
            for team_name, user_ids in team_name_user_id_dict.items():
                feature_ids = (
                    session.query(database.Feature.id)
                    .filter(database.Feature.user_id.in_(user_ids))
                    .all()
                )

                feature_ids = [feature_id[0] for feature_id in feature_ids]
                team_name_feature_id_dict[team_name] = feature_ids

            return team_name_feature_id_dict

    def get_shared_ml_model_ids(self) -> Dict[str, List[uuid.UUID]]:
        """Get the ids of all ml models that are owned by user ids in the teams that the user is a
        part of, other than their own. Should return a dictionary of team name, and list of ml model ids
        that are part of the team."""
        with database.Session.begin() as session:
            team_name_user_id_dict = (
                self._get_user_ids_of_team_members_other_than_self()
            )
            team_name_ml_model_id_dict = {}
            for team_name, user_ids in team_name_user_id_dict.items():
                ml_model_ids = (
                    session.query(database.MLModel.id)
                    .filter(database.MLModel.user_id.in_(user_ids))
                    .all()
                )

                ml_model_ids = [ml_model_id[0] for ml_model_id in ml_model_ids]
                team_name_ml_model_id_dict[team_name] = ml_model_ids

            return team_name_ml_model_id_dict

    def get_team_details(self, team_id: uuid.UUID) -> Dict[str, Any]:
        """Get the details of a team."""
        with database.Session.begin() as session:
            is_team_member_or_owner = (
                session.query(database.TeamMember)
                .filter(
                    database.TeamMember.user_id == self.user_id,
                    database.TeamMember.team_id == team_id,
                )
                .count()
            )

            if is_team_member_or_owner == 0:
                if self.role != "root":
                    raise ValueError("You are not a member of this team.")

            team_details = (
                session.query(database.Team.team_name, database.Team.team_description)
                .filter(database.Team.id == team_id)
                .first()
            )

            if team_details is None:
                raise ValueError("Team not found.")

            team_name = team_details[0]
            team_description = team_details[1]

            team_members = (
                session.query(database.AllUsers.email, database.TeamMember.team_role)
                .join(
                    database.TeamMember,
                    database.AllUsers.user_id == database.TeamMember.user_id,
                )
                .filter(database.TeamMember.team_id == team_id)
                .all()
            )

            list_of_members = []

            for row in team_members:
                list_of_members.append(
                    {
                        "email": row[0].split(constants.ORG_ACCOUNT_SPLIT_TOKEN)[1],
                        "team_role": row[1],
                    }
                )

            return {
                "team_name": team_name,
                "team_description": team_description,
                "team_members": list_of_members,
            }

    def get_user_id_from_email(self, email_ids: List[str]) -> Dict[str, uuid.UUID]:
        """Get the user ids of the users who have the given emails."""
        with database.Session.begin() as session:
            simple_org_id = (
                session.query(database.Organizations.simple_org_id)
                .filter(database.Organizations.org_id == self.org_id)
                .first()
                .simple_org_id
            )
            full_email_ids = [
                simple_org_id + constants.ORG_ACCOUNT_SPLIT_TOKEN + email
                for email in email_ids
            ]
            user_ids = (
                session.query(database.AllUsers.user_id, database.AllUsers.email)
                .filter(
                    and_(
                        database.AllUsers.email.in_(full_email_ids),
                        database.AllUsers.org_id == self.org_id,
                    )
                )
                .all()
            )

            user_id_email_dict = {email: user_id for user_id, email in user_ids}

            return user_id_email_dict

    def list_org_users(self):
        """
        Grab the emails of all users in an organization.
        """
        with database.Session.begin() as session:
            user_emails = (
                session.query(database.AllUsers.email)
                .filter(
                    and_(
                        database.AllUsers.org_id == self.org_id,
                        database.AllUsers.role == "org_user",
                        database.AllUsers.user_id != self.user_id,
                    )
                )
                .all()
            )

            user_emails = [
                email[0].split(constants.ORG_ACCOUNT_SPLIT_TOKEN)[1]
                for email in user_emails
            ]

        return user_emails


def accept_team_invite(token: str) -> Dict[str, Any]:
    try:
        data = decode_jwt(
            token, team_addition_verify_token, [team_addition_verify_token_audience]
        )

    except jwt.PyJWTError:
        raise InvalidTeamAdditionToken()

    try:
        user_id = uuid.UUID(data["sub"])
        org_id = uuid.UUID(data["org_id"])
        team_id = uuid.UUID(data["team_id"])
        email = data["email"]
        role = data["user_role"]

    except KeyError:
        raise InvalidTeamAdditionToken()

    with database.Session.begin() as session:
        if role == "org_user":
            user = (
                session.query(database.OrgUser)
                .filter(
                    database.OrgUser.id == user_id, database.OrgUser.org_id == org_id
                )
                .first()
            )

        else:
            user = (
                session.query(database.User).filter(database.User.id == user_id).first()
            )

            # get the entry in the team table
            team_entry = (
                session.query(database.TeamMember)
                .filter(
                    database.TeamMember.team_id == team_id,
                    database.TeamMember.user_id == user_id,
                )
                .first()
            )

            if team_entry is None:
                raise ValueError("Team entry not found.")

            team_entry.is_accepted = True
            session.commit()

    return {"message": "Team invite accepted."}
