import uuid
from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# # Datasource models
# class SQLConnectionParams(BaseModel):
#     user_name: str
#     host_name: str
#     port_number: int
#     database_name: str
#     table_name: str
#     schema_name: str | None = None


# class SQLAuthParams(BaseModel):
#     password: str


# class S3ConnectionDetails(BaseModel):
#     bucket_name: str
#     object_key: str


# class SQLConnectionDetails(BaseModel):
#     connection_params: SQLConnectionParams
#     auth_params: SQLAuthParams


# class ListDatasourcesRequest(BaseModel):
#     datasource_id: uuid.UUID


# class DataSourceDetails(BaseModel):
#     id: str
#     team: Optional[str] = None
#     datasource_name: str
#     datasource_description: Optional[str] = None
#     datasource_type: str
#     connection_details: SQLConnectionDetails | S3ConnectionDetails
#     datasource_details: Optional[Dict[Any, Any]] = None
#     creation_date: str
#     last_updated: str | None


# class ListDatasourcesResult(BaseModel):
#     datasources: List[DataSourceDetails]


# class DeleteDatasourceRequest(BaseModel):
#     datasource_id: uuid.UUID


# class DeleteDatasourceResult(BaseModel):
#     message: str
#     details: Dict[str, Any] | List[Dict[str, Any]] | None


# class DatasourceIdentifierField(BaseModel):
#     datasource_id: uuid.UUID


# class ModifiableDatasourceFields(BaseModel):
#     datasource_name: Optional[str] = None
#     datasource_description: Optional[str] = None
#     connection_details: Optional[SQLConnectionDetails | S3ConnectionDetails] = None


# class ModifyDatasourceRequest(BaseModel):
#     fields: DatasourceIdentifierField
#     modfield: ModifiableDatasourceFields


# class ModifyDatasourceResult(BaseModel):
#     message: str
#     details: Dict[str, Any] | List[Dict[str, Any]] | None


# # Feature models
# class ListFeaturesRequest(BaseModel):
#     feature_id: uuid.UUID


# class FeatureDetails(BaseModel):
#     id: str
#     creation_date: Optional[str] = None
#     last_updated: Optional[str] = None
#     datasource_names: List[str]
#     feature_name: str
#     feature_description: str = Field(
#         title="Feature Description", max_length=400, default="The description for this feature"
#     )
#     column_types: Dict[Any, Any]
#     feature_cols: List[str]
#     id_cols: List[str]
#     target_cols: Optional[List[str]] = None
#     scheduling_expression_string: Optional[str] = None
#     versioning: bool = False
#     latest_version: int
#     feature_drift_enabled: bool
#     team: Optional[str] = None


# class ListFeaturesResult(BaseModel):
#     features: List[FeatureDetails]


# class DeleteFeatureRequest(BaseModel):
#     feature_id: uuid.UUID


# class DeleteFeatureResult(BaseModel):
#     message: str
#     details: Dict[str, Any] | List[Dict[str, Any]] | None


# class FeatureIdentifierField(BaseModel):
#     feature_id: uuid.UUID


# class ModifiableFeatureFields(BaseModel):
#     feature_name: str
#     feature_description: Optional[str] = None
#     update_freq: Optional[str] = None


# class ModifyFeatureRequest(BaseModel):
#     fields: FeatureIdentifierField
#     modfield: ModifiableFeatureFields


# class ModifyFeatureResult(BaseModel):
#     message: str
#     details: Dict[str, Any] | List[Dict[str, Any]] | None


# class GetFeatureRequest(BaseModel):
#     feature_id: str
#     version: int | None = None


# class CreationMethod(str, Enum):
#     PARSER = "parser"
#     INCEPTION = "inception"


# class UploadFeatureScriptRequest(BaseModel):
#     file_path: str
#     creation_method: CreationMethod
#     scheduling_expression: str | None = None
#     versioning: bool = False
#     feature_drift_enabled: bool = False


# class UploadFeatureScriptResult(BaseModel):
#     message: str
#     details: Dict[str, Any] | List[Dict[str, Any]] | None


# class ListFeatureExecutionsRequest(BaseModel):
#     execution_id: uuid.UUID


# class FeatureExecution(BaseModel):
#     id: str
#     status: str
#     execution_type: str
#     record_date: str
#     reason: Optional[str] = None


# class ListFeatureExecutionsResult(BaseModel):
#     executions: List[FeatureExecution]


# class TriggerFeatureExecutionRequest(BaseModel):
#     feature_id: uuid.UUID


# class TriggerFeatureExecutionResult(BaseModel):
#     message: str
#     details: Dict[str, Any] | List[Dict[str, Any]] | None


# class ViewFeatureDriftsRequest(BaseModel):
#     feature_id: uuid.UUID


# class FeatureDriftDetails(BaseModel):
#     feature_id: uuid.UUID
#     version: int
#     record_date: datetime
#     drifts: Dict[str, Dict[str, Any]]


# class ViewFeatureDriftsResponse(BaseModel):
#     feature_drifts: List[FeatureDriftDetails]


class ListMLModelsRequest(BaseModel):
    """
    The request body for listing ML models.
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


class ListMLModelsResult(BaseModel):
    """
    The response body for listing ML models.
    """

    ml_models: List[MLModelDetails]


class CreateMLModelRequest(BaseModel):
    """
    The request body for creating a new ML model.
    """

    ml_model_name: str
    ml_model_description: str
    training_script_path: str
    predict_function_name: str = "predict"
    require_api_key: bool = True
    schedule: Optional[str] = None
    env_vars: Optional[str] = None


class CreateMLModelResult(BaseModel):
    """
    The response body for creating a new ML model.
    """

    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class RetrainMLModelRequest(BaseModel):
    """
    The request body for retraining an ML model.
    """

    ml_model_id: uuid.UUID


class RetrainMLModelResult(BaseModel):
    """
    The response body for retraining an ML model.
    """

    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class ListTrainingJobsRequest(BaseModel):
    job_id: uuid.UUID


class TrainingJobDetails(BaseModel):
    id: uuid.UUID
    ml_model_id: uuid.UUID
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    reason: Optional[str] = None


class ListTrainingJobsResult(BaseModel):
    training_jobs: List[TrainingJobDetails]


class DeleteMLModelRequest(BaseModel):
    """
    The request body for deleting an ML model.
    """

    ml_model_id: uuid.UUID


class DeployMLModelRequest(BaseModel):
    """
    The request body for starting an ML model.
    """

    ml_model_id: str
    version: Annotated[int, Field(strict=True, gt=0)] | Literal["latest"]
    require_api_key: Optional[bool] = False


class DeployMLModelResult(BaseModel):
    """
    The response body for retraining an ML model.
    """

    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


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


class DeleteMLModelResult(BaseModel):
    """
    The response body for deleting an ML model.
    """

    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class StopMLModelRequest(BaseModel):
    """
    The request body for stopping an ML model.
    """

    hosted_ml_model_id: uuid.UUID


class StopMLModelResult(BaseModel):
    """
    The response body for stopping an ML model.
    """

    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


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
