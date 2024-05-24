import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class APIPaths(str, Enum):
    """
    The different API paths for the ml_model API are defined in this
    enum.
    """

    ML_MODEL_CREATE = "/api/ml-model/create"
    ML_MODEL_LIST = "/api/ml-model/list"
    ML_MODEL_DELETE = "/api/ml-model/delete"
    ML_MODEL_MODIFY = "/api/ml-model/modify"
    ML_MODEL_DEPLOY = "/api/ml-model/deploy"
    ML_MODEL_STOP = "/api/ml-model/stop"
    ML_MODEL_RETRAIN = "/api/ml-model/retrain"
    ML_MODEL_LIST_TRAINING_JOBS = "/api/ml-model/list-training-jobs"
    ML_MODEL_LIST_HOSTED_MODELS = "/api/ml-model/list-hosted-models"
    ML_MODEL_STORE_INFO = "/api/ml-model/store-info"
    ML_MODEL_STORE_METRICS = "/api/ml-model/store-metrics"
    ML_MODEL_LIST_VERSIONS = "/api/ml-model/list-versions"
    ML_MODEL_GET_COUNTS = "/api/ml-model/get-counts"
    ML_MODEL_VIEW_DATA_FLOW = "/api/ml-model/view-data-flow"
    ML_MODEL_LIST_UNDEPLOYED_VERSIONS = "/api/ml-model/list-undeployed-versions"
    ML_MODEL_GET_TRAINING_JOB_LOGS = "/api/ml-model/get-training-job-logs"


class HostedMLModelStatus(str, Enum):
    """
    The status of the hosted model.
    """

    AVAILABLE = "available"
    DELETING = "deleting"
    STOPPING = "stopping"
    FAILED = "failed"
    TRAINING = "training"
    DEPLOYING = "deploying"


class MLModelTrainingJobStatus(str, Enum):
    """
    The status of the training job.
    """

    TRAINING = "training"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


class DeleteMLModelRequest(BaseModel):
    """
    The request body for deleting an ML model.
    """

    ml_model_id: uuid.UUID


class MLModelDetails(BaseModel):
    """
    The response body for getting ML model details.
    """

    id: uuid.UUID
    creation_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    ml_model_name: str
    ml_model_description: str
    status: str
    reason: Optional[str] = None
    endpoint_url: Optional[str] = None
    team: Optional[str] = None
    owner: Optional[str] = None
    ml_model_details: Optional[Dict[Any, Any]] = None
    ml_prediction_type: Optional[str] = None
    ml_model_inputs: Optional[Dict[Any, Any]] = None
    latest_version: Optional[int] = None
    latest_deployed_version: Optional[int] = None
    require_api_key: bool
    schedule: Optional[str] = None


class ListMLModelsRequest(BaseModel):
    """
    The request body for listing ML models.
    """

    ml_model_id: uuid.UUID


class ListMLModelsResult(BaseModel):
    """
    The response body for listing ML models.
    """

    ml_models: List[MLModelDetails]


class ModifyMLModelRequest(BaseModel):
    scheduling_expression_string: Optional[str] = None
    ml_model_description: Optional[str] = None


class MLModelGenericResponse(BaseModel):
    """
    The response body for creating a new ML model.
    """

    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class DeployMLModelRequest(BaseModel):
    """
    The request body for starting an ML model.
    """

    ml_model_id: str
    version: Annotated[int, Field(strict=True, gt=0)] | Literal["latest"]
    require_api_key: Optional[bool] = False


class HostedMLModelDetails(BaseModel):
    """
    The response body for getting hosted ML model details.
    """

    id: uuid.UUID
    ml_model_id: uuid.UUID
    ml_model_name: str
    version: Any
    status: str
    endpoint_url: Optional[str] = None
    creation_date: datetime
    reason: Optional[str] = None
    require_api_key: bool
    owner: str
    is_latest_version: bool = False


class ListHostedMLModelsResult(BaseModel):
    """
    The response body for listing hosted ML models.
    """

    hosted_ml_models: List[HostedMLModelDetails]


class ListHostedMLModelsRequest(BaseModel):
    """
    The request body for listing hosted ML models.
    """

    ml_model_id: uuid.UUID


class StopMLModelRequest(BaseModel):
    """
    The request body for stopping an ML model.
    """

    hosted_ml_model_id: uuid.UUID


class RetrainMLModelRequest(BaseModel):
    """
    The request body for retraining an ML model.
    """

    ml_model_id: uuid.UUID


class TrainingJobDetails(BaseModel):
    id: uuid.UUID
    ml_model_id: uuid.UUID
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    reason: Optional[str] = None


class ListTrainingJobsResult(BaseModel):
    training_jobs: List[TrainingJobDetails]


class ListTrainingJobsRequest(BaseModel):
    job_id: Optional[uuid.UUID] = None
    ml_model_id: Optional[uuid.UUID] = None


class StoreMLModelInfoRequest(BaseModel):
    """
    The request body for storing info about an ML model.
    """

    ml_model_id: uuid.UUID
    ml_model_package: Optional[str] = None
    ml_model_type: Optional[str] = None
    prediction_type: Optional[str] = None
    ml_model_data_flow: Optional[str] = None


class StoreMLModelMetricsRequest(BaseModel):
    """
    The request body for storing hyperparameters about an ML model.
    """

    ml_model_id: uuid.UUID
    version: int
    metrics: List[Dict[str, Any]]


class ListMLModelVersionsRequest(BaseModel):
    """
    The request body for listing ML model versions.
    """

    ml_model_id: uuid.UUID


class MLModelVersionDetails(BaseModel):
    """
    The response body for getting ML model version details.
    """

    id: uuid.UUID
    ml_model_id: uuid.UUID
    version: int
    ml_model_metrics: Dict[str, Any] = None
    creation_date: datetime
    ml_model_metric_limit_breaches: Optional[Dict[str, Any]] = None


class ListMLModelVersionsResult(BaseModel):
    """
    The response body for listing ML model versions.
    """

    ml_model_versions: List[MLModelVersionDetails]


class GetMLModelCountsResult(BaseModel):
    """
    The response body for getting ML model counts.
    """

    trained_ml_models: int
    deployed_ml_models: int


class ViewMLModelDataFlowRequest(BaseModel):
    """
    The request body for viewing the data flow of an ML model.
    """

    ml_model_id: uuid.UUID


class ViewMLModelDataFlowResult(BaseModel):
    """
    The response body for viewing the data flow of an ML model.
    """

    ml_model_id: uuid.UUID
    ml_model_data_flow: Optional[Dict[str, Any]] = None


class UndeployedMLModelVersionsDetails(BaseModel):
    """
    The response body for getting ML model version details.
    """

    ml_model_id: uuid.UUID
    ml_model_name: str
    versions: List[int | str]


class ListUndeployedMLModelVersionsResult(BaseModel):
    """
    The response body for listing undeployed ML model versions.
    """

    undeployed_ml_model_versions: List[UndeployedMLModelVersionsDetails]


class GetTrainingJobLogsRequest(BaseModel):
    """
    The request body for getting training job logs.
    """

    job_id: uuid.UUID
    limit: int = 50
    start_time: int = 0
    end_time: int = int(datetime.now().timestamp() * 1000)
    next_token: str = None


class GetTrainingJobLogsResult(BaseModel):
    """
    The response body for getting training job logs.
    """

    job_id: uuid.UUID
    events: List[Dict[str, Any]]
    forward_token: Optional[str] = None
    backward_token: Optional[str] = None
