import os
import uuid
from enum import Enum

import boto3
import pandas as pd
from preloop_private_api_stubs import (
    GetDatasourceIdRequest,
    ListDatasourcesRequest,
    PreloopPrivateClient,
    SQLAuthParams,
    SQLConnectionDetails,
    SQLConnectionParams,
)
from pydantic import BaseModel, Field

preloop_client = PreloopPrivateClient()
s3_client = boto3.client("s3")


class DatasourceType(str, Enum):
    """
    Enum restricting the datasources that are used by Preloop. Please
    expand this enum as we add in more data sources.
    """

    POSTGRES = "postgres"
    MYSQL = "mysql"
    S3 = "s3"


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
    datasource_type: DatasourceType
    connection_details: PostgresConnectionDetails | S3ConnectionDetails
    execution_id: uuid.UUID = os.getenv("EXECUTION_ID")

    @staticmethod
    def get_data(datasource_name: str):
        pass


class PostgresDatasource(Datasource):
    datasource_type: DatasourceType = DatasourceType.POSTGRES
    connection_details: PostgresConnectionDetails

    @staticmethod
    def get_data(datasource_name: str):
        datasource_id = preloop_client.get_datasource_id(
            GetDatasourceIdRequest(datasource_name=datasource_name)
        ).details["datasource_id"]
        datasource_details = preloop_client.list_datasources(
            ListDatasourcesRequest(datasource_id=datasource_id)
        ).datasources[0]
        datasource_details = datasource_details.model_dump()
        connection_details = datasource_details["connection_details"]
        if not datasource_details["datasource_type"] == DatasourceType.POSTGRES.value:
            raise TypeError("Datasource must be of type Postgres")
        connection_string = f"postgresql://{connection_details['connection_params']['user_name']}:{connection_details['auth_params']['password']}@{connection_details['connection_params']['host_name']}:{connection_details['connection_params']['port_number']}/{connection_details['connection_params']['database_name']}"
        df = pd.read_sql_table(
            connection_details["connection_params"]["table_name"],
            connection_string,
            schema=connection_details["connection_params"]["schema_name"],
        )
        return df


class S3Datasource(Datasource):
    datasource_type: DatasourceType = DatasourceType.S3
    connection_details: S3ConnectionDetails

    @staticmethod
    def get_data(datasource_name: str):
        datasource_id = preloop_client.get_datasource_id(
            GetDatasourceIdRequest(datasource_name=datasource_name)
        ).details["datasource_id"]
        datasource_details = preloop_client.list_datasources(
            ListDatasourcesRequest(datasource_id=datasource_id)
        ).datasources[0]
        datasource_details = datasource_details.model_dump()
        connection_details = datasource_details["connection_details"]
        if not datasource_details["datasource_type"] == DatasourceType.S3.value:
            raise TypeError("Datasource must be of type S3")
        s3_response = s3_client.get_object(
            Bucket=connection_details["bucket_name"], Key=connection_details["object_key"]
        )
        if connection_details["object_key"].split(".")[-1] == "csv":
            df = pd.read_csv(s3_response["Body"])
        elif connection_details["object_key"].split(".")[-1] == "parquet":
            df = pd.read_parquet(s3_response["Body"])
        else:
            raise ValueError("Unsupported file type")
        return df
