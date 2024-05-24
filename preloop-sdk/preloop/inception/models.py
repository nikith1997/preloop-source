from pydantic import BaseModel, Field


class SQLConnectionParams(BaseModel):
    user_name: str
    host_name: str
    port_number: int
    database_name: str
    table_name: str
    schema_name: str | None = None


class SQLAuthParams(BaseModel):
    password: str


class SQLConnectionDetails(BaseModel):
    connection_params: SQLConnectionParams
    auth_params: SQLAuthParams


class PostgresConnectionParams(SQLConnectionParams):
    pass


class PostgresAuthParams(SQLAuthParams):
    pass


class PostgresConnectionDetails(SQLConnectionDetails):
    connection_params: PostgresConnectionParams
    auth_params: PostgresAuthParams


class S3ConnectionDetails(BaseModel):
    bucket_name: str
    object_key: str


class Datasource(BaseModel):
    datasource_name: str
    datasource_description: str = Field(
        title="The description of the datasource", max_length=400, default="Description of this datasource."
    )
    connection_details: PostgresConnectionDetails | S3ConnectionDetails


class PostgresDatasource(Datasource):
    connection_details: PostgresConnectionDetails


class S3Datasource(Datasource):
    connection_details: S3ConnectionDetails
