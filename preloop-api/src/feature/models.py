import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionType(str, Enum):
    FIRST_RUN = "first_run"
    AD_HOC = "ad_hoc"
    SCHEDULED = "scheduled"


class CreationMethod(str, Enum):
    PARSER = "parser"
    INCEPTION = "inception"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class APIPaths(str, Enum):
    """
    The different API paths for the feature API are defined in this
    enum. There are 5 main endpoints that all start with the parent
    word feature:

    feature/create: Used to create a new feature.
    feature/list: List all the features that are available for a given account.
    feature/describe: Used to describe a given feature.
    feature/delete: Used to delete a given feature.
    feature/modify: Used to modify a given feature.
    """

    FEATURE_CREATE = "/api/feature/create"
    FEATURE_LIST = "/api/feature/list"
    FEATURE_DESCRIBE = "/api/feature/describe"
    FEATURE_DELETE = "/api/feature/delete"
    FEATURE_MODIFY = "/api/feature/modify"
    FEATURE_RUN = "/api/feature/run"
    FEATURE_INSERT = "/api/feature/insert"
    FEATURE_GET = "/api/feature/get"
    FEATURE_EXPERIMENTAL_GET = "/api/feature/experimental/get"
    FEATURE_EXPERIMENTAL_CREATE = "/api/feature/experimental/create"
    FEATURE_GET_ID = "/api/feature/get/id"
    FEATURE_UPLOAD_SCRIPT = "/api/feature/upload-script"
    FEATURE_LIST_EXECUTIONS = "/api/feature/list-executions"
    FEATURE_TRIGGER_EXECUTION = "/api/feature/trigger-execution"
    FEATURE_SCHEDULED_EXECUTION = "/api/feature/scheduled-execution"
    FEATURE_STORE_DRIFT = "/api/feature/store-drift"
    FEATURE_VIEW_DRIFTS = "/api/feature/view-drifts"


# pydantic models to validates inputs.


class ModificationFields(BaseModel):
    feature_description: Optional[str] = None
    scheduling_expression_string: Optional[str] = None


class ColumnStructureFeatureDefinitionExperimentalGet(BaseModel):
    name: str
    type: str  # target, id, feature
    data_type: str  # please use pandas type as this will be uniform across all sources


class FeatureDefinitionExperimentalGet(BaseModel):
    name: str
    columns: List[ColumnStructureFeatureDefinitionExperimentalGet]


class ExperimentalGetFeatureInput(BaseModel):
    datasources: List[Dict]
    feature: FeatureDefinitionExperimentalGet


class FeatureAPIGenericInput(BaseModel):
    feature_id: uuid.UUID
    version: Optional[int] = None


class ModifyFeatureRequest(BaseModel):
    feature_id: uuid.UUID
    modifications: ModificationFields


class Feature(BaseModel):
    """
    A feature is derived from a datasource and consists of a
    column from a datasource. Features can be assembled together
    to form a dataset, which is used for downstream analytics and
    ml tasks.
    """

    id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    creation_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    datasource_names: List[str]
    feature_name: str
    feature_description: str = Field(
        title="Feature Description",
        max_length=400,
        default="The description for this feature",
    )
    column_types: Dict[Any, Any]
    feature_dest: str
    feature_cols: List[str]
    feature_signature: Optional[ExperimentalGetFeatureInput] = None
    id_cols: List[str]
    target_cols: Optional[List[str]] = None
    scheduling_expression_string: Optional[str] = None
    creation_method: str
    versioning: bool = False
    latest_version: int
    location_string: Optional[str] = None
    script_loc: str
    feature_drift_enabled: bool = False
    execution_id: uuid.UUID


class FeatureDetails(BaseModel):
    id: Optional[uuid.UUID] = None
    creation_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    datasource_names: List[str]
    feature_name: str
    feature_description: str = Field(
        title="Feature Description",
        max_length=400,
        default="The description for this feature",
    )
    column_types: Dict[Any, Any]
    feature_cols: List[str]
    id_cols: List[str]
    target_cols: Optional[List[str]] = None
    scheduling_expression_string: Optional[str] = None
    versioning: bool = False
    latest_version: int
    feature_drift_enabled: bool
    team: Optional[str] = None


class ListFeaturesResult(BaseModel):
    features: List[FeatureDetails]


class FeatureIDRequest(BaseModel):
    feature_name: str
    name_type: str = "generic"


class ExperimentFeatureGetRequest(BaseModel):
    feature_signature: ExperimentalGetFeatureInput
    version: int


class FeatureAPIGenericResponse(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None | ExperimentalGetFeatureInput


class ExperimentalFeatureCreateRequest(BaseModel):
    versioning: bool
    execution_id: uuid.UUID
    script_loc: str
    feature_signature: Dict[str, Any]
    feature_dest: str
    scheduling_expression: str | None = None
    feature_drift_enabled: bool


class ListExecutionsRequest(BaseModel):
    execution_id: uuid.UUID


class FeatureExecution(BaseModel):
    id: uuid.UUID
    status: ExecutionStatus
    execution_type: ExecutionType
    record_date: datetime
    reason: Optional[str] = None


class ListExecutionsResult(BaseModel):
    executions: List[FeatureExecution]


class TriggerFeatureExecutionRequest(BaseModel):
    feature_id: uuid.UUID


class ScheduledFeatureExecutionRequest(BaseModel):
    state_machine_execution_arn: str


class StoreFeatureDriftRequest(BaseModel):
    feature_id: uuid.UUID
    execution_type: ExecutionType
    drifts: Dict[str, Dict[str, Any]]


class ViewFeatureDriftsRequest(BaseModel):
    feature_id: uuid.UUID


class FeatureDriftDetails(BaseModel):
    feature_id: uuid.UUID
    version: int
    record_date: datetime
    drifts: Dict[str, Dict[str, Any]]


class ViewFeatureDriftsResponse(BaseModel):
    feature_drifts: List[FeatureDriftDetails]
