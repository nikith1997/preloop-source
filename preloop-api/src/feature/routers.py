import logging
import uuid
from io import BytesIO
from typing import Annotated, Optional

import pandas as pd
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import and_, create_engine, exc

from src.auth.db import User
from src.common import check as current_active_user
from src.config import preloop_datastore_url
from src.database import Feature, FeatureVersions, Session
from src.datasource.models import CreateDatasourceRequest
from src.datasource.utilities import DataSourceCore
from src.feature import models
from src.feature.models import ExecutionType
from src.feature.utilities import FeatureCore

# For logging
log = logging.getLogger("uvicorn")

router = APIRouter()

# creation API, used to create a new feature
@router.post(
    models.APIPaths.FEATURE_CREATE,
    status_code=status.HTTP_201_CREATED,
    response_model=models.FeatureAPIGenericResponse,
)
async def create_feature(
    creationfields: models.Feature, user=Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    creationfields.user_id = user_id

    try:
        feature_details = feature.create_feature(creationfields)

    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    except ValueError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    except exc.SQLAlchemyError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    except Exception as e:
        log.error(str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=e.args[0])

    return {"message": "success", "details": feature_details}


@router.post(
    models.APIPaths.FEATURE_LIST,
    status_code=status.HTTP_200_OK,
    response_model=models.ListFeaturesResult,
)
async def list_features(
    fields: Optional[models.FeatureAPIGenericInput] = None,
    user=Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    try:
        if fields is None:
            list_of_features = feature.list_features()
        else:
            feature_id = fields.feature_id
            list_of_features = feature.return_feature_details(feature_id=feature_id)
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail=e.args[0])
    remove_params = [
        "user_id",
        "datasource_ids",
        "script_loc",
        "creation_method",
        "feature_dest",
        "location_string",
        "feature_signature",
    ]
    for feature in list_of_features:
        # set feature name, get datasource names, and drop unnecessary fields
        list_of_datasources = []
        for datasource_id in feature["datasource_ids"]:
            datasource = DataSourceCore(user_id=user_id)
            datasource_details = datasource.return_datasource_details(
                datasource_id=uuid.UUID(datasource_id)
            )[0]
            list_of_datasources.append(datasource_details["datasource_name"])

        feature["datasource_names"] = list_of_datasources

        for key in remove_params:
            feature.pop(key)
    return models.ListFeaturesResult(features=list_of_features)


@router.post(
    models.APIPaths.FEATURE_MODIFY,
    status_code=status.HTTP_200_OK,
    response_model=models.FeatureAPIGenericResponse,
)
async def modify_feature(
    request: models.ModifyFeatureRequest, user=Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature_id = request.feature_id
    params_to_modify = request.modifications.model_dump()
    params_to_modify = {k: v for k, v in params_to_modify.items() if v is not None}
    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    try:
        details = feature.modify_feature(params_to_modify, feature_id=feature_id)

    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    return {"message": "success", "details": details}


@router.post(
    models.APIPaths.FEATURE_DELETE,
    status_code=status.HTTP_200_OK,
    response_model=models.FeatureAPIGenericResponse,
)
async def delete_feature(
    fields: Optional[models.FeatureAPIGenericInput], user=Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature_id = fields.model_dump()["feature_id"]
    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    try:
        feature.delete_feature(feature_id=feature_id)
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail="Feature not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"message": "success", "details": None}


@router.post(
    models.APIPaths.FEATURE_INSERT,
    status_code=status.HTTP_201_CREATED,
    response_model=models.FeatureAPIGenericResponse,
)
async def insert_feature(
    feature_id: Annotated[str, Form()],
    operation_type: Annotated[str, Form()],
    data: Annotated[UploadFile, Form()],
    user=Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature_details = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    try:
        feature_details = feature_details.return_feature_details(feature_id=feature_id)

    except exc.NoResultFound as e:
        raise HTTPException(
            status_code=422, detail=f"The feature with id {feature_id} does not exist"
        )

    except Exception as e:
        log.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    location_string = feature_details[0]["location_string"]
    version = 1
    if feature_details[0]["versioning"] is True or (
        feature_details[0]["versioning"] is False
        and operation_type == ExecutionType.FIRST_RUN.value
    ):
        if operation_type == ExecutionType.FIRST_RUN.value:
            version = 1
        else:
            version = feature_details[0]["latest_version"] + 1

        # update the feature version table with the newest version
        with Session.begin() as session:
            session.add(FeatureVersions(feature_id=feature_id, version=version))

            row_to_modify = (
                session.query(Feature)
                .filter(
                    and_(Feature.id == feature_details[0]["id"]),
                    and_(Feature.user_id == user_id),
                )
                .one()
            )

            row_to_modify.latest_version = version
    data = await data.read()
    buffer = BytesIO(data)
    data = pd.read_parquet(buffer)

    # write this to the datastore
    engine = create_engine(preloop_datastore_url)
    schema = location_string.split(".")[0]
    table_name = location_string.split(".")[1]

    data["__preloop_version"] = version

    try:
        if feature_details[0]["versioning"] is True:
            data.to_sql(
                name=table_name,
                con=engine,
                schema=schema,
                chunksize=10000,
                if_exists="append",
                index=True,
            )
        else:
            data.to_sql(
                name=table_name,
                con=engine,
                schema=schema,
                chunksize=10000,
                if_exists="replace",
                index=True,
            )
    except exc.ProgrammingError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    return {"message": "success", "details": [{"latest_version": version}]}


@router.post(models.APIPaths.FEATURE_GET, status_code=status.HTTP_200_OK)
async def get_feature(
    fields: models.FeatureAPIGenericInput, user=Depends(current_active_user)
):

    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature_id = fields.feature_id
    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    try:
        feature_details = feature.return_feature_details(feature_id=feature_id)
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail=e.args[0])
    if fields.version is None:
        version = feature_details[0]["latest_version"]
    else:
        version = fields.version
    verify_check = feature.check_valid_get_feature_request(
        feature_id=feature_id, version=version
    )
    if verify_check == False:
        raise HTTPException(
            status_code=422, detail="Feature not found or Version does not exist"
        )
    location_string = feature_details[0]["location_string"]
    engine = create_engine(preloop_datastore_url)
    schema = location_string.split(".")[0]
    table_name = location_string.split(".")[1]
    query = f'SELECT * FROM "{schema}"."{table_name}" WHERE __preloop_version={version}'
    data = pd.read_sql(query, engine)
    data.set_index(feature_details[0]["id_cols"], inplace=True)
    data.drop(columns=["__preloop_version"], inplace=True)

    buffer = BytesIO()
    data.to_parquet(buffer)
    buffer.seek(0)

    def iter():
        while True:
            data = buffer.read(10000000)
            if not data:
                break
            yield data

    return StreamingResponse(iter(), media_type="application/octet-stream")


@router.post(models.APIPaths.FEATURE_EXPERIMENTAL_GET, status_code=status.HTTP_200_OK)
async def experiment_get_feature(
    input: models.ExperimentFeatureGetRequest, user=Depends(current_active_user)
):
    body = input.feature_signature
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)

    result = feature.signature_search(body)

    if result is None:
        raise HTTPException(status_code=404, detail="Feature not found")

    if input.version is None:
        version = result["latest_version"]
    else:
        version = result["latest_version"]
    location_string = result["location_string"]
    schema = location_string.split(".")[0]
    table_name = location_string.split(".")[1]
    engine = create_engine(preloop_datastore_url)
    query = f"SELECT * FROM {schema}.{table_name} WHERE __preloop_version={version}"
    data = pd.read_sql(query, engine)

    data.drop(columns=["__preloop_version"], inplace=True)

    buffer = BytesIO()
    data.to_parquet(buffer)
    buffer.seek(0)

    def iter():
        while True:
            data = buffer.read(10000000)
            if not data:
                break
            yield data

    response = StreamingResponse(iter(), media_type="application/octet-stream")
    response.headers["feature-name"] = result["feature_name"]
    return response


@router.post(
    models.APIPaths.FEATURE_EXPERIMENTAL_CREATE, status_code=status.HTTP_201_CREATED
)
async def experimental_create_feature(
    input: models.ExperimentalFeatureCreateRequest, user=Depends(current_active_user)
):
    """
    This endpoint is used to create a new feature using the experimental feature
    creation method, also known as Parser. Parser creates a feature signature,
    and this signature is used to create all datasources and the feature in Preloop.
    Current functionality expects all datasources to have unique names, even if they
    are dupicative in nature. However, in the future, we'll have built in function to
    dedupe datasources and only ensure that one datasource is created for each unique
    signature. Same goes with features as well.

    The process of creating a feature consists of the following steps:

    1. Create all the datasources. If a datasource name already exists, then raise and error.
    2. Create the feature from the signature.

    Inputs:
        feature_signature (JSON): The signature of the feature to be created.

    Returns:
        200, {“message”: “success”, “details”: {“feature_name”: “name of feature”}
        Error codes if something goes wrong
    """
    body = models.ExperimentalGetFeatureInput.model_validate(input.feature_signature)
    user_id = user.id
    org_id = user.org_id
    role = user.role

    execution_id = input.execution_id
    signature = input.feature_signature
    datasource = DataSourceCore(user_id=user_id, org_id=org_id, role=role)
    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)

    datasource_names = []
    existing_datasource_ids = []
    created_datasource_ids = []

    for ds in signature["datasources"]:
        datasource_names.append(ds["name"])
        if ds["existing"] == True:
            datasource_id = datasource.get_datasource_id(ds["name"])
            existing_datasource_ids.append(datasource_id)
            continue

        try:
            datasource_object = CreateDatasourceRequest(
                user_id=user_id,
                datasource_name=ds["name"],
                datasource_type=ds["type"],
                connection_details=ds["connection_details"],
                execution_id=execution_id,
            )

            new_datasource_id = datasource.create_datasource(datasource_object)
            created_datasource_ids.append(new_datasource_id)

        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())

        except ValueError as e:
            raise HTTPException(status_code=422, detail=e.args[0])

        except exc.SQLAlchemyError as e:
            raise HTTPException(status_code=422, detail=e.args[0])

    try:
        feature_signature_subset = signature["feature"]

        # variables to create
        column_types = {}
        feature_cols = []
        id_cols = []
        target_cols = []

        for column in feature_signature_subset["columns"]:
            if column["type"] == "feature":
                feature_cols.append(column["name"])
                column_types[column["name"]] = column["data_type"]

            elif column["type"] == "id":
                id_cols.append(column["name"])
                column_types[column["name"]] = column["data_type"]

            else:
                target_cols.append(column["name"])
                column_types[column["name"]] = column["data_type"]

        feature_creation_input = models.Feature(
            user_id=user_id,
            feature_name=feature_signature_subset["name"],
            datasource_names=datasource_names,
            column_types=column_types,
            feature_dest=input.feature_dest,
            id_cols=id_cols,
            feature_cols=feature_cols,
            feature_signature=input.feature_signature,
            creation_method="parser",
            latest_version=1,
            script_loc=input.script_loc,
            execution_id=execution_id,
            scheduling_expression_string=input.scheduling_expression,
            versioning=input.versioning,
            feature_drift_enabled=input.feature_drift_enabled,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        feature_details = feature.create_feature(feature_creation_input)

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    except ValueError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    except exc.SQLAlchemyError as e:
        raise HTTPException(status_code=422, detail=e.args[0])

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return {
        "message": "success",
        "details": {
            "existing_datasource_ids": existing_datasource_ids,
            "created_datasource_ids": created_datasource_ids,
            "feature": feature_details,
        },
    }


@router.post(
    models.APIPaths.FEATURE_UPLOAD_SCRIPT,
    status_code=status.HTTP_200_OK,
    response_model=models.FeatureAPIGenericResponse,
)
async def upload_feature_script(
    script: Annotated[UploadFile, Form()],
    background_tasks: BackgroundTasks,
    creation_method: Annotated[models.CreationMethod, Form()],
    scheduling_expression: Annotated[str, Form()] = None,
    versioning: Annotated[bool, Form()] = False,
    feature_drift_enabled: Annotated[bool, Form()] = False,
    user=Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature = FeatureCore(user_id, org_id, role)
    try:
        response = feature.upload_feature_script_sync(
            script,
            scheduling_expression,
            versioning,
            creation_method,
            feature_drift_enabled,
        )
        background_tasks.add_task(
            feature.upload_feature_script_async,
            response["state_machine_execution_arn"],
            response["execution_id"],
            response["scheduler_input"],
            response["scheduling_expression"],
        )
        return {
            "message": "success",
            "details": {"execution_id": response["execution_id"]},
        }
    except SyntaxError as e:
        raise HTTPException(
            status_code=422, detail=f"The feature script has a syntax error: {str(e)}"
        )
    except TypeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    models.APIPaths.FEATURE_GET_ID,
    status_code=status.HTTP_200_OK,
    response_model=models.FeatureAPIGenericResponse,
)
async def get_feature_id(
    inputs: models.FeatureIDRequest, user=Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    feature_id = feature.get_feature_id(
        feature_name=inputs.feature_name, name_type=inputs.name_type
    )
    return {"message": "success", "details": {"feature_id": feature_id}}


@router.post(
    models.APIPaths.FEATURE_LIST_EXECUTIONS,
    status_code=status.HTTP_200_OK,
    response_model=models.ListExecutionsResult,
)
async def list_feature_executions(
    input: models.ListExecutionsRequest = None, user=Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)

    try:
        if input is None:
            executions = feature.list_feature_executions()
        else:
            executions = feature.list_feature_executions(
                execution_id=input.execution_id
            )
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return models.ListExecutionsResult(executions=executions)


@router.post(
    models.APIPaths.FEATURE_TRIGGER_EXECUTION,
    status_code=status.HTTP_200_OK,
    response_model=models.FeatureAPIGenericResponse,
)
async def trigger_feature_execution(
    input: models.TriggerFeatureExecutionRequest,
    background_tasks: BackgroundTasks,
    user=Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    try:
        response = feature.trigger_feature_execution(input.feature_id)
        background_tasks.add_task(
            feature.feature_execution_async_handler,
            response["state_machine_execution_arn"],
            response["execution_id"],
        )
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "message": f"The feature execution for {input.feature_id} has been triggered successfully",
        "details": {"execution_id": response["execution_id"]},
    }


@router.post(
    models.APIPaths.FEATURE_SCHEDULED_EXECUTION,
    status_code=status.HTTP_200_OK,
    response_model=models.FeatureAPIGenericResponse,
)
async def scheduled_feature_execution(
    input: models.ScheduledFeatureExecutionRequest,
    background_tasks: BackgroundTasks,
    user=Depends(current_active_user),
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    try:
        execution_id = feature.scheduled_feature_execution()
        background_tasks.add_task(
            feature.feature_execution_async_handler,
            input.state_machine_execution_arn,
            execution_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "message": f"The scheduled execution {execution_id} has been triggered successfully",
        "details": {"execution_id": execution_id},
    }


@router.post(
    models.APIPaths.FEATURE_STORE_DRIFT,
    status_code=status.HTTP_201_CREATED,
    response_model=models.FeatureAPIGenericResponse,
)
async def store_feature_drift(
    input: models.StoreFeatureDriftRequest, user=Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    try:
        feature.store_feature_drift(
            input.feature_id, input.drifts, input.execution_type
        )
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"message": "success", "details": None}


@router.post(
    models.APIPaths.FEATURE_VIEW_DRIFTS,
    status_code=status.HTTP_200_OK,
    response_model=models.ViewFeatureDriftsResponse,
)
async def view_feature_drifts(
    input: models.ViewFeatureDriftsRequest, user=Depends(current_active_user)
):
    user_id = user.id
    org_id = user.org_id
    role = user.role

    feature = FeatureCore(user_id=user_id, org_id=org_id, role=role)
    try:
        results = feature.view_feature_drifts(input.feature_id)
    except exc.NoResultFound as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"feature_drifts": results}
