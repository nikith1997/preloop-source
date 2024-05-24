import logging
import uuid

from sqlalchemy import select

from src.constants import ORG_ACCOUNT_SPLIT_TOKEN
from src.database import AllUsers, Session
from src.team import utilities as team_utilities

log = logging.getLogger("uvicorn")


def get_org_users(org_id: uuid.UUID):
    with Session.begin() as session:
        org_users = session.execute(select(AllUsers).where(AllUsers.org_id == org_id))
        org_user_list = []
        for user in org_users.scalars():
            org_user_list.append(user.user_id)

        return org_user_list


def resolve_access(user_id: uuid.UUID, role: str, org_id: uuid.UUID):
    """
    The purpose of this function is to resolve access to
    other resources within the org, based on the type of user.
    """
    with Session.begin() as session:
        if role == "root":
            return get_org_users(org_id)

        elif role == "org_user":
            team = team_utilities.TeamCore(user_id, role, org_id)
            teams_and_users = team._get_user_ids_of_team_members_other_than_self()
            return_list = [user_id]
            if teams_and_users == []:
                return return_list

            for item in teams_and_users.values():
                if isinstance(item, list):
                    return_list.extend(
                        item
                    )  # if item is a list, extend/flatten it into return_list
                else:
                    return_list.append(item)

            return return_list
