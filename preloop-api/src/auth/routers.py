import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from src.auth import db, models
from src.common import check as current_active_user
from src.constants import ORG_ACCOUNT_SPLIT_TOKEN
from src.database import AllUsers, Session

router = APIRouter()


@router.get(
    "/api/root-admin/list/org-users",
    status_code=status.HTTP_200_OK,
    response_model=models.AuthAPIGenericResponse,
)
async def list_org_users(user=Depends(current_active_user)):
    if user.role != "root":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to perform this action.",
        )

    org_id = user.org_id

    # Get session from async generator
    async_session = db.get_async_session()
    session = await async_session.__anext__()

    try:
        async with session.begin():
            org_users = await session.execute(
                select(db.OrgUser).where(db.OrgUser.org_id == org_id)
            )
            org_user_list = []
            for user in org_users.scalars():
                org_user_list.append(
                    {
                        "user_id": user.id,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email.split(ORG_ACCOUNT_SPLIT_TOKEN)[1],
                    }
                )

            return {"message": "Success", "details": org_user_list}
    finally:
        await session.close()


@router.delete(
    "/api/root-admin/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_org_user(user_id: str, user=Depends(current_active_user)):
    user_found = False

    if user.role != "root":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to perform this action.",
        )

    async_session = db.get_async_session()
    session = await async_session.__anext__()

    try:
        async with session.begin():
            user = await session.execute(
                select(db.OrgUser).where(db.OrgUser.id == user_id)
            )
            user = user.scalar()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
                )

            await session.delete(user)

            user_all_users = await session.execute(
                select(AllUsers).where(AllUsers.user_id == user_id)
            )
            user_all_users = user_all_users.scalar()

            await session.delete(user_all_users)
            return None
    finally:
        await session.close()
