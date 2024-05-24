"""
This module contains classes and methods to provide 
functionality to the Preloop datasource API. 
"""
import hashlib
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import boto3
import pandas as pd
import sqlparse
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, create_engine, exc, or_, text
from sqlparse.sql import Identifier, IdentifierList
from sqlparse.tokens import DML, Keyword

from src.auth import utilities as auth_utilities
from src.common import are_credentials_valid
from src.database import AllUsers, Datasource, Feature, Session
from src.team import utilities as team_utilities

from .models import (
    CreateDatasourceRequest,
    DataSource,
    DataSourceType,
    S3ConnectionDetails,
    SQLConnectionDetails,
)

log = logging.getLogger("uvicorn")

# code to make sure valid sql is being passed
def is_subselect(parsed):
    if not parsed.is_group:
        return False
    for item in parsed.tokens:
        if item.ttype is DML and item.value.upper() == "SELECT":
            return True
    return False


def extract_from_part(parsed):
    from_seen = False
    for item in parsed.tokens:
        if from_seen:
            if is_subselect(item):
                yield from extract_from_part(item)
            elif item.ttype is Keyword:
                return
            else:
                yield item
        elif item.ttype is Keyword and item.value.upper() == "FROM":
            from_seen = True


def extract_table_identifiers(token_stream):
    for item in token_stream:
        if isinstance(item, IdentifierList):
            for identifier in item.get_identifiers():
                yield identifier.get_name()
        elif isinstance(item, Identifier):
            yield item.get_name()
        # It's a bug to check for Keyword here, but in the example
        # above some tables names are identified as keywords...
        elif item.ttype is Keyword:
            yield item.value


def extract_tables(sql):
    stream = extract_from_part(sqlparse.parse(sql)[0])
    return list(extract_table_identifiers(stream))


def datasource_name_exists(org_id: uuid.UUID, datasource_name: str) -> bool:
    """
    Checks if the datasource name already exists, and returns a boolean result.
    """
    with Session.begin() as session:
        user_ids = (
            session.query(AllUsers.user_id).filter(AllUsers.org_id == org_id).all()
        )
        user_ids = [user_id[0] for user_id in user_ids]

        query_results = (
            session.query(Datasource)
            .filter(
                and_(
                    Datasource.datasource_name_generic == datasource_name,
                    Datasource.user_id.in_(user_ids),
                )
            )
            .count()
        )
        if query_results > 0:
            return True
        else:
            return False


