import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Datasource models
class DatasourceType(str, Enum):
    """
    Enum restricting the datasources that are used by Preloop. Please
    expand this enum as we add in more data sources.
    """

    POSTGRES = "postgres"
    MYSQL = "mysql"
    S3 = "s3"


class ExecutionType(str, Enum):
    FIRST_RUN = "first_run"
    AD_HOC = "ad_hoc"
    SCHEDULED = "scheduled"


class SQLConnectionParams(BaseModel):
    user_name: str
    host_name: str
    port_number: int
    database_name: str
    table_name: str
    schema_name: str | None = None


class SQLAuthParams(BaseModel):
    password: str


class S3ConnectionDetails(BaseModel):
    bucket_name: str
    object_key: str


class SQLConnectionDetails(BaseModel):
    connection_params: SQLConnectionParams
    auth_params: SQLAuthParams


# Pydantic models to validate inputs
class CreateDatasourceRequest(BaseModel):
    datasource_name: str
    datasource_description: str = Field(
        title="The description of the datasource", max_length=400, default="Description of this datasource."
    )
    datasource_type: DatasourceType
    connection_details: SQLConnectionDetails | S3ConnectionDetails
    execution_id: uuid.UUID


class CreateDatasourceResult(BaseModel):
    returned_message: str
    id: uuid.UUID
    preview_of_data: Optional[Any] = None


class ListDatasourcesRequest(BaseModel):
    datasource_id: uuid.UUID


class DataSourceDetails(BaseModel):
    id: str | uuid.UUID
    team: Optional[str] = None
    datasource_name: str
    datasource_description: Optional[str] = None
    datasource_type: DatasourceType
    connection_details: SQLConnectionDetails | S3ConnectionDetails
    datasource_details: Optional[Dict[Any, Any]] = None
    creation_date: datetime
    last_updated: datetime | None


class ListDatasourcesResult(BaseModel):
    datasources: List[DataSourceDetails]


class DeleteDatasourceRequest(BaseModel):
    datasource_id: uuid.UUID


class DeleteDatasourceResult(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class DatasourceIdentifierField(BaseModel):
    datasource_id: uuid.UUID


class ModifiableDatasourceFields(BaseModel):
    datasource_name: Optional[str] = None
    datasource_description: Optional[str] = None
    connection_details: Optional[SQLConnectionDetails | S3ConnectionDetails] = None


class ModifyDatasourceRequest(BaseModel):
    fields: DatasourceIdentifierField
    modfield: ModifiableDatasourceFields


class ModifyDatasourceResult(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class GetDatasourceRequest(BaseModel):
    datasource_id: uuid.UUID


class GetDatasourceIdRequest(BaseModel):
    datasource_name: str
    name_type: str = "generic"


class GetDatasourceIdResult(BaseModel):
    message: str
    details: Dict[str, Any]


# Feature models
class ListFeaturesRequest(BaseModel):
    feature_id: uuid.UUID


class FeatureDetails(BaseModel):
    id: str
    creation_date: Optional[str] = None
    last_updated: Optional[str] = None
    datasource_names: List[str]
    feature_name: str
    feature_description: str = Field(
        title="Feature Description", max_length=400, default="The description for this feature"
    )
    column_types: Dict[Any, Any]
    feature_cols: List[str]
    id_cols: List[str]
    target_cols: Optional[List[str]] = None
    scheduling_expression_string: Optional[str] = None
    versioning: bool = False
    latest_version: int
    team: Optional[str] = None


class ListFeaturesResult(BaseModel):
    features: List[FeatureDetails]


class CreateFeatureRequest(BaseModel):
    datasource_names: List[str]
    feature_name: str
    feature_description: str
    column_types: Dict[Any, Any]
    feature_dest: str
    feature_cols: List[str]
    id_cols: List[str]
    target_cols: Optional[List[str]] = None
    scheduling_expression_string: Optional[str] = None
    creation_method: str
    versioning: bool
    latest_version: int
    location_string: Optional[str] = None
    script_loc: str
    feature_drift_enabled: bool = False
    execution_id: uuid.UUID


class CreateFeatureResult(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class DeleteFeatureRequest(BaseModel):
    feature_id: uuid.UUID


class DeleteFeatureResult(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class FeatureIdentifierField(BaseModel):
    feature_id: uuid.UUID


class ModifiableFeatureFields(BaseModel):
    feature_name: str
    feature_description: Optional[str] = None
    scheduling_expression_string: Optional[str] = None


class ModifyFeatureRequest(BaseModel):
    fields: FeatureIdentifierField
    modfield: ModifiableFeatureFields


class ModifyFeatureResult(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class InsertFeatureRequest(BaseModel):
    feature_id: uuid.UUID
    operation_type: str
    data: Any


class InsertFeatureResult(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class GetFeatureRequest(BaseModel):
    feature_id: str
    version: int


class ColumnStructureFeatureDefinitionExperimentalGet(BaseModel):
    column_name: str
    datasource_name: str
    transforms: List[str]
    type: str  # target, id, feature
    datatype: str  # please use pandas type as this will be uniform across all sources


class FeatureDefinitionExperimentalGet(BaseModel):
    feature_name: str
    columns: List[ColumnStructureFeatureDefinitionExperimentalGet]


class ExperimentalGetFeatureInput(BaseModel):
    datasources: List[Dict]
    feature: List[FeatureDefinitionExperimentalGet]


class ExperimentalCreateFeatureRequest(BaseModel):
    versioning: bool
    script_loc: str
    execution_id: uuid.UUID
    feature_signature: Dict[str, Any]
    feature_dest: str
    scheduling_expression: str | None = None
    feature_drift_enabled: bool = False


class ExperimentalCreateFeatureResult(BaseModel):
    message: str
    details: Dict[str, Any]


class ExperimentalGetFeatureRequest(BaseModel):
    feature_signature: ExperimentalGetFeatureInput
    version: int


class GetFeatureIdRequest(BaseModel):
    feature_name: str
    name_type: str = "generic"


class GetFeatureIdResult(BaseModel):
    message: str
    details: Dict[str, Any]


class ScheduledFeatureExecutionRequest(BaseModel):
    state_machine_execution_arn: str


class ScheduledFeatureExecutionResult(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class StoreFeatureDriftRequest(BaseModel):
    feature_id: uuid.UUID
    execution_type: ExecutionType
    drifts: Dict[str, Dict[str, Any]]


class StoreFeatureDriftResult(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None
