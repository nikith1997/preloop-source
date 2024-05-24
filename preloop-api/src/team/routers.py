import logging
import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import exc

from src.common import check as current_active_user
from src.team import models, utilities

log = logging.getLogger("uvicorn")

router = APIRouter()


@router.post(
    models.APIPaths.TEAM_CREATE,
    status_code=status.HTTP_201_CREATED,
    response_model=models.TeamAPIGenericResponse,
)
async def create_team(
    team: models.TeamModel, user: uuid.UUID = Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    team_instance = utilities.TeamCore(user_id=user_id, org_id=org_id, role=role)
    try:
        team_id = team_instance.create_team(
            team_name=team.team_name, team_description=team.team_description
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    return {"message": "Team created successfully.", "details": {"team_id": team_id}}


@router.post(
    models.APIPaths.TEAM_LIST,
    status_code=status.HTTP_200_OK,
    response_model=models.TeamAPIGenericResponse,
)
async def list_teams(
    input: Optional[models.ListTeamsInput] = None,
    user: uuid.UUID = Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    team_instance = utilities.TeamCore(user_id=user_id, org_id=org_id, role=role)
    try:
        if input is None:
            team_list = team_instance.list_teams()
        else:
            team_list = team_instance.list_teams(input.team_id)
    except ValueError as value_error:
        raise HTTPException(status_code=422, detail=str(value_error))
    return {
        "message": "Team list retrieved successfully.",
        "details": {"team_list": team_list},
    }


@router.post(
    models.APIPaths.TEAM_DELETE,
    status_code=status.HTTP_200_OK,
    response_model=models.TeamAPIGenericResponse,
)
async def delete_team(
    input: models.TeamDeleteInput, user: uuid.UUID = Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    team_instance = utilities.TeamCore(user_id=user_id, org_id=org_id, role=role)
    try:
        team_instance.delete_team(team_id=input.team_id)
        return {
            "message": "Team deleted successfully.",
        }

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )


@router.post(
    models.APIPaths.TEAM_MODIFY,
    status_code=status.HTTP_200_OK,
    response_model=models.TeamAPIGenericResponse,
)
async def modify_team(
    team_id: Annotated[uuid.UUID, Body()],
    modify_params: models.TeamModify,
    user: uuid.UUID = Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    team_instance = utilities.TeamCore(user_id=user_id, org_id=org_id, role=role)
    try:
        team_instance.modify_team(team_id=team_id, modify_params=modify_params)
        return {"message": "Team modified successfully."}

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )


@router.post(
    models.APIPaths.TEAM_ADD_MEMBERS,
    status_code=status.HTTP_200_OK,
    response_model=models.TeamAPIGenericResponse,
)
async def add_members(
    team_members: models.CreateTeamInput, user: uuid.UUID = Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    team_instance = utilities.TeamCore(user_id=user_id, org_id=org_id, role=role)

    try:
        output = team_instance.add_members_to_team(
            team_id=team_members.team_id,
            user_ids=team_members.team_members,
            role="member",
        )
        if output.added_members == None:
            return {"message": "No members added to the team."}

        elif output.members_not_added == None:
            return {"message": "All members added to the team."}

        else:
            return {
                "message": "Some members added to the team.",
                "details": output.model_dump(),
            }

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )


@router.post(
    models.APIPaths.TEAM_REMOVE_MEMBERS,
    status_code=status.HTTP_200_OK,
    response_model=models.TeamAPIGenericResponse,
)
async def remove_members(
    team_members: models.CreateTeamInput, user: uuid.UUID = Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    team_instance = utilities.TeamCore(user_id=user_id, org_id=org_id, role=role)
    try:
        output = team_instance.remove_members_from_team(
            team_id=team_members.team_id, user_ids=team_members.team_members
        )

        if output.removed_members == None:
            return {"message": "No members removed from the team."}

        elif output.members_not_removed == None:
            return {"message": "All members removed from the team."}

        else:
            return {
                "message": "Some members removed from the team.",
                "details": output.model_dump(),
            }

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )


@router.post(
    models.APIPaths.TEAM_DETAILS,
    status_code=status.HTTP_200_OK,
    response_model=models.TeamAPIGenericResponse,
)
async def get_team_details(
    team_id: Annotated[uuid.UUID, Body()],
    user: uuid.UUID = Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    team_instance = utilities.TeamCore(user_id=user_id, org_id=org_id, role=role)
    try:
        team_details = team_instance.get_team_details(team_id=team_id)
        return {
            "message": "Team details retrieved successfully.",
            "details": team_details,
        }

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )


@router.post(
    models.APIPaths.USER_ID_FROM_EMAIL,
    status_code=status.HTTP_200_OK,
    response_model=models.TeamAPIGenericResponse,
)
async def get_user_id_from_email(
    emails: Annotated[List[str], Body()], user: uuid.UUID = Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    team_instance = utilities.TeamCore(user_id=user_id, org_id=org_id, role=role)
    try:
        user_ids = team_instance.get_user_id_from_email(email_ids=emails)
        return {"message": "User IDs retrieved successfully.", "details": user_ids}

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except exc.SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )


@router.post(
    models.APIPaths.ACCEPT_TEAM_INVITE,
    status_code=status.HTTP_200_OK,
    response_model=models.TeamAPIGenericResponse,
)
async def accept_team_invite(token: str = Body(..., embed=True)):
    try:
        result = utilities.accept_team_invite(token=token)
        return {"message": "Team invite accepted successfully."}

    except utilities.InvalidTeamAdditionToken:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid token."
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )


@router.get(
    models.APIPaths.LIST_ORG_USERS,
    status_code=status.HTTP_200_OK,
    response_model=models.TeamAPIGenericResponse,
)
async def list_org_users(user: uuid.UUID = Depends(current_active_user)):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    team_instance = utilities.TeamCore(user_id=user_id, org_id=org_id, role=role)

    try:
        result = team_instance.list_org_users()
        return {"message": "List of users retrieved successfully.", "details": result}

    except utilities.InvalidToken:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid token."
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0]
        )
