import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, Json


class DataSourceType(str, Enum):
    """
    Enum restricting the datasources that are used by Preloop. Please
    expand this enum as we add in more data sources.
    """

    POSTGRES = "postgres"
    MYSQL = "mysql"
    S3 = "s3"


class APIPaths(str, Enum):
    """
    The different API paths for the datasource API are defined in this
    enum. There are 4 main endpoints that all start with the parent
    word datasource:

    datasource/create: Used to create a new datasource.
    datasource/list: List all the datasources that are available for a given account.
    datasource/describe: Used to describe a given datasource.
    datasource/delete: Used to delete a given datasource.
    datasource/modify: Used to modify a given datasource.
    """

    DATASOURCE_CREATE = "/api/datasource"
    DATASOURCE_LIST = "/api/datasource/list"
    DATASOURCE_DESCRIBE = "/api/datasource/describe"
    DATASOURCE_DELETE = "/api/datasource/delete"
    DATASOURCE_MODIFY = "/api/datasource/modify"
    DATASOURCE_CONNECT = "/api/datasource/connect"  # internal use only
    DATASOURCE_GET = "/api/datasource/get"
    DATASOURCE_GET_ID = "/api/datasource/get/id"


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
        title="The description of the datasource",
        max_length=400,
        default="Description of this datasource.",
    )
    datasource_type: DataSourceType
    connection_details: SQLConnectionDetails | S3ConnectionDetails
    execution_id: uuid.UUID


class DataSource(BaseModel):
    """
    Data source is the primitive in Preloop from which features
    and datasets are constructed.
    """

    user_id: uuid.UUID
    datasource_name_script: str
    datasource_name_generic: str
    datasource_description: Optional[str] = None
    connection_details: SQLConnectionDetails | S3ConnectionDetails
    datasource_type: DataSourceType
    datasource_details: Optional[Dict[Any, Any]] = None
    hashed_value: Optional[str] = None
    execution_id: uuid.UUID


class CreationResponse(BaseModel):
    returned_message: str
    id: uuid.UUID
    preview_of_data: Optional[Any] = None


class ModificationField(BaseModel):
    datasource_description: Optional[str] = None
    connection_details: Optional[SQLConnectionDetails | S3ConnectionDetails] = None


class DataSourceDetails(BaseModel):
    id: str | uuid.UUID
    team: Optional[str] = None
    datasource_name: str
    datasource_description: Optional[str] = None
    datasource_type: DataSourceType
    connection_details: SQLConnectionDetails | S3ConnectionDetails
    datasource_details: Optional[Dict[Any, Any]] = None
    creation_date: datetime
    last_updated: datetime | None


class ListDatasourcesResult(BaseModel):
    datasources: List[DataSourceDetails]


class DataSourceGet(BaseModel):
    datasource_id: uuid.UUID


class DataSourceAPIGenericResponse(BaseModel):
    message: str
    details: Dict[str, Any] | List[Dict[str, Any]] | None


class DataSourceAPIGenericInput(BaseModel):
    datasource_id: uuid.UUID


class DatasourceIDRequest(BaseModel):
    datasource_name: str
    name_type: str = "generic"


class DatasourceIDResponse(BaseModel):
    message: str
    details: Dict[Any, Any]
