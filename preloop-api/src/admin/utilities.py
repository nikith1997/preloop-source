from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, select

import src.admin.models as admin_models
from src import constants
from src.auth import db, models
from src.auth.routers import list_org_users
from src.database import (
    AllUsers,
    Datasource,
    Feature,
    MLModel,
    Session,
    Team,
    TeamMember,
)
from src.datasource import routers as datasource_routers
from src.feature import routers as feature_routers
from src.ml_model import routers as model_routers


class UserObject(BaseModel):
    """
    Simulated user object used to access the methods that are
    used by the various API endpoint methods.
    """

    id: UUID
    org_id: UUID
    role: str


class AdminCore:
    """
    This class encapsulates a number of functionalities
    that are relevant to functionality available to the
    root user. It extends a number of functions that already exist.
    """

    def __init__(
        self,
        user_id: str,
        org_id: str,
        role: str,
        simple_org_id: str,
        all_org_users: list[str],
    ) -> None:
        self.user_id = user_id
        self.org_id = org_id
        self.simple_org_id = simple_org_id
        self.role = role
        self.all_org_users = all_org_users

        if self.role != "root":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to perform this action.",
            )

    @classmethod
    async def initialize_admin_core(cls, user_id, org_id, simple_org_id, role):
        """
        This method initiales AdminCore class
        with the list of user ids of users who
        are part of the org.
        """
        user_object = UserObject(id=user_id, org_id=org_id, role=role)
        all_org_users = await list_org_users(user=user_object)
        all_org_users = all_org_users["details"]
        all_org_users = [user["user_id"] for user in all_org_users]
        return cls(user_id, org_id, role, simple_org_id, all_org_users)

    def list_datasources(self):
        """
        List all the datasources that are in a given organization.
        """
        with Session.begin() as session:
            results = (
                session.query(
                    Datasource, AllUsers.email, AllUsers.simple_org_id, AllUsers.role
                )
                .join(AllUsers)
                .filter(Datasource.user_id.in_(self.all_org_users))
                .all()
            )

            datasources = []
            for result in results:
                datasource, email, simple_org_id, role = result
                datasource_dict = {
                    key: getattr(datasource, key)
                    for key in datasource.__table__.columns.keys()
                    if not key.startswith("_sa_")
                }
                datasource_dict.update(
                    {
                        "email": email.split(constants.ORG_ACCOUNT_SPLIT_TOKEN)[1],
                        "simple_org_id": simple_org_id,
                        "role": role,
                    }
                )
                datasources.append(datasource_dict)

            return datasources

    def list_features(self):
        """
        List all the features that have been created in a given
        organization.
        """
        with Session.begin() as session:
            results = (
                session.query(
                    Feature, AllUsers.email, AllUsers.simple_org_id, AllUsers.role
                )
                .join(AllUsers)
                .filter(Feature.user_id.in_(self.all_org_users))
                .all()
            )

            features = []
            for result in results:
                feature, email, simple_org_id, role = result
                feature_dict = {
                    key: getattr(feature, key)
                    for key in feature.__table__.columns.keys()
                    if not key.startswith("_sa_")
                }
                feature_dict.update(
                    {
                        "email": email.split(constants.ORG_ACCOUNT_SPLIT_TOKEN)[1],
                        "simple_org_id": simple_org_id,
                        "role": role,
                    }
                )
                features.append(feature_dict)

            return features

    def list_all_teams(self):
        """
        List all the teams that exist under the admin's organization.
        """
        with Session.begin() as session:
            result = (
                session.query(
                    Team.id,
                    Team.name,
                    Team.description,
                    Team.creation_date,
                    AllUsers.email,
                )
                .join(AllUsers)
                .filter(
                    and_(Team.org_id == self.org_id, Team.user_id == AllUsers.user_id)
                )
                .all()
            )
            teams = []
            for team in teams:
                team_id, name, description, creation_date, email = team
                entry = {
                    "team_id": team_id,
                    "name": name,
                    "description": description,
                    "creation_date": creation_date,
                    "team_owner": email.split(constants.ORG_ACCOUNT_SPLIT_TOKEN)[1],
                }
                teams.append(entry)

            return teams

    def get_team_details(self, team_id: UUID):
        """
        Get details about a specific team.
        """
        with Session.begin() as session:
            team_details = (
                session.query(
                    Team.id,
                    Team.name,
                    Team.description,
                    Team.creation_date,
                    TeamMember.team_role,
                    TeamMember.member_from,
                    AllUsers.email,
                )
                .outerjoin(TeamMember)
                .join(AllUsers)
                .filter(
                    and_(
                        Team.id == team_id,
                        TeamMember.team_id == team_id,
                        TeamMember.user_id == AllUsers.user_id,
                    )
                )
                .all()
            )
            teams = []

            for team in team_details:
                (
                    team_id,
                    name,
                    description,
                    creation_date,
                    team_role,
                    member_from,
                    email,
                ) = team
                entry = {
                    "team_id": team.id,
                    "name": name,
                    "description": description,
                    "creation_date": creation_date,
                    "team_member_email": email.split(
                        constants.ORG_ACCOUNT_SPLIT_TOKEN[1]
                    ),
                    "team_role": team_role,
                    "member_from": member_from,
                }
                teams.append(entry)

            return teams

    def get_user_object(self, simple_org_id, email):
        """
        Get and return the user object for a given simple org id and email.
        This is important as an admin will need be able to run operations
        on any given user.
        """
        email = constants.ORG_ACCOUNT_SPLIT_TOKEN + email
        with Session.begin() as session:
            user = (
                session.query(AllUsers)
                .filter_by(simple_org_id=simple_org_id, email=email)
                .first()
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
                )
            user_object = UserObject(
                id=user.user_id, org_id=user.simple_org_id, role=user.role
            )

            return user_object

    def perform_user_operation(
        self, operation_type: admin_models.Operations, simple_org_id: str, email: str
    ):
        """
        Perform the given operation on a user that belongs to the
        organization that an administrator owns.
        """
        pass
        # TODO: Implement this function. Not a priority at the moment.
