import io
import uuid
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import exc

from src.common import check as current_active_user
from src.datasource import models
from src.datasource.utilities import DataSourceCore

router = APIRouter()

# api routes


@router.post(models.APIPaths.DATASOURCE_CREATE, status_code=status.HTTP_201_CREATED)
async def create_datasource(
    request: models.CreateDatasourceRequest, user=Depends(current_active_user)
) -> models.CreationResponse:
    user_id = user.id
    org_id = user.org_id
    role = user.role

    # placeholder to remove once we set up auth
    dsc = DataSourceCore(user_id=user_id, org_id=org_id, role=role)

    try:
        creation_response = dsc.create_datasource(request)

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    except ValueError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    except exc.SQLAlchemyError as e:
        raise HTTPException(status_code=422, detail=e.args[0])
    except TypeError as e:
        raise HTTPException(status_code=422, detail=e.args[0])
    return models.CreationResponse(**creation_response)


@router.post(
    models.APIPaths.DATASOURCE_LIST,
    status_code=status.HTTP_200_OK,
    response_model=models.ListDatasourcesResult,
)
async def list_datasources(
    fields: Optional[models.DataSourceAPIGenericInput] = Body(default=None),
    user=Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    dsc = DataSourceCore(user_id=user_id, org_id=org_id, role=role)
    if fields is None:
        datasource_list = dsc.list_datasources()
        return models.ListDatasourcesResult(datasources=datasource_list)
    else:
        datasource_id = fields.datasource_id
        datasource_list = dsc.return_datasource_details(datasource_id=datasource_id)
        if datasource_list == []:
            raise HTTPException(status_code=404, detail="Datasource not found")

    return models.ListDatasourcesResult(datasources=datasource_list)


@router.post(
    models.APIPaths.DATASOURCE_DELETE,
    status_code=status.HTTP_200_OK,
    response_model=models.DataSourceAPIGenericResponse,
)
async def delete_datasource(
    fields: models.DataSourceAPIGenericInput, user=Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    dsc = DataSourceCore(user_id=user_id, org_id=org_id, role=role)
    try:
        dsc = dsc.delete_datasource(datasource_id=fields.datasource_id)
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail="Datasource not found")
    except AttributeError as e:
        raise HTTPException(status_code=422, detail="Datasource not found")

    except ValueError as e:
        if e.args[0] == "Datasource dependency detected":
            raise HTTPException(
                status_code=409, detail="Datasource is being used by a feature"
            )

    return models.DataSourceAPIGenericResponse(
        message="Datasource deleted successfully", details=None
    )


@router.post(
    models.APIPaths.DATASOURCE_MODIFY,
    status_code=status.HTTP_200_OK,
    response_model=models.DataSourceAPIGenericResponse,
)
async def modify_datasource(
    fields: models.DataSourceAPIGenericInput,
    modfield: models.ModificationField,
    user=Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    params_to_modify = modfield.model_dump()
    params_to_modify = {k: v for k, v in params_to_modify.items() if v is not None}

    dsc = DataSourceCore(user_id=user_id, org_id=org_id, role=role)
    try:
        dsc.modify_datasource(params_to_modify, fields.datasource_id)
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail="Datasource not found")

    except exc.NoSuchTableError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    except ValueError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    except ConnectionError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    return models.DataSourceAPIGenericResponse(
        message="Datasource modified successfully", details=None
    )


@router.post(models.APIPaths.DATASOURCE_CONNECT, status_code=status.HTTP_200_OK)
async def connect_to_datasource(
    connection_params: models.SQLConnectionParams,
    auth_params: models.SQLAuthParams,
    user=Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    connection_params_dict = connection_params.model_dump()

    auth_params_dict = auth_params.model_dump()
    dsc = DataSourceCore(user_id=user_id, org_id=org_id, role=role)

    try:
        schema_and_preview = dsc.connect_to_datasource(
            models.DataSourceType.POSTGRES.value,
            connection_params_dict,
            auth_params_dict,
        )
    except ConnectionError as e:
        if e.args[0] == "Connection failed":
            raise HTTPException(status_code=404, detail=e.args[0])
    except exc.NoSuchTableError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    return schema_and_preview


@router.get(models.APIPaths.DATASOURCE_GET, status_code=status.HTTP_200_OK)
async def get_datasource(
    details: models.DataSourceGet, user=Depends(current_active_user)
):
    """Return the datasource as a parquet file for further processing using FastAPI's FileResponse."""
    user_id = user.id
    org_id = user.org_id
    role = user.role

    dsc = DataSourceCore(user_id=user_id, org_id=org_id, role=role)

    details = details.model_dump()
    datasource_id = details["datasource_id"]
    try:
        datasource = dsc.get_datasource(datasource_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=e.args[0])
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail=e.args[0])
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    buffer = io.BytesIO()
    datasource.to_parquet(buffer)
    buffer.seek(0)

    def iter():
        while True:
            data = buffer.read(10000000)
            if not data:
                break
            yield data

    return StreamingResponse(iter(), media_type="application/octet-stream")


@router.post(
    models.APIPaths.DATASOURCE_GET_ID,
    status_code=status.HTTP_200_OK,
    response_model=models.DatasourceIDResponse,
)
async def get_datasource_id(
    inputs: models.DatasourceIDRequest, user=Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    datasource = DataSourceCore(user_id=user_id, org_id=org_id, role=role)
    try:
        datasource_id = datasource.get_datasource_id(
            datasource_name=inputs.datasource_name, name_type=inputs.name_type
        )
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"message": "success", "details": {"datasource_id": datasource_id}}
