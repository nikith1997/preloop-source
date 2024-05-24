import logging
from typing import Annotated, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import Json

from src.auth.routers import list_org_users
from src.common import check
from src.ml_model.models import *
from src.ml_model.utilities import MLModelCore

log = logging.getLogger("uvicorn")

router = APIRouter()


@router.post(
    APIPaths.ML_MODEL_LIST,
    status_code=status.HTTP_200_OK,
    response_model=ListMLModelsResult,
    response_model_exclude_none=True,
)
async def list_ml_models(
    request: Optional[ListMLModelsRequest] = None, user=Depends(check)
):
    """
    Lists all the ML models created by the user.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)

    if request is None:
        ml_models = ml_model_core.list_ml_models()
        return ListMLModelsResult(ml_models=ml_models)

    ml_models = ml_model_core.list_ml_models(request.ml_model_id)
    if ml_models == []:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ML Model {request.ml_model_id} does not exist",
        )
    return ListMLModelsResult(ml_models=ml_models)


@router.post(
    APIPaths.ML_MODEL_CREATE,
    status_code=status.HTTP_201_CREATED,
    response_model=MLModelGenericResponse,
)
async def create_ml_model(
    ml_model_name: Annotated[str, Form()],
    ml_model_description: Annotated[str, Form()],
    training_script: Annotated[UploadFile, Form()],
    background_tasks: BackgroundTasks,
    predict_function_name: Annotated[str, Form()] = "predict",
    require_api_key: Annotated[bool, Form()] = True,
    schedule: Annotated[str, Form()] = None,
    env_vars: Annotated[Json[Any], Form()] = None,
    user=Depends(check),
):
    """
    Creates a new ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        ml_model_id, ml_model_training_job_id, scripts = ml_model_core.create_ml_model(
            ml_model_name,
            ml_model_description,
            training_script,
            predict_function_name,
            require_api_key,
            schedule,
            env_vars,
        )
        background_tasks.add_task(
            ml_model_core.create_ml_model_async,
            ml_model_id,
            ml_model_training_job_id,
            scripts,
            require_api_key,
            schedule,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return MLModelGenericResponse(
        message="Success", details={"ml_model_id": ml_model_id, "status": "training"}
    )


@router.post(
    APIPaths.ML_MODEL_DEPLOY,
    status_code=status.HTTP_200_OK,
    response_model=MLModelGenericResponse,
)
async def deploy_ml_model(
    request: DeployMLModelRequest,
    background_tasks: BackgroundTasks,
    user=Depends(check),
):
    """
    Starts an ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        (
            hosted_ml_model_id,
            ml_model_name,
            inference_script_loc,
        ) = ml_model_core.start_ml_model(
            request.ml_model_id, request.version, request.require_api_key
        )
        background_tasks.add_task(
            ml_model_core.start_ml_model_async,
            request.ml_model_id,
            ml_model_name,
            -1 if request.version == "latest" else request.version,
            inference_script_loc,
            request.require_api_key,
            hosted_ml_model_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return MLModelGenericResponse(
        message="Success",
        details={"hosted_ml_model_id": hosted_ml_model_id, "status": "deploying"},
    )


@router.post(
    APIPaths.ML_MODEL_LIST_HOSTED_MODELS,
    status_code=status.HTTP_200_OK,
    response_model=ListHostedMLModelsResult,
)
async def list_hosted_ml_models(
    request: Optional[ListHostedMLModelsRequest] = None, user=Depends(check)
):
    """
    Lists all the hosted ML models.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)

    if request is None:
        hosted_ml_models = ml_model_core.list_hosted_ml_models()
        return ListHostedMLModelsResult(hosted_ml_models=hosted_ml_models)

    hosted_ml_models = ml_model_core.list_hosted_ml_models(request.ml_model_id)
    if hosted_ml_models == []:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ML Model {request.ml_model_id} does not exist",
        )
    return ListHostedMLModelsResult(hosted_ml_models=hosted_ml_models)