class DataSourceCore:
    """
    This class contains important variables and methods to
    interact with a datasource, which is a primitive in Preloop.
    Using a datasource, we can construct features and subsequently
    datasets that can be used by downstream processes, and consumers
    such as Data Scientists and ML engineers.
    """

    def __init__(
        self, user_id: str = None, org_id: str = None, role: str = None
    ) -> None:
        with Session.begin() as session:
            self.user_id = user_id
            self.org_id = org_id
            self.role = role

            query_results = (
                session.query(Datasource)
                .filter((Datasource.user_id == self.user_id))
                .all()
            )
            own_datasources = [
                {
                    **{
                        key: datasource.__dict__[key]
                        for key in datasource.__dict__
                        if not key.startswith("_sa_")
                    },
                    "team": "own",
                }
                for datasource in query_results
            ]

            team = team_utilities.TeamCore(user_id, org_id, role)
            teams_and_datasource_ids = team.get_shared_datasource_ids()

            # get the team datasource details. Set the "team"
            #  dict key to the team name from the function
            team_datasources = []
            for team, datasource_ids in teams_and_datasource_ids.items():
                query_results = (
                    session.query(Datasource)
                    .filter(Datasource.id.in_(datasource_ids))
                    .all()
                )
                team_datasources.extend(
                    [
                        {
                            **{
                                key: datasource.__dict__[key]
                                for key in datasource.__dict__
                                if not key.startswith("_sa_")
                            },
                            "team": team,
                        }
                        for datasource in query_results
                    ]
                )

            self.list_of_datasources = own_datasources + team_datasources

    # the methods below are primarily used to connect to and create a new
    # datasource
    def connect_to_datasource(
        self,
        datasource_type: str,
        connection_params: Dict[str, Any],
        auth_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        This method connects to a datasource and returns a list of rows and
        the schema along with the data types of each field.

        Inputs:
            datasource_type (str): A string indicating where the data
            originates from. For now, Postgres is the only source supported.

            connection_params (dict): Params required to connect to the given data source.

            auth_params (dict): The authorization params, usually a password.
            TODO: hash this

        Returns:
            A dictionary containing the column names, data types and first 5 rows of
            the given dataset.
        """
        if datasource_type == DataSourceType.POSTGRES:
            # get the variables that we need to construct the string
            user_name = connection_params["user_name"]
            host_name = connection_params["host_name"]
            port = connection_params["port_number"]
            database_name = connection_params["database_name"]
            passwd = auth_params["password"]

            connection_string = (
                f"postgresql://{user_name}:{passwd}@{host_name}:{port}/{database_name}"
            )
            engine_datasource = create_engine(connection_string)

            if are_credentials_valid(engine_datasource.url) == False:
                raise ConnectionError("Connection failed")

            with engine_datasource.begin() as datasource_connection:

                if connection_params["schema_name"] is not None:
                    table_name = (
                        connection_params["schema_name"]
                        + "."
                        + connection_params["table_name"]
                    )
                    table_only = connection_params["table_name"]
                    schema_only = connection_params["schema_name"]

                    # get the schema of the datasource
                    schema_query = text(
                        "select column_name, data_type from \
                                        information_schema.columns where table_name =:table_name \
                                        and table_schema =:schema_name; \
                                        "
                    )
                    results = datasource_connection.execute(
                        schema_query,
                        {"table_name": table_only, "schema_name": schema_only},
                    )
                    if results.rowcount == 0:
                        raise exc.NoSuchTableError(
                            f"The table {table_name} does not exist in the database"
                        )
                else:
                    table_name = connection_params["table_name"]
                    table_only = connection_params["table_name"]

                    schema_query = text(
                        "select column_name, data_type from \
                                        information_schema.columns where table_name =:table_name; \
                                        "
                    )
                    results = datasource_connection.execute(
                        schema_query, {"table_name": table_only}
                    )
                    if results.rowcount == 0:
                        raise exc.NoSuchTableError(
                            f"The table {table_name} does not exist in the database"
                        )

                self.datasource_schema = {x[0]: x[1] for x in results.fetchall()}

                # get and store a preview of the data
                preview_query = text(f"select * from {table_name} limit 5;")
                results = datasource_connection.execute(preview_query)
                results = results.mappings().all()
                results = [dict(result) for result in results]
                self.datasource_preview = results

        return {
            "schema_and_types": self.datasource_schema,
            "datasource_preview": self.datasource_preview,
        }

    def create_sql_datasource(
        self, sql_datasource: CreateDatasourceRequest
    ) -> uuid.UUID:
        """
        This method is used to create a new datasource and add it to the
        Preloop database. If the datasource already exists,then an error
        will be raised.

        Inputs:
            datasource_details (DataSource): A parameter that contains the
            values required to load a given datasource. At this point of time,
            only Postgres is supported.

        Returns:
            None
        """
        if not isinstance(sql_datasource.connection_details, SQLConnectionDetails):
            raise TypeError(
                "The connection details must be of type SQLConnectionDetails"
            )
        connection_params = (
            sql_datasource.connection_details.connection_params.model_dump()
        )
        auth_params = sql_datasource.connection_details.auth_params.model_dump()
        try:
            schema_and_preview = self.connect_to_datasource(
                sql_datasource.datasource_type, connection_params, auth_params
            )
        except ConnectionError as e:
            raise ValueError(
                f"Could not connect to datasource with name {sql_datasource.datasource_name}. Please check the connection details and try again."
            )
        except exc.NoSuchTableError as e:
            raise ValueError(e.args[0])
        variables = sql_datasource.model_dump()
        hash_obj = hashlib.sha256()

        # Update the hash object with the JSON-encoded string of each parameter
        hash_obj.update(json.dumps(connection_params).encode())
        hash_obj.update(json.dumps(auth_params).encode())
        hash_obj.update(json.dumps(schema_and_preview["schema_and_types"]).encode())

        # define datasource_details field
        datasource_details = {
            "schema_and_types": schema_and_preview["schema_and_types"]
        }

        # Get the hexadecimal digest of the hash
        variables["hashed_value"] = hash_obj.hexdigest()

        with Session.begin() as session:
            # check if dataset exists already. If it does, then return an error message
            is_name_exist = datasource_name_exists(
                self.org_id, variables["datasource_name"]
            )

            if is_name_exist:
                raise ValueError("Datasource name already exists.")

            try:
                new_datasource = DataSource(
                    user_id=self.user_id,
                    datasource_name_script=variables["datasource_name"],
                    datasource_name_generic=variables["datasource_name"],
                    datasource_description=variables["datasource_description"],
                    connection_details=variables["connection_details"],
                    datasource_type=variables["datasource_type"],
                    datasource_details=datasource_details,
                    hashed_value=variables["hashed_value"],
                    execution_id=variables["execution_id"],
                )
                datasource_orm_obj = Datasource(**new_datasource.model_dump())
                session.add(datasource_orm_obj)
                session.flush()
                session.refresh(datasource_orm_obj)

            except ValidationError as e:
                raise e

            except exc.SQLAlchemyError as e:
                raise e

            return {
                "returned_message": "The datasource was created successfully",
                "id": datasource_orm_obj.id,
                "preview_of_data": schema_and_preview["datasource_preview"],
            }

    def create_s3_datasource(self, s3_datasource: CreateDatasourceRequest) -> uuid.UUID:
        """
        This method is used to create a new s3 datasource and add it to the
        Preloop database. If the datasource already exists,then an error
        will be raised.

        Inputs:
            s3_datasource (CreateS3DatasourceRequest)

        Returns:
            datasource_id (uuid.UUID)
        """
        if not isinstance(s3_datasource.connection_details, S3ConnectionDetails):
            raise TypeError(
                "The connection details must be of type S3ConnectionDetails"
            )
        if not (
            s3_datasource.connection_details.object_key.endswith(".csv")
            or s3_datasource.connection_details.object_key.endswith(".parquet")
        ):
            raise ValueError("The object key must be a csv or parquet file")
        try:
            boto3.client("s3").get_object(
                Bucket=s3_datasource.connection_details.bucket_name,
                Key=s3_datasource.connection_details.object_key,
            )
        except Exception as e:
            log.error(str(e), exc_info=True)
            raise ValueError(
                f"Unable to connect to s3 datasource with name {s3_datasource.datasource_name}. Please check the connection details and try again. (Could also be a permissions issue)"
            )
        with Session.begin() as session:
            # check if dataset exists already. If it does, then return an error message
            is_name_exist = datasource_name_exists(
                self.org_id, s3_datasource.datasource_name
            )

            if is_name_exist:
                raise ValueError("Datasource name already exists.")

            try:
                new_datasource = DataSource(
                    user_id=self.user_id,
                    datasource_name_script=s3_datasource.datasource_name,
                    datasource_name_generic=s3_datasource.datasource_name,
                    datasource_description=s3_datasource.datasource_description,
                    connection_details=s3_datasource.connection_details,
                    datasource_type=s3_datasource.datasource_type,
                    execution_id=s3_datasource.execution_id,
                )
                new_datasource = Datasource(**new_datasource.model_dump())
                session.add(new_datasource)
                session.flush()
                session.refresh(new_datasource)

            except exc.SQLAlchemyError as e:
                raise e

            return {
                "returned_message": "The datasource was created successfully",
                "id": new_datasource.id,
            }

    def create_datasource(self, datasource: CreateDatasourceRequest) -> uuid.UUID:
        if datasource.datasource_type == DataSourceType.POSTGRES:
            return self.create_sql_datasource(datasource)
        if datasource.datasource_type == DataSourceType.S3:
            return self.create_s3_datasource(datasource)

    def list_datasources(self) -> list:
        """
        Lists all the datasources for a given customer. In the future,
        we will enable fine grained permissions to allow user level
        control, but at this point that is not enabled.

        Inputs:
           None

        Returns:
            A list of dictionaries containing all the datasources for that customer.
        """
        results = self.list_of_datasources
        for result in results:
            result["datasource_name"] = result["datasource_name_generic"]
            del result["datasource_name_generic"]
            del result["datasource_name_script"]

        return results

    def return_datasource_details(self, datasource_id: uuid.UUID) -> dict:
        """
        This method returns data for a given datasource for a given customer.

        Inputs:
            None
        """
        with Session.begin() as session:
            results = (
                session.query(Datasource)
                .filter(
                    and_(
                        Datasource.id == datasource_id,
                        Datasource.user_id == self.user_id,
                    )
                )
                .all()
            )
            if results == []:
                team = team_utilities.TeamCore(self.user_id, self.org_id, self.role)
                datasource_id_teams = team.get_shared_datasource_ids()
                for team, datasource_ids in datasource_id_teams.items():
                    if datasource_id in datasource_ids:
                        results = (
                            session.query(Datasource)
                            .filter(Datasource.id == datasource_id)
                            .all()
                        )
                        results = [
                            {
                                **{
                                    key: datasource.__dict__[key]
                                    for key in datasource.__dict__
                                    if not (
                                        key.startswith("_sa_")
                                        or key == "datasource_name_script"
                                    )
                                },
                                "team": team,
                            }
                            for datasource in results
                        ]
                        for result in results:
                            result["datasource_name"] = result[
                                "datasource_name_generic"
                            ]
                            del result["datasource_name_generic"]

                        return results

                    if results == []:
                        return []

            results = [
                {
                    **{
                        key: datasource.__dict__[key]
                        for key in datasource.__dict__
                        if not (
                            key.startswith("_sa_") or key == "datasource_name_script"
                        )
                    },
                    "team": "own",
                }
                for datasource in results
            ]

            for result in results:
                result["datasource_name"] = result["datasource_name_generic"]
                del result["datasource_name_generic"]

            return results

    def delete_datasource(self, datasource_id) -> None:
        """
        Method to delete datasource for a given customer id and dataset name.

        Inputs:
            None

        Returns:
            None
        """
        with Session.begin() as session:
            item = (
                session.query(Datasource)
                .filter(
                    and_(
                        Datasource.id == datasource_id,
                        Datasource.user_id == self.user_id,
                    )
                )
                .first()
            )

            # check if any features are using this datasource
            datasource_id = item.id
            dependency_check = (
                session.query(Feature.datasource_ids)
                .filter(Feature.user_id == self.user_id)
                .all()
            )
            for row in dependency_check:
                if str(datasource_id) in row[0]:
                    raise ValueError("Datasource dependency detected")

            session.delete(item)
            return

    def modify_datasource(self, params_to_modify: dict, datasource_id: str) -> None:
        """
        Method to modify the various parameters of a dataset.
        It is important to note that connection_params,
        auth_params, datasource_name, datasource_type,
        customer_id, user_id, schema and last_run_status cannot be changed.
        Only the datasource_description, update_freq,
        locally_cached, dest_loc and config_file can.

        Input:
            params_to_modify (dict): list of params that need to modified.

        Returns:
            None
        """
        with Session.begin() as session:
            row_to_modify = (
                session.query(Datasource)
                .filter(
                    and_(
                        Datasource.id == datasource_id,
                        Datasource.user_id == self.user_id,
                    )
                )
                .first()
            )

            if row_to_modify is None:
                raise exc.NoResultFound

            datasource_type = getattr(row_to_modify, "datasource_type")

            if any(
                field in params_to_modify.keys() for field in ["connection_details"]
            ):
                if getattr(row_to_modify, "datasource_type") == DataSourceType.POSTGRES:
                    connection_details = getattr(row_to_modify, "connection_details")
                    connection_params_existing = connection_details["connection_params"]
                    auth_params_existing = connection_details["auth_params"]

                    schema_existing = self.connect_to_datasource(
                        datasource_type,
                        connection_params_existing,
                        auth_params_existing,
                    )["schema_and_types"]

                    connection_params_new = params_to_modify["connection_details"][
                        "connection_params"
                    ]
                    auth_params_new = params_to_modify["connection_details"][
                        "auth_params"
                    ]

                    schema_new = self.connect_to_datasource(
                        datasource_type, connection_params_new, auth_params_new
                    )["schema_and_types"]

                    if schema_existing != schema_new:
                        raise ValueError(
                            "Schema mismatch detected. Please check your connection params and auth params."
                        )

            for key, value in params_to_modify.items():
                setattr(row_to_modify, key, value)

        return

    def get_datasource(self, datasource_id: str) -> pd.DataFrame:
        """
        Method to return a pandas dataframe for the given datasource.
        This dataframe is then further processed and used to construct
        features.

        Inputs:
            datasource_id (str): The id of the datasource.

        Returns:
            A pandas dataframe with the filtered data.
        """
        with Session.begin() as session:
            datasource_details = (
                session.query(Datasource)
                .filter(
                    and_(
                        Datasource.id == datasource_id,
                        Datasource.user_id == self.user_id,
                    )
                )
                .first()
            )

            if datasource_details is None:
                # see if it's a shared datasource. If yes, then return the datasource details
                datasource_id_teams = team_utilities.TeamCore(
                    self.user_id, self.org_id, self.role
                ).get_shared_datasource_ids()
                datasource_ids = datasource_id_teams.values().flatten()

                if datasource_id in datasource_ids:
                    datasource_details = (
                        session.query(Datasource)
                        .filter(Datasource.id == datasource_id)
                        .first()
                    )

                else:
                    raise ValueError(
                        f"The datasource with id {datasource_id} doesn't exist"
                    )

            connection_params = getattr(datasource_details, "connection_params")
            auth_params = getattr(datasource_details, "auth_params")
            schema_name = connection_params["schema_name"]
            table_name = connection_params["table_name"]

            if schema_name is not None:
                sql_string = f"select *from {schema_name}.{table_name}"
            else:
                sql_string = f"select *from {table_name}"

            connection_string = f"postgresql://{connection_params['user_name']}:{auth_params['password']}@{connection_params['host_name']}:{connection_params['port_number']}/{connection_params['database_name']}"
            engine_datasource = create_engine(connection_string)

            with engine_datasource.begin() as datasource_connection:
                # get the schema of the datasource
                query = text(sql_string)
                results = datasource_connection.execute(query)
                results = results.mappings().all()
                results = [dict(result) for result in results]
                results = pd.DataFrame(results)
                return results

    def get_datasource_id(
        self, datasource_name: str, name_type: str = "generic"
    ) -> str:
        """
        A method to return the datasource id for a given datasource name.

        Inputs:
            datasource_name (str): The name of a given datasource

        Returns:
            datasource_id (str): The id for the given datasource
        """
        with Session.begin() as session:
            own_plus_team_user_ids = [self.user_id]
            user_ids_team_members = team_utilities.TeamCore(
                self.user_id, self.org_id, self.role
            )._get_user_ids_of_team_members_other_than_self()
            user_ids_team_members = user_ids_team_members.values()
            for user_id_list in user_ids_team_members:
                own_plus_team_user_ids.extend(user_id_list)

            if name_type == "generic":
                result = (
                    session.query(Datasource)
                    .filter(
                        and_(
                            Datasource.user_id.in_(own_plus_team_user_ids),
                            Datasource.datasource_name_generic == datasource_name,
                        )
                    )
                    .first()
                )

            elif name_type == "script":
                result = (
                    session.query(Datasource)
                    .filter(
                        and_(
                            Datasource.user_id.in_(own_plus_team_user_ids),
                            Datasource.datasource_name_script == datasource_name,
                        )
                    )
                    .first()
                )

            # return value error if result is empty
            if result is None:
                raise ValueError(
                    f"The datasource with name {datasource_name} does not exist, or you don't have access to it"
                )

            return result.id

    def clean_up_created_datasources(self, created_datasource_ids: List[str]):
        for datasource_id in created_datasource_ids:
            try:
                self.delete_datasource(datasource_id=datasource_id)
            except exc.NoResultFound as e:
                log.error(f"Datasource {datasource_id} does not exist", exc_info=True)
            except AttributeError as e:
                log.error(f"Datasource {datasource_id} does not exist", exc_info=True)
