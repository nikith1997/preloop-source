import uvicorn
from fastapi import Depends, FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.admin.routers import router as admin_router
from src.api_key_management.routers import router as api_key_router
from src.auth.routers import router as root_admin_router
from src.auth.schemas import (
    OrgUserCreate,
    OrgUserRead,
    OrgUserUpdate,
    UserCreate,
    UserRead,
    UserUpdate,
)
from src.auth.users import (
    auth_backend,
    fastapi_org_users,
    fastapi_users,
    org_auth_backend,
)
from src.datasource.routers import router as datasource_router
from src.feature.routers import router as feature_router
from src.ml_model.routers import router as ml_model_router
from src.organizations.routers import router as org_router
from src.team.routers import router as team_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasource_router, tags=["datasource"])
app.include_router(feature_router, tags=["feature"])
app.include_router(api_key_router, tags=["api_key"])
app.include_router(team_router, tags=["team"])
app.include_router(org_router, tags=["organizations"])
app.include_router(root_admin_router, tags=["root_admin"])
app.include_router(ml_model_router, tags=["ml_model"])
app.include_router(admin_router, tags=["root_admin"])

# authentication endpoints
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/api/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/api/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/api/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/api/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/api/users",
    tags=["users"],
)

# organization authentication endpoints
app.include_router(
    fastapi_org_users.get_auth_router(org_auth_backend),
    prefix="/api/org-auth",
    tags=["orgauth"],
)
app.include_router(
    fastapi_org_users.get_register_router(OrgUserRead, OrgUserCreate),
    prefix="/api/org-auth",
    tags=["orgauth"],
)
app.include_router(
    fastapi_org_users.get_reset_password_router(),
    prefix="/api/org-auth",
    tags=["orgauth"],
)
app.include_router(
    fastapi_org_users.get_verify_router(OrgUserRead),
    prefix="/api/org-auth",
    tags=["orgauth"],
)
app.include_router(
    fastapi_org_users.get_users_router(OrgUserRead, OrgUserUpdate),
    prefix="/api/org-users",
    tags=["orgusers"],
)
# at last, the bottom of the file/module
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5049)