@router.post(
    APIPaths.ML_MODEL_STOP,
    status_code=status.HTTP_200_OK,
    response_model=MLModelGenericResponse,
)
async def stop_ml_model(
    request: StopMLModelRequest,
    background_tasks: BackgroundTasks,
    user=Depends(check),
):
    """
    Hosts an ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        response = ml_model_core.stop_ml_model(request.hosted_ml_model_id)
        background_tasks.add_task(
            ml_model_core.stop_ml_model_async, request.hosted_ml_model_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return {
        "message": "Success",
        "details": {
            "hosted_ml_model_id": request.hosted_ml_model_id,
            "status": HostedMLModelStatus.STOPPING.value,
        },
    }


@router.post(
    APIPaths.ML_MODEL_RETRAIN,
    status_code=status.HTTP_200_OK,
    response_model=MLModelGenericResponse,
)
async def retrain_ml_model(
    request: RetrainMLModelRequest,
    background_tasks: BackgroundTasks,
    user=Depends(check),
):
    """
    Retrains an ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        training_job_id = ml_model_core.retrain_ml_model(request.ml_model_id)
        background_tasks.add_task(
            ml_model_core.retrain_ml_model_async, request.ml_model_id, training_job_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return MLModelGenericResponse(
        message="Success",
        details={
            "ml_model_training_job_id": training_job_id,
            "status": MLModelTrainingJobStatus.TRAINING.value,
        },
    )


@router.post(
    APIPaths.ML_MODEL_LIST_TRAINING_JOBS,
    status_code=status.HTTP_200_OK,
    response_model=ListTrainingJobsResult,
)
async def list_training_jobs(
    request: Optional[ListTrainingJobsRequest] = None, user=Depends(check)
):
    """
    Lists all the training jobs for an ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)

    if request is None:
        training_jobs = ml_model_core.list_training_jobs()
        return ListTrainingJobsResult(training_jobs=training_jobs)

    elif request.job_id:
        training_jobs = ml_model_core.list_training_jobs(job_id=request.job_id)

    elif request.ml_model_id:
        training_jobs = ml_model_core.list_training_jobs(
            ml_model_id=request.ml_model_id
        )

    elif request.job_id and request.ml_model_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only one of job_id or ml_model_id can be specified",
        )

    if training_jobs == []:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Job {request.job_id} does not exist",
        )
    return ListTrainingJobsResult(training_jobs=training_jobs)


@router.post(
    APIPaths.ML_MODEL_DELETE,
    status_code=status.HTTP_200_OK,
    response_model=MLModelGenericResponse,
)
async def delete_ml_model(
    request: DeleteMLModelRequest,
    background_tasks: BackgroundTasks,
    user=Depends(check),
):
    """
    Deletes an ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        ml_model_core.delete_ml_model(request.ml_model_id)
        background_tasks.add_task(
            ml_model_core.delete_ml_model_async, request.ml_model_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return {
        "message": "Success",
        "details": {
            "ml_model_id": request.ml_model_id,
            "status": HostedMLModelStatus.DELETING.value,
        },
    }


@router.post(
    APIPaths.ML_MODEL_STORE_INFO,
    status_code=status.HTTP_201_CREATED,
    response_model=MLModelGenericResponse,
)
async def store_ml_model_info(request: StoreMLModelInfoRequest, user=Depends(check)):
    """
    Stores the information of an ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        ml_model_core.store_ml_model_info(
            request.ml_model_id,
            request.ml_model_package,
            request.ml_model_type,
            request.prediction_type,
            request.ml_model_data_flow,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return MLModelGenericResponse(message="Success", details={})


@router.post(
    APIPaths.ML_MODEL_STORE_METRICS,
    status_code=status.HTTP_201_CREATED,
    response_model=MLModelGenericResponse,
)
async def store_ml_model_metrics(
    request: StoreMLModelMetricsRequest, user=Depends(check)
):
    """
    Stores the hyperparameters of an ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        ml_model_core.store_ml_model_metrics(
            request.ml_model_id, request.version, request.metrics
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return MLModelGenericResponse(message="Success", details={})


@router.post(
    APIPaths.ML_MODEL_LIST_VERSIONS,
    status_code=status.HTTP_200_OK,
    response_model=ListMLModelVersionsResult,
)
async def list_ml_model_versions(
    request: ListMLModelVersionsRequest, user=Depends(check)
):
    """
    Lists all the versions of an ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        ml_model_versions = ml_model_core.list_ml_model_versions(request.ml_model_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return ListMLModelVersionsResult(ml_model_versions=ml_model_versions)


@router.get(
    APIPaths.ML_MODEL_GET_COUNTS,
    status_code=status.HTTP_200_OK,
    response_model=GetMLModelCountsResult,
)
async def get_ml_model_counts(user=Depends(check)):
    """
    Gets the counts of ML models.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    ml_model_counts = ml_model_core.get_ml_model_counts()
    return GetMLModelCountsResult(
        trained_ml_models=ml_model_counts["trained_ml_models"],
        deployed_ml_models=ml_model_counts["deployed_ml_models"],
    )


@router.post(
    APIPaths.ML_MODEL_VIEW_DATA_FLOW,
    status_code=status.HTTP_200_OK,
    response_model=ViewMLModelDataFlowResult,
)
async def view_ml_model_data_flow(
    request: ViewMLModelDataFlowRequest, user=Depends(check)
):
    """
    Views the data flow of an ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        ml_model_data_flow = ml_model_core.view_ml_model_data_flow(request.ml_model_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return ViewMLModelDataFlowResult(
        ml_model_id=request.ml_model_id, ml_model_data_flow=ml_model_data_flow
    )


@router.get(
    APIPaths.ML_MODEL_LIST_UNDEPLOYED_VERSIONS,
    status_code=status.HTTP_200_OK,
    response_model=ListUndeployedMLModelVersionsResult,
)
async def list_undeployed_ml_model_versions(user=Depends(check)):
    """
    Lists all the undeployed versions of an ML model.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        undeployed_ml_model_versions = ml_model_core.list_undeployed_ml_model_versions()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    return ListUndeployedMLModelVersionsResult(
        undeployed_ml_model_versions=undeployed_ml_model_versions
    )


@router.post(
    APIPaths.ML_MODEL_GET_TRAINING_JOB_LOGS,
    status_code=status.HTTP_200_OK,
    response_model=GetTrainingJobLogsResult,
)
async def get_training_job_logs(
    request: GetTrainingJobLogsRequest, user=Depends(check)
):
    """
    Gets the logs of a training job.
    """
    user_id = user.id
    org_id = user.org_id
    role = user.role

    ml_model_core = MLModelCore(user_id, org_id, role)
    try:
        response = ml_model_core.get_training_job_logs(
            request.job_id,
            request.limit,
            request.start_time,
            request.end_time,
            request.next_token,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    return GetTrainingJobLogsResult(
        job_id=request.job_id,
        events=response["events"],
        forward_token=response["nextForwardToken"],
        backward_token=response["nextBackwardToken"],
    )
