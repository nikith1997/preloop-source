from fastapi import APIRouter, Body, Depends, HTTPException, status

from src.admin import models, utilities
from src.common import check as current_active_user
from src.constants import ORG_ACCOUNT_SPLIT_TOKEN

router = APIRouter()


@router.get(
    models.APIPaths.LIST_DATASOURCES,
    status_code=status.HTTP_200_OK,
    response_model=models.AdminAPIGenericResponse,
)
async def list_all_datasources(
    user=Depends(current_active_user), simple_org_id: str = Body(..., embed=True)
):
    """
    List all the datasources that are in a given organization.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    if user.role != "root":
        raise HTTPException(status_code=403, detail="User is not an admin")

    simple_org_id = simple_org_id
    admin = await utilities.AdminCore.initialize_admin_core(
        user_id, org_id, simple_org_id, role
    )
    datasources = admin.list_datasources()
    return {"message": "Datasources listed successfully.", "details": datasources}


@router.get(
    models.APIPaths.LIST_FEATURES,
    status_code=status.HTTP_200_OK,
    response_model=models.AdminAPIGenericResponse,
)
async def list_all_features(
    user=Depends(current_active_user), simple_org_id: str = Body(..., embed=True)
):
    """
    List all the features that are in a given organization.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    if user.role != "root":
        raise HTTPException(status_code=403, detail="User is not an admin")

    simple_org_id = simple_org_id
    admin = await utilities.AdminCore.initialize_admin_core(
        user_id, org_id, simple_org_id, role
    )
    features = admin.list_features()

    return {"message": "Features listed successfully.", "details": features}


@router.get(
    models.APIPaths.LIST_TEAMS,
    status_code=status.HTTP_200_OK,
    response_model=models.AdminAPIGenericResponse,
)
async def list_all_teams(
    user=Depends(current_active_user), simple_org_id: str = Body(..., embed=True)
):
    """
    List all the teams that exist under the admin's organization.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    if user.role != "root":
        raise HTTPException(status_code=403, detail="User is not an admin")

    simple_org_id = user.simple_org_id
    admin = await utilities.AdminCore.initialize_admin_core(
        user_id, org_id, simple_org_id, role
    )
    teams = admin.list_all_teams()

    return {"message": "Teams listed successfully.", "details": teams}


@router.get(
    models.APIPaths.LIST_TEAM_DETAILS,
    status_code=status.HTTP_200_OK,
    response_model=models.AdminAPIGenericResponse,
)
async def list_team_details(
    user=Depends(current_active_user),
    simple_org_id: str = Body(..., embed=True),
    team_id: str = Body(..., embed=True),
):
    """
    Provide additional details on the specific team id.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    if user.role != "root":
        raise HTTPException(status_code=403, detail="User is not an admin")

    admin = await utilities.AdminCore.initialize_admin_core(
        user_id, org_id, simple_org_id, role
    )
    team_details = admin.list_team_details(team_id)

    return {"message": "Team details listed successfully.", "details": team_details}
