"""
This module contains classes and methods to provide
functionality to the Preloop feature API
"""
import ast
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import boto3
import botocore
from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy import Table, and_, create_engine, exc, func, or_, text

import src.feature.models as models
from src.api_key_management.utilities import get_internal_api_key
from src.database import (
    AllUsers,
    Datasource,
    Executions,
    Feature,
    FeatureDrift,
    FeatureVersions,
    Session,
    metadata,
)
from src.feature.constants import Constants
from src.feature.models import Feature as FeatureModel
from src.team import utilities as team_utilities

log = logging.getLogger("uvicorn")


def feature_name_exists(org_id: uuid.UUID, feature_name: str) -> bool:
    """
    Checks if the feature name already exists, and returns a boolean result.
    """
    with Session.begin() as session:
        user_ids = (
            session.query(AllUsers.user_id).filter(AllUsers.org_id == org_id).all()
        )
        user_ids = [user_id[0] for user_id in user_ids]

        query_results = (
            session.query(Feature)
            .filter(
                and_(
                    Feature.feature_name_generic == feature_name,
                    Feature.user_id.in_(user_ids),
                )
            )
            .count()
        )
        if query_results > 0:
            return True
        else:
            return False


class FeatureCore:
    """
    Important variables, and methods to
    interact with a feature. A feature, is generated from
    a datasource and is used to generate datasets that are
    used in various ML and analytical tasks.
    """

    def __init__(self, user_id: str, org_id: str, role: str):
        with Session.begin() as session:
            self.user_id = user_id
            self.org_id = org_id
            self.role = role

            query_results = (
                session.query(Feature).filter((Feature.user_id == self.user_id)).all()
            )
            own_features = [
                {
                    **{
                        key: feature.__dict__[key]
                        for key in feature.__dict__
                        if not key.startswith("_sa_")
                    },
                    "team": "own",
                }
                for feature in query_results
            ]

            team = team_utilities.TeamCore(user_id, org_id, role)
            teams_and_feature_ids = team.get_shared_feature_ids()

            # get the team feature details. Set the "team"
            #  dict key to the team name from the function
            team_features = []

            for team, feature_ids in teams_and_feature_ids.items():
                query_results = (
                    session.query(Feature).filter((Feature.id.in_(feature_ids))).all()
                )
                team_features.extend(
                    [
                        {
                            **{
                                key: feature.__dict__[key]
                                for key in feature.__dict__
                                if not key.startswith("_sa_")
                            },
                            "team": team,
                        }
                        for feature in query_results
                    ]
                )

            self.list_of_features = own_features + team_features

    def create_feature(self, feature: FeatureModel):
        """
        This method creates a new feature, which involves two main steps.
        The first step is writing the record to the database, and the
        second step is executing the script to create the feature. The
        script will need to be run according to the schedule specified by
        the user, and in most cases, we expect this to be a recurring action.

        Inputs:
            features (Feature): A Feature type containing details of the feature.

        Returns:
            jobid if successful, or error messages otherwise.
        """
        with Session.begin() as session:
            # check if dataset exists already. If it does, then return an error message
            is_name_exist = feature_name_exists(self.org_id, feature.feature_name)

            if is_name_exist:
                raise ValueError("Feature name already exists.")

            dict_to_insert = feature.model_dump()

            datasource_ids = []
            for datasource in dict_to_insert["datasource_names"]:
                datasource_id = self.get_datasource_id(datasource)
                datasource_ids.append(datasource_id)

            dict_to_insert["datasource_ids"] = datasource_ids

            # drop the datasource_names key from the dictionary
            dict_to_insert.pop("datasource_names")
            dict_to_insert["feature_name_generic"] = dict_to_insert["feature_name"]
            dict_to_insert["feature_name_script"] = dict_to_insert["feature_name"]
            dict_to_insert.pop("feature_name")
            try:
                new_feature = Feature(**dict_to_insert)
                session.add(new_feature)
                session.flush()
                session.refresh(new_feature)

                schema_name = f"features_{str(self.user_id).replace('-','_')}"
                table_name = str(new_feature.id).replace("-", "_")
                location_string = schema_name + "." + table_name
                new_feature.location_string = location_string

                obj_dict = {
                    key: value
                    for key, value in new_feature.__dict__.items()
                    if not key.startswith("_")
                }

            except ValidationError as e:
                raise e

            except exc.SQLAlchemyError as e:
                raise e

            return obj_dict

    def list_features(self) -> list:
        """
        Lists all the features for a given customer. In the future,
        we will enable fine grained permission to allow user level
        control, but this isn't enabled at this point.

        Inputs:
            None

        Returns:
            A list of dictionaries containing all the datasources for that customer.
        """
        results = self.list_of_features

        for result in results:
            result["feature_name"] = result["feature_name_generic"]
            del result["feature_name_generic"]
            del result["feature_name_script"]

        return results

    def modify_feature(self, params_to_modify: dict, feature_id: str):
        """
        Method to modify the various parameters of a feature. This enables
        the user to modify certain fields in the feature table for the
        given feature. Features that can be modified include feature
        description, feature_type, is_target, update_freq.

        Inputs:
            params_to_modify (dict): A dictionary that contains the
                parameters that need to be modified.

            feature_name (str): The name of the feature for which
                modifications will need to be made.

        Returns:
            None
        """
        details = {}
        with Session.begin() as session:
            row_to_modify = (
                session.query(Feature)
                .filter(and_(Feature.user_id == self.user_id, Feature.id == feature_id))
                .first()
            )
            if row_to_modify is None:
                raise exc.NoResultFound(
                    f"Feature with feature_id {feature_id} doesn't exist"
                )

            for key in params_to_modify:
                if key == "feature_description":
                    setattr(row_to_modify, key, params_to_modify[key])
                    details[key] = "succeeded"
                if key == "scheduling_expression_string":
                    scheduling_expression_array = params_to_modify[key].split(" ")
                    if len(scheduling_expression_array) != 6:
                        details[
                            key
                        ] = "failed, scheduling expression must have 6 fields"
                        continue
                    scheduler_client = boto3.client("scheduler")
                    try:
                        scheduler_response = scheduler_client.get_schedule(
                            Name=str(row_to_modify.execution_id)
                        )
                        scheduler_response[
                            "ScheduleExpression"
                        ] = f"cron({params_to_modify[key]})"
                        try:
                            scheduler_client.update_schedule(scheduler_response)
                        except scheduler_client.exceptions.ValidationException as e:
                            details[
                                key
                            ] = "failed, scheduling expression is invalid cron syntax"
                            continue
                    except scheduler_client.exceptions.ResourceNotFoundException as e:
                        log.info(
                            f"The schedule for feature {row_to_modify.id} does not exist, creating a schedule"
                        )
                        internal_api_key = get_internal_api_key(self.user_id)
                        scheduler_input = {
                            "SCRIPT_LOC": row_to_modify.script_loc,
                            "KEY_ID": internal_api_key["key_id"],
                            "SECRET": internal_api_key["secret"],
                            "SCHEDULING_EXPRESSION": f"cron({params_to_modify[key]})",
                            "VERSIONING": str(row_to_modify.versioning),
                            "EXECUTION_TYPE": models.ExecutionType.SCHEDULED.value,
                            "EXECUTION_ID": None,
                        }
                        try:
                            scheduler_client.create_schedule(
                                FlexibleTimeWindow={"Mode": "OFF"},
                                Name=str(row_to_modify.execution_id),
                                ScheduleExpression=f"cron({params_to_modify[key]})",
                                State="ENABLED",
                                Target={
                                    "Arn": f"arn:aws:lambda:{os.getenv('AWS_DEFAULT_REGION')}:{os.getenv('AWS_ACCOUNT_ID')}:function:ExecutionEngineLambda",
                                    "Input": json.dumps(scheduler_input),
                                    "RoleArn": f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/execution-engine-scheduler-role",
                                },
                            )
                        except scheduler_client.exceptions.ValidationException as e:
                            details[
                                key
                            ] = f"The provided scheduling expression {params_to_modify[key]} is not valid cron syntax"
                            continue
                    setattr(row_to_modify, key, params_to_modify[key])
                    details[key] = "succeeded"
            return details

    def return_feature_details(self, feature_id: str) -> List[dict]:
        """
        This method returns data for a given feature for a given customer.

        Inputs:
            feature_name (str): The name of a feature.

        Returns:
            List of dictionary, where there is a single dictionary containing
                details of the feature.
        """
        with Session.begin() as session:
            results = (
                session.query(Feature)
                .filter(and_(Feature.id == feature_id, Feature.user_id == self.user_id))
                .all()
            )
            if results == []:
                team = team_utilities.TeamCore(self.user_id, self.org_id, self.role)
                feature_id_teams = team.get_shared_feature_ids()
                for team, feature_ids in feature_id_teams.items():
                    if feature_id in feature_ids:
                        results = (
                            session.query(Feature)
                            .filter(and_(Feature.id == feature_id))
                            .all()
                        )
                        results = [
                            {
                                **{
                                    key: feature.__dict__[key]
                                    for key in feature.__dict__
                                    if not (
                                        key.startswith("_sa_")
                                        or key == "feature_name_script"
                                    )
                                },
                                "team": team,
                            }
                            for feature in results
                        ]
                        for result in results:
                            result["feature_name"] = result["feature_name_generic"]
                            del result["feature_name_generic"]

                        return results

                    if results == []:
                        return []

            results = [
                {
                    **{
                        key: feature.__dict__[key]
                        for key in feature.__dict__
                        if not (key.startswith("_sa_") or key == "feature_name_script")
                    },
                    "team": "own",
                }
                for feature in results
            ]
            for result in results:
                result["feature_name"] = result["feature_name_generic"]
                del result["feature_name_generic"]

            return results

    def delete_feature(self, feature_id: str):
        """
        This method deletes a feature from the database and additionally
        takes care of removing all scripts and recurring processes that
        are associated with that feature.

        Inputs:
            feature_id (str): The name of the feature to remove

        Returns:
            None
        """
        scheduler_client = boto3.client("scheduler")
        s3_client = boto3.client("s3")
        feature_dict = {}
        with Session.begin() as session:
            feature_data = (
                session.query(Feature)
                .filter(and_(Feature.user_id == self.user_id, Feature.id == feature_id))
                .first()
            )
            if feature_data is None:
                raise exc.NoResultFound(f"Feature with {feature_id} not found")
            feature_dict = {
                "feature_id": feature_data.id,
                "execution_id": feature_data.execution_id,
                "location_string": feature_data.location_string,
            }
            # Delete schedule
            try:
                scheduler_client.delete_schedule(Name=str(feature_dict["execution_id"]))
            except scheduler_client.exceptions.ResourceNotFoundException:
                log.info(
                    f"The schedule for feature {feature_dict['feature_id']} does not exist, continuing"
                )
            except Exception as e:
                log.error(str(e))
                raise
            # Delete script
            try:
                s3_client.delete_object(
                    Bucket=Constants.S3_FEATURE_SCRIPTS_BUCKET,
                    Key=f"{self.user_id}/{feature_dict['execution_id']}.py",
                )
            except Exception as e:
                log.error(str(e))
                raise
            # Delete feature data
            location_string_components = feature_dict["location_string"].split(".")
            try:
                feature_data_table = Table(
                    location_string_components[1],
                    metadata,
                    schema=location_string_components[0],
                )
                feature_data_table.drop(bind=session.bind)
            except Exception as e:
                log.error(str(e))
                raise
            # Delete Feature
            session.query(Feature).filter(
                and_(Feature.user_id == self.user_id, Feature.id == feature_id)
            ).delete()

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

    def check_valid_get_feature_request(self, feature_id: str, version: int) -> bool:
        """
        This method checks if a given feature exists for a given customer.

        Inputs:
            feature_id (str): The id of the feature.
            version (int): The version of the feature.

        Returns:
            True if the feature exists, False otherwise.
        """
        with Session.begin() as session:
            query = session.query(FeatureVersions).filter(
                and_(
                    FeatureVersions.feature_id == feature_id,
                    FeatureVersions.version == version,
                )
            )
            if query.count() == 0:
                return False

            return True

    def signature_search(self, signature: str) -> str:
        """Check if a feature signature exists. If it does, return feature name and id."""
        with Session.begin() as session:
            query = (
                session.query(Feature)
                .filter(
                    and_(
                        Feature.user_id == self.user_id,
                        Feature.feature_signature == signature,
                    )
                )
                .first()
            )

            if query is None:
                return None

            return {
                "feature_name": query.feature_name_generic,
                "feature_id": query.id,
                "location_string": query.location_string,
                "latest_version": query.latest_version,
            }

    def get_feature_id(self, feature_name: str, name_type: str = "generic") -> str:
        """
        A method to return the feature id for a given feature name.

        Inputs:
            feature_name (str): The name of a given feature

        Returns:
            feature_id (str): The id for the given feature
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
                    session.query(Feature)
                    .filter(
                        and_(
                            Feature.user_id.in_(own_plus_team_user_ids),
                            Feature.feature_name_generic == feature_name,
                        )
                    )
                    .first()
                )

            elif name_type == "script":
                result = (
                    session.query(Feature)
                    .filter(
                        and_(
                            Feature.user_id.in_(own_plus_team_user_ids),
                            Feature.feature_name_script == feature_name,
                        )
                    )
                    .first()
                )

            # return value error if result is empty
            if result is None:
                raise ValueError(
                    f"The feature with name {feature_name} does not exist, or you don't have access to it"
                )

            return result.id

    @staticmethod
    def validate_script_entities(script: UploadFile):
        """
        This method validates the script entities and ensures
        that unwanted entities that could compromise security
        are not present. Additionally, this method also validates
        syntax errors in the script.
        Inputs:
            script (UploadFile): The script to validate.

        Returns:
            None
        """
        file_obj = script.file
        file_obj.seek(0)
        code = file_obj.read().decode()
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise):
                raise ValueError(f"Feature script must not explicitly raise exceptions")

    def upload_feature_script_sync(
        self,
        script: UploadFile,
        scheduling_expression: str,
        versioning: bool,
        creation_method: str,
        feature_drift_enabled: bool,
    ):
        lambda_client = boto3.client("lambda")
        s3_client = boto3.client("s3")
        scheduler_client = boto3.client("scheduler")
        file_extension = script.filename.rsplit(".", 1)[1].lower()
        execution_id = uuid.uuid4()
        internal_api_key = get_internal_api_key(self.user_id)
        script_loc = f"s3://{Constants.S3_FEATURE_SCRIPTS_BUCKET}/{self.user_id}/{execution_id}.py"
        scheduler_input = None
        if file_extension != "py":
            raise TypeError("Script must be a python file")
        FeatureCore.validate_script_entities(script)
        if scheduling_expression is not None:
            scheduling_expression_array = scheduling_expression.split(" ")
            if len(scheduling_expression_array) != 6:
                raise ValueError("Scheduling expression must have 6 fields")
            scheduler_input = {
                "SCRIPT_LOC": script_loc,
                "KEY_ID": internal_api_key["key_id"],
                "SECRET": internal_api_key["secret"],
                "SCHEDULING_EXPRESSION": None,
                "VERSIONING": str(versioning),
                "EXECUTION_TYPE": models.ExecutionType.SCHEDULED.value,
                "EXECUTION_ID": None,
                "FEATURE_DRIFT_ENABLED": str(feature_drift_enabled),
                "ML_MODEL_TRAINING": None,
            }
            try:
                scheduler_client.create_schedule(
                    FlexibleTimeWindow={"Mode": "OFF"},
                    Name=str(execution_id),
                    ScheduleExpression=f"cron({scheduling_expression})",
                    State="DISABLED",
                    Target={
                        "Arn": f"arn:aws:lambda:{os.getenv('AWS_DEFAULT_REGION')}:{os.getenv('AWS_ACCOUNT_ID')}:function:ExecutionEngineLambda",
                        "Input": json.dumps(scheduler_input),
                        "RoleArn": f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/execution-engine-scheduler-role",
                    },
                )
            except Exception as e:
                raise ValueError(
                    f"The provided scheduling expression {scheduling_expression} is not valid cron syntax"
                )
        else:
            script.file.seek(0)
            s3_client.upload_fileobj(
                script.file,
                Constants.S3_FEATURE_SCRIPTS_BUCKET,
                f"{self.user_id}/{execution_id}.py",
            )
        lambda_payload = {
            "SCRIPT_LOC": script_loc,
            "KEY_ID": internal_api_key["key_id"],
            "SECRET": internal_api_key["secret"],
            "SCHEDULING_EXPRESSION": scheduling_expression,
            "VERSIONING": str(versioning),
            "EXECUTION_TYPE": models.ExecutionType.FIRST_RUN.value,
            "EXECUTION_ID": str(execution_id),
            "FEATURE_DRIFT_ENABLED": str(feature_drift_enabled),
            "ML_MODEL_TRAINING": None,
        }
        lambda_response = lambda_client.invoke(
            FunctionName=Constants.EXECUTION_ENGINE_LAMBDA_NAME,
            Payload=json.dumps(lambda_payload),
        )
        lambda_response_dict = json.loads(lambda_response["Payload"].read())
        with Session.begin() as session:
            dict_to_insert = {
                "id": execution_id,
                "user_id": self.user_id,
                "status": models.ExecutionStatus.PENDING.value,
                "execution_type": models.ExecutionType.FIRST_RUN.value,
            }
            session.add(Executions(**dict_to_insert))
        response_dict = {
            "state_machine_execution_arn": lambda_response_dict["body"]["executionArn"],
            "execution_id": str(execution_id),
            "scheduler_input": scheduler_input,
            "scheduling_expression": scheduling_expression,
        }
        return response_dict

    def upload_feature_script_async(
        self,
        state_machine_execution_arn: str,
        execution_id: str,
        scheduler_input: Dict,
        scheduling_expression: str,
        max_retries=100,
        retry_interval=15,
    ):
        sfn_client = boto3.client("stepfunctions")
        scheduler_client = boto3.client("scheduler")
        retries = 0
        try:
            while retries < max_retries:
                execution_response = sfn_client.describe_execution(
                    executionArn=state_machine_execution_arn
                )
                if execution_response["status"] == "FAILED":
                    raise Exception(execution_response["cause"])
                elif execution_response["status"] == "TIMED_OUT":
                    raise Exception(f"The execution {execution_id} has timed out")
                elif execution_response["status"] == "SUCCEEDED":
                    row_count = 0
                    with Session.begin() as session:
                        row_count = (
                            session.query(Feature)
                            .filter(
                                Feature.user_id == self.user_id,
                                Feature.execution_id == execution_id,
                            )
                            .count()
                        )
                    if row_count < 1:
                        raise Exception(
                            f"The execution {execution_id} did not create a feature"
                        )
                    else:
                        if scheduling_expression is not None:
                            scheduler_client.update_schedule(
                                FlexibleTimeWindow={"Mode": "OFF"},
                                Name=str(execution_id),
                                ScheduleExpression=f"cron({scheduling_expression})",
                                State="ENABLED",
                                Target={
                                    "Arn": f"arn:aws:lambda:{os.getenv('AWS_DEFAULT_REGION')}:{os.getenv('AWS_ACCOUNT_ID')}:function:ExecutionEngineLambda",
                                    "Input": json.dumps(scheduler_input),
                                    "RoleArn": f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/execution-engine-scheduler-role",
                                },
                            )
                        with Session.begin() as session:
                            row_to_modify = (
                                session.query(Executions)
                                .filter(
                                    Executions.user_id == self.user_id,
                                    Executions.id == execution_id,
                                )
                                .first()
                            )
                            setattr(
                                row_to_modify,
                                "status",
                                models.ExecutionStatus.SUCCEEDED.value,
                            )
                        log.info(f"Execution {execution_id} was successful")
                    break
                elif execution_response["status"] == "RUNNING":
                    log.info(f"Execution {execution_id} is currently running")
                    retries += 1
                    time.sleep(retry_interval)
            if retries == max_retries:
                raise Exception(f"The execution {execution_id} has timed out")
        except Exception as e:
            log.error(str(e))
            self.failed_execution_handler(execution_id, str(e))

    def failed_execution_handler(self, execution_id, failure_cause):
        log.error(f"Execution {execution_id} has failed, cleaning up resources")
        scheduler_client = boto3.client("scheduler")
        s3_client = boto3.client("s3")
        with Session.begin() as session:
            row_to_modify = (
                session.query(Executions)
                .filter(
                    Executions.user_id == self.user_id, Executions.id == execution_id
                )
                .first()
            )
            setattr(row_to_modify, "status", models.ExecutionStatus.FAILED.value)
            setattr(row_to_modify, "reason", failure_cause)
            session.query(Feature).filter(
                Feature.user_id == self.user_id, Feature.execution_id == execution_id
            ).delete()
            session.query(Datasource).filter(
                Datasource.user_id == self.user_id,
                Datasource.execution_id == execution_id,
            ).delete()
        try:
            scheduler_client.delete_schedule(Name=execution_id)
        except Exception as e:
            log.error(f"Schedule {execution_id} does not exist, ignoring")
        try:
            s3_client.delete_object(
                Bucket=Constants.S3_FEATURE_SCRIPTS_BUCKET,
                Key=f"{self.user_id}/{execution_id}.py",
            )
        except Exception as e:
            log.error(
                f"Script {self.user_id}/{execution_id}.py may have failed to delete"
            )
        log.error(f"Failed execution {execution_id} cleanup was successful")

    def list_feature_executions(self, execution_id=None):
        with Session.begin() as session:
            if execution_id is None:
                executions_list = (
                    session.query(Executions)
                    .filter(
                        Executions.user_id == self.user_id,
                        Executions.record_date
                        >= (datetime.utcnow() - timedelta(days=10)),
                    )
                    .all()
                )
            else:
                executions_list = (
                    session.query(Executions)
                    .filter(
                        Executions.user_id == self.user_id,
                        Executions.id == execution_id,
                        Executions.record_date
                        >= (datetime.utcnow() - timedelta(days=10)),
                    )
                    .all()
                )
                if executions_list == []:
                    raise exc.NoResultFound(f"Execution {execution_id} not found")
            # drop the _sa_instance_state and the user_id key from the dictionary
            executions_list = [
                {
                    **{
                        key: execution.__dict__[key]
                        for key in execution.__dict__
                        if not (key.startswith("_sa_") or key == "user_id")
                    }
                }
                for execution in executions_list
            ]
            return executions_list

    def trigger_feature_execution(self, feature_id):
        with Session.begin() as session:
            feature_data = (
                session.query(Feature)
                .filter(and_(Feature.user_id == self.user_id, Feature.id == feature_id))
                .first()
            )
            if feature_data is None:
                raise exc.NoResultFound(f"Feature with {feature_id} not found")
            script_loc = feature_data.script_loc
            feature_drift_enabled = feature_data.feature_drift_enabled
        lambda_client = boto3.client("lambda")
        internal_api_key = get_internal_api_key(self.user_id)
        execution_id = uuid.uuid4()
        lambda_payload = {
            "SCRIPT_LOC": script_loc,
            "KEY_ID": internal_api_key["key_id"],
            "SECRET": internal_api_key["secret"],
            "SCHEDULING_EXPRESSION": None,
            "VERSIONING": "None",
            "EXECUTION_TYPE": models.ExecutionType.AD_HOC.value,
            "EXECUTION_ID": None,
            "FEATURE_DRIFT_ENABLED": str(feature_drift_enabled),
        }
        lambda_response = lambda_client.invoke(
            FunctionName=Constants.EXECUTION_ENGINE_LAMBDA_NAME,
            Payload=json.dumps(lambda_payload),
        )
        lambda_response_dict = json.loads(lambda_response["Payload"].read())
        with Session.begin() as session:
            dict_to_insert = {
                "id": execution_id,
                "user_id": self.user_id,
                "status": models.ExecutionStatus.PENDING.value,
                "execution_type": models.ExecutionType.AD_HOC.value,
            }
            session.add(Executions(**dict_to_insert))
        response_dict = {
            "state_machine_execution_arn": lambda_response_dict["body"]["executionArn"],
            "execution_id": str(execution_id),
        }
        return response_dict

    def scheduled_feature_execution(self):
        execution_id = uuid.uuid4()
        with Session.begin() as session:
            dict_to_insert = {
                "id": execution_id,
                "user_id": self.user_id,
                "status": models.ExecutionStatus.PENDING.value,
                "execution_type": models.ExecutionType.SCHEDULED.value,
            }
            session.add(Executions(**dict_to_insert))
        return execution_id

    def feature_execution_async_handler(
        self,
        state_machine_execution_arn: str,
        execution_id: str,
        max_retries=100,
        retry_interval=15,
    ):
        sfn_client = boto3.client("stepfunctions")
        retries = 0
        try:
            while retries < max_retries:
                execution_response = sfn_client.describe_execution(
                    executionArn=state_machine_execution_arn
                )
                if execution_response["status"] == "FAILED":
                    raise Exception(execution_response["cause"])
                elif execution_response["status"] == "TIMED_OUT":
                    raise Exception(f"The execution {execution_id} has timed out")
                elif execution_response["status"] == "SUCCEEDED":
                    with Session.begin() as session:
                        row_to_modify = (
                            session.query(Executions)
                            .filter(
                                Executions.user_id == self.user_id,
                                Executions.id == execution_id,
                            )
                            .first()
                        )
                        setattr(
                            row_to_modify,
                            "status",
                            models.ExecutionStatus.SUCCEEDED.value,
                        )
                    log.info(f"Execution {execution_id} was successful")
                    break
                elif execution_response["status"] == "RUNNING":
                    log.info(f"Execution {execution_id} is currently running")
                    retries += 1
                    time.sleep(retry_interval)
            if retries == 100:
                raise Exception(f"The execution {execution_id} has timed out")
        except Exception as e:
            log.error(str(e))
            self.failed_execution_handler(execution_id, str(e))

    def store_feature_drift(self, feature_id, drifts, execution_type):
        feature_details = self.return_feature_details(feature_id)
        if len(feature_details) == 0:
            raise exc.NoResultFound(f"Feature with {feature_id} not found")
        feature_details = feature_details[0]
        with Session.begin() as session:
            if execution_type == models.ExecutionType.FIRST_RUN.value:
                session.add(
                    FeatureDrift(feature_id=feature_id, version=1, drifts=drifts)
                )
            else:
                session.add(
                    FeatureDrift(
                        feature_id=feature_id,
                        version=feature_details["latest_version"] + 1,
                        drifts=drifts,
                    )
                )

    def view_feature_drifts(self, feature_id):
        feature_drift_series = []
        with Session.begin() as session:
            feature_drifts = (
                session.query(FeatureDrift)
                .filter(FeatureDrift.feature_id == feature_id)
                .all()
            )
            if len(feature_drifts) == 0:
                raise exc.NoResultFound(f"Feature with {feature_id} not found")
            for feature_drift in feature_drifts:
                feature_drift_series.append(
                    {
                        "feature_id": feature_id,
                        "version": feature_drift.version,
                        "record_date": feature_drift.record_date,
                        "drifts": feature_drift.drifts,
                    }
                )
            return feature_drift_series
