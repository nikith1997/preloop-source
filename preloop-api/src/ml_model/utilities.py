import json
import logging
import os
import random
import string
import time
import uuid
from datetime import datetime
from io import BytesIO
from typing import List, Optional
import base64
import subprocess
import tempfile

import boto3
from kubernetes import client, config
import nbconvert
import nbformat
from cryptography.fernet import Fernet
from fastapi import UploadFile
from preloop.compiler import ScriptGenerator
from pylint import lint
from sqlalchemy import and_, exc, or_

import src.constants as constants
from src.api_key_management.utilities import get_internal_api_key
from src.auth import utilities as auth_utilities
from src.database import (
    AllUsers,
    HostedMLModels,
    MLModel,
    MLModelTrainingJobs,
    MLModelVersions,
    OrgLoadBalancers,
    Session,
)
from src.ml_model.models import *

log = logging.getLogger("uvicorn")


class MLModelCore:
    def __init__(
        self,
        user_id: str,
        org_id: str,
        role: str,
    ) -> None:
        self.user_id = user_id
        self.org_id = org_id
        self.role = role
        self.access_resolution_list = auth_utilities.resolve_access(
            self.user_id, self.role, self.org_id
        )

    def ml_model_name_exists(self, org_id: uuid.UUID, ml_model_name: str) -> bool:
        """
        Checks if the model name already exists, and returns a boolean result.
        """
        with Session.begin() as session:
            user_ids = (
                session.query(AllUsers.user_id).filter(AllUsers.org_id == org_id).all()
            )
            user_ids = [user_id[0] for user_id in user_ids]

            query_results = (
                session.query(MLModel)
                .filter(
                    MLModel.ml_model_name == ml_model_name,
                    MLModel.user_id.in_(user_ids),
                )
                .count()
            )
            if query_results > 0:
                return True
            else:
                return False

    def list_ml_models(self, ml_model_id: Optional[uuid.UUID] = None):
        """
        Lists all the ML models created by the user.
        """
        with Session.begin() as session:
            if ml_model_id is None:
                query_results = (
                    session.query(MLModel, AllUsers.email, AllUsers.role)
                    .join(AllUsers)
                    .filter(MLModel.user_id.in_(self.access_resolution_list))
                    .all()
                )
            else:
                query_results = (
                    session.query(MLModel, AllUsers.email, AllUsers.role)
                    .join(AllUsers)
                    .filter(
                        and_(
                            MLModel.user_id.in_(self.access_resolution_list),
                            MLModel.id == ml_model_id,
                        )
                    )
                    .all()
                )

            ml_models = []
            if not query_results:
                return []

            for row in query_results:
                ml_models.append(
                    {
                        **{
                            key: row[0].__dict__[key]
                            for key in row[0].__dict__
                            if not key.startswith("_sa_")
                        },
                        "owner": row[1]
                        if row[2] == "root"
                        else row[1].split(constants.ORG_ACCOUNT_SPLIT_TOKEN)[1],
                    }
                )

            return ml_models

    def create_ml_model(
        self,
        ml_model_name: str,
        ml_model_description: str,
        training_script: UploadFile,
        predict_function_name: str,
        require_api_key: bool,
        schedule: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ):
        """
        Creates a new ML model.
        """
        if self.ml_model_name_exists(self.org_id, ml_model_name):
            raise ValueError(f"ML model {ml_model_name} already exists")
        if not all(c.isalpha() or c.isspace() for c in ml_model_name):
            raise ValueError("Model name can only contain alphabets and spaces")
        file_extension = training_script.filename.rsplit(".", 1)[1].lower()
        training_script.file.seek(0)
        if file_extension == "ipynb":
            notebook = nbformat.read(training_script.file, as_version=4)
            exporter = nbconvert.PythonExporter()
            training_code, _ = exporter.from_notebook_node(notebook)
        elif file_extension == "py":
            training_code = training_script.file.read().decode("utf-8")
        else:
            raise TypeError("Training script must be a .py or .ipynb file")
        encrypted_env_vars = None
        if env_vars is not None:
            for key in env_vars:
                if key[0].isnumeric():
                    raise ValueError(
                        "Environment variable keys cannot start with a number"
                    )
                if not all(c.isalnum() or c == "_" for c in key):
                    raise ValueError(
                        "Environment variable keys can only contain alphanumeric characters and underscores"
                    )
            env_vars_string = json.dumps(env_vars)
            encrypted_env_vars = self.encrypt_env_vars(env_vars_string)
        with Session.begin() as session:
            ml_model = MLModel(
                user_id=self.user_id,
                ml_model_name=ml_model_name,
                ml_model_description=ml_model_description,
                require_api_key=require_api_key,
                status=HostedMLModelStatus.TRAINING.value,
                schedule=schedule,
                predict_function_name=predict_function_name,
                env_vars=encrypted_env_vars,
            )
            session.add(ml_model)
            session.flush()
            ml_model_id = ml_model.id
            ml_model.ml_object_dir = f"{self.user_id}/{ml_model_id}/objects/"
            ml_model.script_dir = f"{self.user_id}/{ml_model_id}/scripts/"
            scripts = ScriptGenerator(
                training_code, ml_model.ml_object_dir, predict_function_name
            )
            ml_model.libraries = scripts.script_info.libraries
            ml_model.ml_model_inputs = scripts.predict_function_inputs_and_types
            ml_model_training_job = MLModelTrainingJobs(
                ml_model_id=ml_model_id,
                user_id=self.user_id,
                status=MLModelTrainingJobStatus.TRAINING.value,
            )
            session.add(ml_model_training_job)
            session.flush()
            ml_model_training_job_id = ml_model_training_job.id
            ml_model_version = MLModelVersions(
                ml_model_id=ml_model_id,
                user_id=self.user_id,
                version=1,
            )
            session.add(ml_model_version)
            if schedule is not None:
                scheduler_client = boto3.client("scheduler")
                schedule_array = schedule.split(" ")
                if len(schedule_array) != 6:
                    raise ValueError(
                        "Scheduling expression must have 6 fields separated by spaces"
                    )
                try:
                    scheduler_client.create_schedule(
                        FlexibleTimeWindow={"Mode": "OFF"},
                        Name=str(ml_model_id),
                        ScheduleExpression=f"cron({schedule})",
                        State="DISABLED",
                        Target={
                            "Arn": f"arn:aws:lambda:{os.getenv('AWS_DEFAULT_REGION')}:{os.getenv('AWS_ACCOUNT_ID')}:function:ExecutionEngineLambda",
                            "Input": json.dumps({"KEY": "VALUE"}),
                            "RoleArn": f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/execution-engine-scheduler-role",
                        },
                    )
                except Exception as e:
                    raise ValueError(
                        f"The provided scheduling expression {schedule} is not valid cron syntax"
                    )

        return ml_model_id, ml_model_training_job_id, scripts

    def create_ml_model_async(
        self,
        ml_model_id,
        ml_model_training_job_id,
        scripts: ScriptGenerator,
        require_api_key: bool,
        schedule: Optional[str] = None,
        max_retries=constants.EXECUTION_ENGINE_RETRY_COUNT,
        retry_interval=constants.EXECUTION_ENGINE_RETRY_DELAY,
    ):
        with Session.begin() as session:
            ml_model = (
                session.query(MLModel)
                .filter(
                    MLModel.user_id.in_(self.access_resolution_list),
                    MLModel.id == ml_model_id,
                )
                .first()
            )

        ca_temp_file = tempfile.NamedTemporaryFile(suffix=".crt")
        configuration = client.Configuration()
        ca_data_decoded = base64.b64decode("LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURCVENDQWUyZ0F3SUJBZ0lJVGI1ckp0S3VqMDB3RFFZSktvWklodmNOQVFFTEJRQXdGVEVUTUJFR0ExVUUKQXhNS2EzVmlaWEp1WlhSbGN6QWVGdzB5TkRBME1ESXdOVFEzTXpSYUZ3MHpOREF6TXpFd05UVXlNelJhTUJVeApFekFSQmdOVkJBTVRDbXQxWW1WeWJtVjBaWE13Z2dFaU1BMEdDU3FHU0liM0RRRUJBUVVBQTRJQkR3QXdnZ0VLCkFvSUJBUUNYOHB4bkliMmM1VTZKejVEblYyNnloYjFHZzV4TXZoeVFIeTV5UE5TcG5DZC83RFJ0WC92UnB5b1EKTVh0VFdaVkRYcFpQRFRwbXcxWFhlWVJXUVFzVURUalpRak5MeGNlQzR4ZGkvbUNQdGdQMktmOUxlRkgrMldGNApZem9oSWtXOHV2b0tDSHowR1dnR0dnSkw1enNEd1pkMkxvTE14ekFEWVlHaStoNVJzUDdPbGU3MUdSYzRkdS9VClhMNXYvc1hoR3dFV0s4SlBSVDYzcVhNWkhhQ2lZdHZyM2pmYTZhcDBqQXVyTlpxeHFSbXZiSm1qNytNRjgrQTYKL3d6WmdndW8zRlBBL3JXbzhFRWpXNGw5WUlnM2J2OG1KaWp3d1hZT2N4S2hXTmRCVFAzaTR6VTdZR1Q3c2c4MQpQTksxV3RuTXlCZXdRTWY1NVZCajJOU2ZkYXJ4QWdNQkFBR2pXVEJYTUE0R0ExVWREd0VCL3dRRUF3SUNwREFQCkJnTlZIUk1CQWY4RUJUQURBUUgvTUIwR0ExVWREZ1FXQkJRMHNodk9aMnkraHNmZ2NZSFVwdUk3WkJhdlBqQVYKQmdOVkhSRUVEakFNZ2dwcmRXSmxjbTVsZEdWek1BMEdDU3FHU0liM0RRRUJDd1VBQTRJQkFRQVk1Zk9tZnk4SAovZUdQMHdrRHAyMHZZQ2VKOHlOUDRNUW44RXhUdDBpM3d4RzdaVWZuUVBHeDhwV2RqekR0dkdaQUxCRm9tNXVmCk0vQjVpazB1R3oyOTh4NW50UU5RS2I0QTM3NTFZTG9oVXVLYmFGOHByQ3FzNGFCVVhFdktSUjh5c2FMbUFjTE0KUVVySXRQc3NYR2ZFczFNN1lFQU5nRXZha1NIaVlEVnN1T2ZzeWEwOXowSTd4K1FpaVUveGM4aUdqZFNCOFA4ZgpjNjE2SU9sU3lVSzJEL2JLSUdqUVZRenJyVloxd3lpdzFtc2tKRVhtMENmcU1POExvVCs5ZncvSFNoUE53NjRXCkNaQmQzV0p2QXk2NVVMcEFYeXBxNGNLSlNiN2ZpbW9pSytUeEZNZlV4NWZETjEwWUFRRW1NZFY1TEtNK1NObk4KbWVjVDR2Tnp4WFZwCi0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K")
        with open(ca_temp_file.name, 'wb') as ca_file:
            ca_file.write(ca_data_decoded)
        configuration.host = "https://0E0BC507F010F0E969B7BE1E73078E85.gr7.us-east-1.eks.amazonaws.com"
        configuration.ssl_ca_cert = ca_temp_file.name
        configuration.verify_ssl = True
        command_output = subprocess.run("aws eks get-token --cluster-name education-eks-FQCLNOqx", shell=True, capture_output=True, text=True)
        token = json.loads(command_output.stdout)["status"]["token"]
        configuration.api_key = {"authorization": f"Bearer {token}"}

        client.Configuration.set_default(configuration)
        scheduler_client = boto3.client("scheduler")
        libs_string = self.get_required_libraries(ml_model.libraries)
        sfn_client = boto3.client("stepfunctions")
        s3_client = boto3.client("s3")
        ml_model = self.list_ml_models(ml_model_id)[0]
        training_script_string = scripts.training_script
        training_code_bytes = BytesIO(training_script_string.encode("utf-8"))
        api_key = get_internal_api_key(self.user_id)
        s3_client.upload_fileobj(
            training_code_bytes,
            f"preloop-ml-objects-{constants.DEPLOY_ENVIRONMENT}",
            f"{ml_model['script_dir']}training_script.py",
        )
        log.info("Starting the training script execution")
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=f"training-job-{ml_model_id}"),
            spec=client.V1JobSpec(
                backoff_limit=0,
                ttl_seconds_after_finished=120,
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        service_account_name="default",
                        containers=[
                            client.V1Container(
                                name="training-container",
                                image="439101250057.dkr.ecr.us-east-1.amazonaws.com/preloop-execution-engine:latest",
                                resources=client.V1ResourceRequirements(
                                    requests={"cpu": "8", "memory": "16G"},
                                ),
                                env=[
                                    client.V1EnvVar(
                                        name="SCRIPT_LOC",
                                        value=f"s3://preloop-ml-objects-{constants.DEPLOY_ENVIRONMENT}/{ml_model['script_dir']}training_script.py",
                                    ),
                                    client.V1EnvVar(name="VERSION", value="1"),
                                    client.V1EnvVar(name="LIBRARIES", value=libs_string),
                                    client.V1EnvVar(
                                        name="LOOP_LINE_NUMBERS",
                                        value=",".join(
                                            str(c) for c in scripts.loop_line_numbers
                                        ),
                                    ),
                                    client.V1EnvVar(
                                        name="ENV_VARS",
                                        value=self.decrypt_env_vars(ml_model["env_vars"])
                                        if ml_model["env_vars"] is not None
                                        else "",
                                    ),
                                ],
                            )
                        ],
                        restart_policy="Never",
                    )
                )
            )
        )
        api_instance = client.BatchV1Api()
        namespace = "execution-engine"
        api_instance.create_namespaced_job(body=job, namespace=namespace)
        retry = 0
        while retry < max_retries:
            status = api_instance.read_namespaced_job_status(name=f"training-job-{ml_model_id}", namespace=namespace)
            if status.status.succeeded == 1:
                break
            elif status.status.failed == 1:
                with Session.begin() as session:
                    session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                        {
                            "status": HostedMLModelStatus.FAILED.value,
                            "reason": "Script execution failure",
                        }
                    )
                    session.query(MLModelTrainingJobs).filter(
                        MLModelTrainingJobs.id == ml_model_training_job_id
                    ).update(
                        {
                            "status": MLModelTrainingJobStatus.FAILED.value,
                            "reason": "Script execution failure",
                            "end_time": datetime.now(),
                        }
                    )
                if schedule is not None:
                    scheduler_client.delete_schedule(Name=ml_model_id)
                raise Exception(f"Script execution failure")
            retry += 1
            time.sleep(retry_interval)
            if retry == max_retries:
                with Session.begin() as session:
                    session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                        {
                            "status": HostedMLModelStatus.FAILED.value,
                            "reason": "Maximum retries reached",
                        }
                    )
                    session.query(MLModelTrainingJobs).filter(
                        MLModelTrainingJobs.id == ml_model_training_job_id
                    ).update(
                        {
                            "status": MLModelTrainingJobStatus.FAILED.value,
                            "reason": "Maximum retries reached",
                            "end_time": datetime.now(),
                        }
                    )
                if schedule is not None:
                    scheduler_client.delete_schedule(Name=str(ml_model_id))
                raise Exception("Training script execution failed")
        inference_code = scripts.inference_script
        inference_code_bytes = BytesIO(inference_code.encode("utf-8"))
        inference_script_loc = f"s3://preloop-ml-objects-{constants.DEPLOY_ENVIRONMENT}/{ml_model['script_dir']}inference.py"
        s3_client.upload_fileobj(
            inference_code_bytes,
            f"preloop-ml-objects-{constants.DEPLOY_ENVIRONMENT}",
            f"{ml_model['script_dir']}inference.py",
        )
        with Session.begin() as session:
            session.query(MLModelTrainingJobs).filter(
                MLModelTrainingJobs.id == ml_model_training_job_id
            ).update(
                {
                    "status": MLModelTrainingJobStatus.SUCCEEDED.value,
                    "end_time": datetime.now(),
                }
            )
            session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                {"latest_version": 1}
            )
        # with Session.begin() as session:
        #     hosted_model_object = HostedMLModels(
        #         ml_model_id=ml_model_id,
        #         user_id=self.user_id,
        #         status=HostedMLModelStatus.DEPLOYING.value,
        #         require_api_key=require_api_key,
        #         version=-1,
        #     )
        #     session.add(hosted_model_object)
        #     session.flush()
        #     hosted_ml_model_id = hosted_model_object.id
        #     session.query(MLModel).filter(MLModel.id == ml_model_id).update(
        #         {"status": HostedMLModelStatus.DEPLOYING.value}
        #     )
        # ml_model_name = ml_model["ml_model_name"].replace(" ", "-").lower()
        # elb_client = boto3.client("elbv2")
        # aws_resources = []
        # with Session.begin() as session:
        #     load_balancer = (
        #         session.query(OrgLoadBalancers)
        #         .filter(
        #             OrgLoadBalancers.org_id == self.org_id,
        #             OrgLoadBalancers.num_target_groups < 80,
        #         )
        #         .first()
        #     )
        # if load_balancer is None:
        #     log.info("No load balancer available, creating a new one")
        #     try:
        #         self.create_application_load_balancer()
        #         log.info("Created a new load balancer")
        #     except:
        #         with Session.begin() as session:
        #             session.query(HostedMLModels).filter(
        #                 HostedMLModels.id == hosted_ml_model_id,
        #             ).delete()
        #             session.query(MLModel).filter(MLModel.id == ml_model_id).update(
        #                 {
        #                     "status": HostedMLModelStatus.FAILED.value,
        #                     "reason": "Load balancer creation failed",
        #                 }
        #             )
        #         raise Exception("Load balancer creation failed")
        #     with Session.begin() as session:
        #         load_balancer = (
        #             session.query(OrgLoadBalancers)
        #             .filter(
        #                 OrgLoadBalancers.org_id == self.org_id,
        #                 OrgLoadBalancers.num_target_groups < 80,
        #             )
        #             .first()
        #         )
        #         if load_balancer is None:
        #             with Session.begin() as session:
        #                 session.query(HostedMLModels).filter(
        #                 HostedMLModels.id == hosted_ml_model_id,
        #             ).delete()
        #                 session.query(MLModel).filter(MLModel.id == ml_model_id).update(
        #                     {
        #                         "status": HostedMLModelStatus.FAILED.value,
        #                         "reason": "Load balancer creation failed",
        #                     }
        #                 )
        #             raise Exception("No load balancer available")
        # # FIX THIS IF STATEMENT LOGIC
        # if load_balancer.status == "provisioning":
        #     retry = 0
        #     while retry < constants.LB_MAX_RETRIES:
        #         try:
        #             response = elb_client.describe_load_balancers(
        #                 LoadBalancerArns=[load_balancer.load_balancer_arn]
        #             )
        #             if response["LoadBalancers"][0]["State"]["Code"] == "failed":
        #                 with Session.begin() as session:
        #                     session.query(HostedMLModels).filter(
        #                 HostedMLModels.id == hosted_ml_model_id,
        #             ).delete()
        #                     session.query(MLModel).filter(MLModel.id == ml_model_id).update(
        #                     {
        #                         "status": HostedMLModelStatus.FAILED.value,
        #                         "reason": "Load balancer creation failed",
        #                     }
        #                 )
        #                 raise Exception("Load balancer creation failed")
        #         except:
        #             with Session.begin() as session:
        #                 session.query(HostedMLModels).filter(
        #                 HostedMLModels.id == hosted_ml_model_id,
        #             ).delete()
        #                 session.query(MLModel).filter(MLModel.id == ml_model_id).update(
        #                     {
        #                         "status": HostedMLModelStatus.FAILED.value,
        #                         "reason": "Load balancer creation failed",
        #                     }
        #                 )
        #             raise Exception("Load balancer creation failed")
        #         if response["LoadBalancers"][0]["State"]["Code"] == "active":
        #             break
        #         retry += 1
        #         time.sleep(constants.LB_RETRY_DELAY)
        #         if retry == constants.LB_MAX_RETRIES:
        #             session.query(HostedMLModels).filter(
        #                 HostedMLModels.id == hosted_ml_model_id,
        #             ).delete()
        #             session.query(MLModel).filter(MLModel.id == ml_model_id).update(
        #                     {
        #                         "status": HostedMLModelStatus.FAILED.value,
        #                         "reason": "Load balancer creation failed",
        #                     }
        #                 )
        #             raise Exception("Load balancer creation failed")
        # with Session.begin() as session:
        #     session.query(OrgLoadBalancers).filter(
        #         OrgLoadBalancers.id == load_balancer.id
        #     ).update({"num_target_groups": load_balancer.num_target_groups + 1})
        # try:
        #     container_env_version = 1
        #     url_version = "latest"
        #     # Create target group for service
        #     log.info("Creating target group")
        #     target_group_name = "".join(
        #         random.choice(string.ascii_lowercase) for _ in range(10)
        #     )
        #     target_group_response = elb_client.create_target_group(
        #         Name=target_group_name,
        #         Protocol="HTTP",
        #         Port=80,
        #         VpcId=constants.VPC_ID,
        #         HealthCheckPath="/docs",
        #         Matcher={"HttpCode": "200"},
        #         TargetType="ip",
        #     )
        #     aws_resources.append(
        #         {
        #             "resource_type": "target_group",
        #             "resource_arn": target_group_response["TargetGroups"][0][
        #                 "TargetGroupArn"
        #             ],
        #             "priority": 2,
        #         }
        #     )

        #     # Create listener rule for target group
        #     log.info("Creating listener rule")
        #     listener_rule_response = elb_client.create_rule(
        #         ListenerArn=load_balancer.listener_arn,
        #         Conditions=[
        #             {
        #                 "Field": "path-pattern",
        #                 "Values": [f"/{ml_model_name}/{url_version}"],
        #             }
        #         ],
        #         Priority=self.find_smallest_priority_available_in_alb(load_balancer.listener_arn),
        #         Actions=[
        #             {
        #                 "Type": "forward",
        #                 "TargetGroupArn": target_group_response["TargetGroups"][0][
        #                     "TargetGroupArn"
        #                 ],
        #             }
        #         ],
        #     )
        #     aws_resources.append(
        #         {
        #             "resource_type": "listener_rule",
        #             "resource_arn": listener_rule_response["Rules"][0]["RuleArn"],
        #             "priority": 1,
        #         }
        #     )

        #     # Create security group for ecs service
        #     log.info("Creating security group")
        #     ec2_client = boto3.client("ec2")
        #     security_group_name = "".join(
        #         random.choice(string.ascii_lowercase) for i in range(10)
        #     )
        #     security_group_response = ec2_client.create_security_group(
        #         Description="Security group for ECS target to allow traffic from ALB",
        #         GroupName=security_group_name,
        #         VpcId=constants.VPC_ID,
        #     )
        #     aws_resources.append(
        #         {
        #             "resource_type": "security_group",
        #             "group_id": security_group_response["GroupId"],
        #             "priority": 3,
        #         }
        #     )

        #     # Add ingress rule to security group to allow traffic from ALB to ECS
        #     security_group_ingress_response = (
        #         ec2_client.authorize_security_group_ingress(
        #             GroupId=security_group_response["GroupId"],
        #             IpPermissions=[
        #                 {
        #                     "IpProtocol": "tcp",
        #                     "FromPort": 80,
        #                     "ToPort": 80,
        #                     "UserIdGroupPairs": [
        #                         {"GroupId": load_balancer.security_group_id}
        #                     ],
        #                 }
        #             ],
        #         )
        #     )

        #     with Session.begin() as session:
        #         ml_model = (
        #             session.query(MLModel)
        #             .filter(
        #                 MLModel.id == ml_model_id,
        #                 MLModel.user_id.in_(self.access_resolution_list),
        #             )
        #             .first()
        #         )
        #     libs_string = self.get_required_libraries(ml_model.libraries)
        #     predict_function_name = ml_model.predict_function_name
        #     # Register a fargate task definition
        #     log.info("Registering fargate task definition")
        #     ecs_client = boto3.client("ecs")
        #     task_definition_name = "".join(
        #         random.choice(string.ascii_lowercase) for i in range(20)
        #     )
        #     ecs_service_name = "".join(
        #         random.choice(string.ascii_lowercase) for i in range(20)
        #     )
        #     key_id = ""
        #     secret = ""
        #     if require_api_key:
        #         api_key = get_internal_api_key(self.user_id)
        #         key_id = api_key["key_id"]
        #         secret = api_key["secret"]
        #     task_definition_response = ecs_client.register_task_definition(
        #         family=task_definition_name,
        #         taskRoleArn=constants.MODEL_INFERENCE_ENGINE_FARGATE_TASK_ROLE_ARN,
        #         executionRoleArn=constants.MODEL_INFERENCE_ENGINE_FARGATE_EXECUTION_ROLE_ARN,
        #         networkMode="awsvpc",
        #         containerDefinitions=[
        #             {
        #                 "name": "ModelInferenceEngineContainer",
        #                 "image": f"{constants.AWS_ACCOUNT_ID}.dkr.ecr.{constants.AWS_DEFAULT_REGION}.amazonaws.com/preloop-model-inference-engine:latest",
        #                 "essential": True,
        #                 "portMappings": [{"containerPort": 80}],
        #                 "logConfiguration": {
        #                     "logDriver": "awslogs",
        #                     "options": {
        #                         "awslogs-group": "/ecs/model-inference-engine",
        #                         "awslogs-region": constants.AWS_DEFAULT_REGION,
        #                         "awslogs-stream-prefix": "ModelInferenceEngine",
        #                     },
        #                 },
        #                 "environment": [
        #                     {"name": "ML_MODEL_NAME", "value": ml_model_name},
        #                     {
        #                         "name": "INFERENCE_SCRIPT_LOC",
        #                         "value": inference_script_loc,
        #                     },
        #                     {
        #                         "name": "PREDICT_FUNCTION_NAME",
        #                         "value": predict_function_name,
        #                     },
        #                     {"name": "ML_MODEL_TRAINING", "value": "True"},
        #                     {"name": "VERSION", "value": str(container_env_version)},
        #                     {"name": "URL_VERSION", "value": url_version},
        #                     {
        #                         "name": "REQUIRE_API_KEY",
        #                         "value": str(require_api_key)
        #                         if require_api_key
        #                         else "",
        #                     },
        #                     {"name": "PRELOOP_KEY_ID", "value": key_id},
        #                     {"name": "PRELOOP_SECRET", "value": secret},
        #                     {"name": "ECS_SERVICE_NAME", "value": ecs_service_name},
        #                     {"name": "LIBRARIES", "value": libs_string},
        #                     {
        #                         "name": "ENV_VARS",
        #                         "value": self.decrypt_env_vars(ml_model.env_vars)
        #                         if ml_model.env_vars is not None
        #                         else "",
        #                     },
        #                 ],
        #             }
        #         ],
        #         cpu="2 vCPU",
        #         memory="16 GB",
        #     )
        #     aws_resources.append(
        #         {
        #             "resource_type": "ecs_task_definition",
        #             "task_definition_arn": task_definition_response["taskDefinition"][
        #                 "taskDefinitionArn"
        #             ],
        #             "priority": 1,
        #         }
        #     )

        #     log.info("Creating ECS service")
        #     ecs_client = boto3.client("ecs")
        #     response = ecs_client.create_service(
        #         cluster="ModelInferenceEngineCluster",
        #         serviceName=ecs_service_name,
        #         taskDefinition=task_definition_name,
        #         loadBalancers=[
        #             {
        #                 "targetGroupArn": target_group_response["TargetGroups"][0][
        #                     "TargetGroupArn"
        #                 ],
        #                 "containerName": "ModelInferenceEngineContainer",
        #                 "containerPort": 80,
        #             }
        #         ],
        #         desiredCount=2,
        #         launchType="FARGATE",
        #         networkConfiguration={
        #             "awsvpcConfiguration": {
        #                 "subnets": [
        #                     constants.COMPUTE_SUBNET_1,
        #                     constants.COMPUTE_SUBNET_2,
        #                 ],
        #                 "securityGroups": [security_group_response["GroupId"]],
        #             }
        #         },
        #     )
        #     aws_resources.append(
        #         {
        #             "resource_type": "ecs_service",
        #             "cluster_name": "ModelInferenceEngineCluster",
        #             "service_name": ecs_service_name,
        #             "priority": 2,
        #         }
        #     )
        #     time.sleep(70)
        #     with Session.begin() as session:
        #         session.query(HostedMLModels).filter(
        #                 HostedMLModels.id == hosted_ml_model_id,
        #             ).update(
        #             {
        #                 "ecs_cluster_name": "ModelInferenceEngineCluster",
        #                 "ecs_service_name": ecs_service_name,
        #                 "target_group_arn": target_group_response["TargetGroups"][0][
        #                     "TargetGroupArn"
        #                 ],
        #                 "listener_rule_arn": listener_rule_response["Rules"][0][
        #                     "RuleArn"
        #                 ],
        #                 "task_security_group_id": security_group_response["GroupId"],
        #                 "task_definition_arn": task_definition_response[
        #                     "taskDefinition"
        #                 ]["taskDefinitionArn"],
        #                 "load_balancer_id": load_balancer.id,
        #                 "status": HostedMLModelStatus.AVAILABLE.value,
        #                 "endpoint_url": f"{load_balancer.url}/{ml_model_name}/{url_version}",
        #             }
        #         )
        #         session.query(MLModel).filter(MLModel.id == ml_model_id).update(
        #             {
        #                 "status": HostedMLModelStatus.AVAILABLE.value,
        #                 "endpoint_url": f"{load_balancer.url}/{ml_model_name}/{url_version}",
        #                 "latest_deployed_version": 1,
        #             }
        #         )
        #     if schedule is not None:
        #         api_key = get_internal_api_key(self.user_id)
        #         scheduler_client = boto3.client("scheduler")
        #         scheduler_input = {
        #             "key_id": api_key["key_id"],
        #             "secret": api_key["secret"],
        #             "ml_model_id": str(ml_model_id),
        #         }
        #         scheduler_client.update_schedule(
        #             FlexibleTimeWindow={"Mode": "OFF"},
        #             Name=str(ml_model_id),
        #             ScheduleExpression=f"cron({schedule})",
        #             State="ENABLED",
        #             Target={
        #                 "Arn": f"arn:aws:lambda:{os.getenv('AWS_DEFAULT_REGION')}:{os.getenv('AWS_ACCOUNT_ID')}:function:ExecutionEngineLambda",
        #                 "Input": json.dumps(scheduler_input),
        #                 "RoleArn": f"arn:aws:iam::{os.getenv('AWS_ACCOUNT_ID')}:role/execution-engine-scheduler-role",
        #             },
        #         )
        #         aws_resources.append(
        #             {
        #                 "resource_type": "schedule",
        #                 "name": str(ml_model_id),
        #                 "priority": 1,
        #             }
        #         )

        # except Exception as e:
        #     log.error(str(e), exc_info=True)
        #     with Session.begin() as session:
        #         session.query(OrgLoadBalancers).filter(
        #             OrgLoadBalancers.id == load_balancer.id
        #         ).update({"num_target_groups": load_balancer.num_target_groups})
        #         session.query(HostedMLModels).filter(
        #                 HostedMLModels.id == hosted_ml_model_id,
        #             ).update(
        #             {
        #                 "status": HostedMLModelStatus.FAILED.value,
        #                 "reason": "Resources failed to create",
        #             }
        #         )
        #         session.query(MLModel).filter(MLModel.id == ml_model_id).update(
        #             {
        #                 "status": HostedMLModelStatus.FAILED.value,
        #                 "reason": "Resources failed to create",
        #             }
        #         )
        #     self.clean_up_aws_resources(aws_resources)

    def start_ml_model(
        self, ml_model_id: uuid.UUID, version: int | str, require_api_key: bool
    ):
        with Session.begin() as session:
            query_results = (
                session.query(MLModel)
                .filter(
                    MLModel.user_id.in_(self.access_resolution_list),
                    MLModel.id == ml_model_id,
                )
                .all()
            )

            if not query_results:
                raise ValueError(f"ML model {ml_model_id} does not exist")

            ml_model = {
                **{
                    key: query_results[0].__dict__[key]
                    for key in query_results[0].__dict__
                    if not key.startswith("_sa_")
                }
            }
            if ml_model.get("latest_version") is None:
                raise ValueError(f"Model {ml_model_id} has not been trained yet")
            if isinstance(version, int) and version > ml_model["latest_version"]:
                raise ValueError(
                    f"Version {version} does not exist for model {ml_model_id}"
                )
            latest_hosted_ml_model = (
                session.query(HostedMLModels)
                .filter(
                    HostedMLModels.ml_model_id == ml_model_id,
                    HostedMLModels.version == -1,
                    HostedMLModels.status != "failed",
                )
                .first()
            )
            if version == "latest":
                if latest_hosted_ml_model is not None:
                    raise ValueError(
                        f"Model {ml_model_id} already has a 'latest' version deployed."
                    )
                hosted_model_object = HostedMLModels(
                    ml_model_id=ml_model_id,
                    user_id=self.user_id,
                    status=HostedMLModelStatus.DEPLOYING.value,
                    require_api_key=require_api_key,
                    version=-1,
                )
                session.add(hosted_model_object)
                session.flush()
                hosted_model_id = hosted_model_object.id
                return (
                    hosted_model_id,
                    ml_model["ml_model_name"],
                    f"s3://preloop-ml-objects-{constants.DEPLOY_ENVIRONMENT}/{ml_model['script_dir']}inference.py",
                )
            hosted_ml_model = (
                session.query(HostedMLModels)
                .filter(
                    HostedMLModels.ml_model_id == ml_model_id,
                    HostedMLModels.version == version,
                    HostedMLModels.status != "failed",
                )
                .first()
            )
            if ml_model.get("latest_deployed_version") is not None:
                if (
                    latest_hosted_ml_model is not None
                    and version == ml_model["latest_deployed_version"]
                ):
                    raise ValueError(
                        f"Model {ml_model_id} version {version} is already deployed as the 'latest' version"
                    )
            if hosted_ml_model is not None:
                raise ValueError(
                    f"Model {ml_model_id} version {version} is already hosted"
                )
            hosted_model_object = HostedMLModels(
                ml_model_id=ml_model_id,
                user_id=self.user_id,
                status=HostedMLModelStatus.DEPLOYING.value,
                require_api_key=require_api_key,
                version=version,
            )
            session.add(hosted_model_object)
            session.flush()
            hosted_model_id = hosted_model_object.id
        return (
            hosted_model_id,
            ml_model["ml_model_name"],
            f"s3://preloop-ml-objects-{constants.DEPLOY_ENVIRONMENT}/{ml_model['script_dir']}inference.py",
        )

    def start_ml_model_async(
        self,
        ml_model_id,
        ml_model_name,
        version,
        inference_script_loc,
        require_api_key,
        hosted_ml_model_id,
        lb_max_retries=100,
        lb_retry_interval=5,
    ):
        ml_model_name = ml_model_name.replace(" ", "-").lower()
        elb_client = boto3.client("elbv2")
        aws_resources = []
        with Session.begin() as session:
            load_balancer = (
                session.query(OrgLoadBalancers)
                .filter(
                    OrgLoadBalancers.org_id == self.org_id,
                    OrgLoadBalancers.num_target_groups < 80,
                )
                .first()
            )
        if load_balancer is None:
            log.info("No load balancer available, creating a new one")
            try:
                self.create_application_load_balancer()
                log.info("Created a new load balancer")
            except:
                with Session.begin() as session:
                    session.query(HostedMLModels).filter(
                        HostedMLModels.id == hosted_ml_model_id,
                    ).update(
                        {
                            "status": HostedMLModelStatus.FAILED.value,
                            "reason": "Load balancer creation failed",
                        }
                    )
                raise Exception("Load balancer creation failed")
            with Session.begin() as session:
                load_balancer = (
                    session.query(OrgLoadBalancers)
                    .filter(
                        OrgLoadBalancers.org_id == self.org_id,
                        OrgLoadBalancers.num_target_groups < 80,
                    )
                    .first()
                )
                if load_balancer is None:
                    with Session.begin() as session:
                        session.query(HostedMLModels).filter(
                        HostedMLModels.id == hosted_ml_model_id,
                    ).update(
                            {
                                "status": HostedMLModelStatus.FAILED.value,
                                "reason": "Load balancer creation failed",
                            }
                        )
                    raise Exception("No load balancer available")
        # FIX THIS IF STATEMENT LOGIC
        if load_balancer.status == "provisioning":
            retry = 0
            while retry < lb_max_retries:
                try:
                    response = elb_client.describe_load_balancers(
                        LoadBalancerArns=[load_balancer.load_balancer_arn]
                    )
                    if response["LoadBalancers"][0]["State"]["Code"] == "failed":
                        with Session.begin() as session:
                            session.query(HostedMLModels).filter(
                        HostedMLModels.id == hosted_ml_model_id,
                    ).update(
                                {
                                    "status": HostedMLModelStatus.FAILED.value,
                                    "reason": "Load balancer creation failed",
                                }
                            )
                        raise Exception("Load balancer creation failed")
                except:
                    with Session.begin() as session:
                        session.query(HostedMLModels).filter(
                        HostedMLModels.id == hosted_ml_model_id,
                    ).update(
                            {
                                "status": HostedMLModelStatus.FAILED.value,
                                "reason": "Load balancer creation failed",
                            }
                        )
                    raise Exception("Load balancer creation failed")
                if response["LoadBalancers"][0]["State"]["Code"] == "active":
                    break
                retry += 1
                time.sleep(lb_retry_interval)
                if retry == lb_max_retries:
                    with Session.begin() as session:
                        session.query(HostedMLModels).filter(
                        HostedMLModels.id == hosted_ml_model_id,
                    ).update(
                            {
                                "status": HostedMLModelStatus.FAILED.value,
                                "reason": "Load balancer creation failed",
                            }
                        )
                    raise Exception("Load balancer creation failed")
        with Session.begin() as session:
            session.query(OrgLoadBalancers).filter(
                OrgLoadBalancers.id == load_balancer.id
            ).update({"num_target_groups": load_balancer.num_target_groups + 1})
            ml_model = session.query(MLModel).filter(MLModel.id == ml_model_id).first()
        try:
            if version == -1:
                container_env_version = ml_model.latest_deployed_version
                url_version = "latest"
            else:
                container_env_version = version
                url_version = str(version)
            # Create target group for service
            log.info("Creating target group")
            target_group_name = "".join(
                random.choice(string.ascii_lowercase) for _ in range(10)
            )
            target_group_response = elb_client.create_target_group(
                Name=target_group_name,
                Protocol="HTTP",
                Port=80,
                VpcId=constants.VPC_ID,
                HealthCheckPath="/docs",
                Matcher={"HttpCode": "200"},
                TargetType="ip",
            )
            aws_resources.append(
                {
                    "resource_type": "target_group",
                    "resource_arn": target_group_response["TargetGroups"][0][
                        "TargetGroupArn"
                    ],
                    "priority": 2,
                }
            )

            # Create listener rule for target group
            log.info("Creating listener rule")
            listener_rule_response = elb_client.create_rule(
                ListenerArn=load_balancer.listener_arn,
                Conditions=[
                    {
                        "Field": "path-pattern",
                        "Values": [f"/{ml_model_name}/{url_version}"],
                    }
                ],
                Priority=self.find_smallest_priority_available_in_alb(load_balancer.listener_arn),
                Actions=[
                    {
                        "Type": "forward",
                        "TargetGroupArn": target_group_response["TargetGroups"][0][
                            "TargetGroupArn"
                        ],
                    }
                ],
            )
            aws_resources.append(
                {
                    "resource_type": "listener_rule",
                    "resource_arn": listener_rule_response["Rules"][0]["RuleArn"],
                    "priority": 1,
                }
            )

            # Create security group for ecs service
            log.info("Creating security group")
            ec2_client = boto3.client("ec2")
            security_group_name = "".join(
                random.choice(string.ascii_lowercase) for i in range(10)
            )
            security_group_response = ec2_client.create_security_group(
                Description="Security group for ECS target to allow traffic from ALB",
                GroupName=security_group_name,
                VpcId=constants.VPC_ID,
            )
            aws_resources.append(
                {
                    "resource_type": "security_group",
                    "group_id": security_group_response["GroupId"],
                    "priority": 3,
                }
            )

            # Add ingress rule to security group to allow traffic from ALB to ECS
            security_group_ingress_response = (
                ec2_client.authorize_security_group_ingress(
                    GroupId=security_group_response["GroupId"],
                    IpPermissions=[
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 80,
                            "ToPort": 80,
                            "UserIdGroupPairs": [
                                {"GroupId": load_balancer.security_group_id}
                            ],
                        }
                    ],
                )
            )
            with Session.begin() as session:
                ml_model = (
                    session.query(MLModel)
                    .filter(
                        MLModel.id == ml_model_id,
                        MLModel.user_id.in_(self.access_resolution_list),
                    )
                    .first()
                )
            libs_string = self.get_required_libraries(ml_model.libraries)
            predict_function_name = ml_model.predict_function_name
            # Register a fargate task definition
            log.info("Registering fargate task definition")
            ecs_client = boto3.client("ecs")
            task_definition_name = "".join(
                random.choice(string.ascii_lowercase) for i in range(20)
            )
            ecs_service_name = "".join(
                random.choice(string.ascii_lowercase) for i in range(20)
            )
            key_id = ""
            secret = ""
            if require_api_key:
                api_key = get_internal_api_key(self.user_id)
                key_id = api_key["key_id"]
                secret = api_key["secret"]
            task_definition_response = ecs_client.register_task_definition(
                family=task_definition_name,
                taskRoleArn=constants.MODEL_INFERENCE_ENGINE_FARGATE_TASK_ROLE_ARN,
                executionRoleArn=constants.MODEL_INFERENCE_ENGINE_FARGATE_EXECUTION_ROLE_ARN,
                networkMode="awsvpc",
                containerDefinitions=[
                    {
                        "name": "ModelInferenceEngineContainer",
                        "image": f"{constants.AWS_ACCOUNT_ID}.dkr.ecr.{constants.AWS_DEFAULT_REGION}.amazonaws.com/preloop-model-inference-engine:latest",
                        "essential": True,
                        "portMappings": [{"containerPort": 80}],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": "/ecs/model-inference-engine",
                                "awslogs-region": constants.AWS_DEFAULT_REGION,
                                "awslogs-stream-prefix": "ModelInferenceEngine",
                            },
                        },
                        "environment": [
                            {"name": "ML_MODEL_NAME", "value": ml_model_name},
                            {
                                "name": "INFERENCE_SCRIPT_LOC",
                                "value": inference_script_loc,
                            },
                            {
                                "name": "PREDICT_FUNCTION_NAME",
                                "value": predict_function_name,
                            },
                            {"name": "ML_MODEL_TRAINING", "value": "True"},
                            {"name": "VERSION", "value": str(container_env_version)},
                            {"name": "URL_VERSION", "value": url_version},
                            {
                                "name": "REQUIRE_API_KEY",
                                "value": str(require_api_key)
                                if require_api_key
                                else "",
                            },
                            {"name": "PRELOOP_KEY_ID", "value": key_id},
                            {"name": "PRELOOP_SECRET", "value": secret},
                            {"name": "ECS_SERVICE_NAME", "value": ecs_service_name},
                            {"name": "LIBRARIES", "value": libs_string},
                            {
                                "name": "ENV_VARS",
                                "value": self.decrypt_env_vars(ml_model.env_vars)
                                if ml_model.env_vars is not None
                                else "",
                            },
                        ],
                    }
                ],
                cpu="2 vCPU",
                memory="16 GB",
            )
            aws_resources.append(
                {
                    "resource_type": "ecs_task_definition",
                    "task_definition_arn": task_definition_response["taskDefinition"][
                        "taskDefinitionArn"
                    ],
                    "priority": 1,
                }
            )

            # create ECS service
            log.info("Creating ECS service")
            ecs_client = boto3.client("ecs")
            response = ecs_client.create_service(
                cluster="ModelInferenceEngineCluster",
                serviceName=ecs_service_name,
                taskDefinition=task_definition_name,
                loadBalancers=[
                    {
                        "targetGroupArn": target_group_response["TargetGroups"][0][
                            "TargetGroupArn"
                        ],
                        "containerName": "ModelInferenceEngineContainer",
                        "containerPort": 80,
                    }
                ],
                desiredCount=2,
                launchType="FARGATE",
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": [
                            constants.COMPUTE_SUBNET_1,
                            constants.COMPUTE_SUBNET_2,
                        ],
                        "securityGroups": [security_group_response["GroupId"]],
                    }
                },
            )
            aws_resources.append(
                {
                    "resource_type": "ecs_service",
                    "cluster_name": "ModelInferenceEngineCluster",
                    "service_name": ecs_service_name,
                    "priority": 2,
                }
            )
            time.sleep(70)
            with Session.begin() as session:
                session.query(HostedMLModels).filter(
                        HostedMLModels.id == hosted_ml_model_id,
                    ).update(
                    {
                        "ecs_cluster_name": "ModelInferenceEngineCluster",
                        "ecs_service_name": ecs_service_name,
                        "target_group_arn": target_group_response["TargetGroups"][0][
                            "TargetGroupArn"
                        ],
                        "listener_rule_arn": listener_rule_response["Rules"][0][
                            "RuleArn"
                        ],
                        "task_security_group_id": security_group_response["GroupId"],
                        "task_definition_arn": task_definition_response[
                            "taskDefinition"
                        ]["taskDefinitionArn"],
                        "load_balancer_id": load_balancer.id,
                        "status": HostedMLModelStatus.AVAILABLE.value,
                        "endpoint_url": f"{load_balancer.url}/{ml_model_name}/{url_version}",
                    }
                )
        except Exception as e:
            log.error(str(e), exc_info=True)
            with Session.begin() as session:
                session.query(OrgLoadBalancers).filter(
                    OrgLoadBalancers.id == load_balancer.id
                ).update({"num_target_groups": load_balancer.num_target_groups})
                session.query(HostedMLModels).filter(
                        HostedMLModels.id == hosted_ml_model_id,
                    ).update(
                    {
                        "status": HostedMLModelStatus.FAILED.value,
                        "reason": "Resources failed to create",
                    }
                )
            self.clean_up_aws_resources(aws_resources)

    def retrain_ml_model(self, ml_model_id: uuid.UUID):
        with Session.begin() as session:
            ml_model = (
                session.query(MLModel)
                .filter(
                    MLModel.id == ml_model_id,
                    MLModel.user_id.in_(self.access_resolution_list),
                )
                .first()
            )
            if ml_model is None:
                raise ValueError(f"Ml model {ml_model_id} does not exist")
            if ml_model.status == HostedMLModelStatus.TRAINING.value:
                raise ValueError(f"Ml model {ml_model_id} is being trained")
            if ml_model.status == HostedMLModelStatus.FAILED.value:
                raise ValueError(
                    f"Ml model {ml_model_id} failed to create, please try creating a new model"
                )
            if ml_model.status == HostedMLModelStatus.DELETING.value:
                raise ValueError(f"Ml model {ml_model_id} is being deleted")
            session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                {"status": HostedMLModelStatus.TRAINING.value}
            )
            ml_model_training_job = MLModelTrainingJobs(
                ml_model_id=ml_model_id,
                user_id=ml_model.user_id,
                status=MLModelTrainingJobStatus.TRAINING.value,
            )
            session.add(ml_model_training_job)
            session.flush()
            ml_model_training_job_id = ml_model_training_job.id
            ml_model_version = MLModelVersions(
                ml_model_id=ml_model_id,
                user_id=ml_model.user_id,
                version=ml_model.latest_version + 1,
            )
            session.add(ml_model_version)
        return ml_model_training_job_id

    def retrain_ml_model_async(self, ml_model_id, ml_model_training_job_id):
        sfn_client = boto3.client("stepfunctions")
        ml_model = self.list_ml_models(ml_model_id)[0]
        task_metadata_retrieved = False
        log.info("Starting the training script execution")
        api_key = get_internal_api_key(self.user_id)
        sfn_input = {
            "SCRIPT_LOC": f"s3://preloop-ml-objects-{constants.DEPLOY_ENVIRONMENT}/{ml_model['script_dir']}training_script.py",
            "KEY_ID": api_key["key_id"],
            "SECRET": api_key["secret"],
            "SCHEDULING_EXPRESSION": None,
            "VERSIONING": None,
            "EXECUTION_TYPE": None,
            "EXECUTION_ID": None,
            "FEATURE_DRIFT_ENABLED": None,
            "LATEST_VERSION": None,
            "VERSION": str(ml_model["latest_version"] + 1),
            "ML_MODEL_TRAINING": None,
            "ML_MODEL_RETRAINING": "True",
            "ML_MODEL_ID": str(ml_model_id),
            "LIBRARIES": self.get_required_libraries(ml_model["libraries"]),
            "LOOP_LINE_NUMBERS": None,
            "ENV_VARS": self.decrypt_env_vars(ml_model["env_vars"])
            if ml_model["env_vars"] is not None
            else None,
        }
        sfn_response = sfn_client.start_execution(
            stateMachineArn=constants.EXECUTION_ENGINE_STATE_MACHINE_EXECUTION_ARN,
            input=json.dumps(sfn_input),
        )
        execution_arn = sfn_response["executionArn"]
        retry = 0
        while retry < constants.EXECUTION_ENGINE_RETRY_COUNT:
            if not task_metadata_retrieved:
                execution_history = sfn_client.get_execution_history(
                    executionArn=execution_arn
                )
                for event in execution_history["events"]:
                    if event["type"] == "TaskSubmitted":
                        task_submitted_output = json.loads(
                            event["taskSubmittedEventDetails"]["output"]
                        )
                        cluster_arn = task_submitted_output["Tasks"][0]["ClusterArn"]
                        task_arn = task_submitted_output["Tasks"][0]["Containers"][0][
                            "TaskArn"
                        ]
                        task_id = task_arn.split("/")[-1]
                        with Session.begin() as session:
                            session.query(MLModelTrainingJobs).filter(
                                MLModelTrainingJobs.id == ml_model_training_job_id
                            ).update(
                                {
                                    "ecs_task_arn": task_arn,
                                    "ecs_cluster_arn": cluster_arn,
                                    "cloudwatch_log_group_name": "/ecs/execution-engine",
                                    "cloudwatch_log_stream_name": f"ExecutionEngine/ExecutionEngineContainer/{task_id}",
                                }
                            )
                        task_metadata_retrieved = True
                        break
            execution_response = sfn_client.describe_execution(
                executionArn=execution_arn
            )
            if execution_response["status"] == "SUCCEEDED":
                break
            elif execution_response["status"] == "TIMED_OUT":
                with Session.begin() as session:
                    session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                        {"status": HostedMLModelStatus.AVAILABLE.value}
                    )
                    session.query(MLModelTrainingJobs).filter(
                        MLModelTrainingJobs.id == ml_model_training_job_id
                    ).update(
                        {
                            "status": MLModelTrainingJobStatus.FAILED.value,
                            "reason": "Timeout reached during training",
                            "end_time": datetime.now(),
                        }
                    )
                    session.query(MLModelVersions).filter(
                        MLModelVersions.ml_model_id == ml_model_id,
                        MLModelVersions.version == ml_model["latest_version"] + 1,
                    ).delete()
                raise Exception(f"The creation has timed out")
            if execution_response["status"] == "FAILED":
                with Session.begin() as session:
                    session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                        {"status": HostedMLModelStatus.AVAILABLE.value}
                    )
                    session.query(MLModelTrainingJobs).filter(
                        MLModelTrainingJobs.id == ml_model_training_job_id
                    ).update(
                        {
                            "status": MLModelTrainingJobStatus.FAILED.value,
                            "reason": execution_response["cause"],
                            "end_time": datetime.now(),
                        }
                    )
                    session.query(MLModelVersions).filter(
                        MLModelVersions.ml_model_id == ml_model_id,
                        MLModelVersions.version == ml_model["latest_version"] + 1,
                    ).delete()
                raise Exception("Training script execution failed")
            retry += 1
            time.sleep(constants.EXECUTION_ENGINE_RETRY_DELAY)
            if retry == constants.EXECUTION_ENGINE_RETRY_COUNT:
                with Session.begin() as session:
                    session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                        {"status": HostedMLModelStatus.AVAILABLE.value}
                    )
                    session.query(MLModelTrainingJobs).filter(
                        MLModelTrainingJobs.id == ml_model_training_job_id
                    ).update(
                        {
                            "status": MLModelTrainingJobStatus.FAILED.value,
                            "reason": execution_response["cause"],
                            "end_time": datetime.now(),
                        }
                    )
                    session.query(MLModelVersions).filter(
                        MLModelVersions.ml_model_id == ml_model_id,
                        MLModelVersions.version == ml_model["latest_version"] + 1,
                    ).delete()
                raise Exception("Training script execution failed")
        with Session.begin() as session:
            session.query(MLModelTrainingJobs).filter(
                MLModelTrainingJobs.id == ml_model_training_job_id
            ).update(
                {
                    "status": MLModelTrainingJobStatus.SUCCEEDED.value,
                    "end_time": datetime.now(),
                }
            )
            session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                {"latest_version": ml_model["latest_version"] + 1}
            )
            refreshed_ml_model = (
                session.query(MLModel).filter(MLModel.id == ml_model_id).first()
            )
            ml_model_version = (
                session.query(MLModelVersions)
                .filter(
                    MLModelVersions.ml_model_id == ml_model_id,
                    MLModelVersions.version == ml_model["latest_version"] + 1,
                )
                .first()
            )
            ml_model_metrics = ml_model_version.ml_model_metrics
            ml_model_metric_limits = refreshed_ml_model.ml_model_metric_limits
            limit_breached, limit_breaches = self.validate_ml_model_metric_limits(
                ml_model_metrics, ml_model_metric_limits
            )
        if limit_breached:
            with Session.begin() as session:
                session.query(MLModelVersions).filter(
                    MLModelVersions.ml_model_id == ml_model_id,
                    MLModelVersions.version == ml_model["latest_version"] + 1,
                ).update(
                    {
                        "metric_limit_breaches": limit_breaches,
                    }
                )
                session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                    {
                        "status": HostedMLModelStatus.AVAILABLE.value,
                    }
                )
            raise ValueError(f"Metric limits breached: {limit_breaches}")
        with Session.begin() as session:
            hosted_ml_model = (
                session.query(HostedMLModels)
                .filter(
                    HostedMLModels.ml_model_id == ml_model_id,
                    HostedMLModels.version == -1,
                    HostedMLModels.status == "available",
                )
                .first()
            )
        if hosted_ml_model is None:
            with Session.begin() as session:
                session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                    {
                        "status": HostedMLModelStatus.AVAILABLE.value,
                    }
                )
            raise ValueError(
                f"The 'latest' version of the model {ml_model_id} is not hosted"
            )
        with Session.begin() as session:
            session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                {"status": HostedMLModelStatus.DEPLOYING.value}
            )
        ecs_cluster_name = hosted_ml_model.ecs_cluster_name
        ecs_service_name = hosted_ml_model.ecs_service_name
        ecs_client = boto3.client("ecs")
        try:
            task_def_response = ecs_client.describe_task_definition(
                taskDefinition=hosted_ml_model.task_definition_arn
            )
            environment = task_def_response["taskDefinition"]["containerDefinitions"][
                0
            ]["environment"]
            for env in environment:
                if env["name"] == "VERSION":
                    env["value"] = str(ml_model["latest_version"] + 1)
            task_def_response["taskDefinition"]["containerDefinitions"][0][
                "environment"
            ] = environment
            new_task_def_response = ecs_client.register_task_definition(
                family=task_def_response["taskDefinition"]["family"],
                taskRoleArn=task_def_response["taskDefinition"]["taskRoleArn"],
                executionRoleArn=task_def_response["taskDefinition"][
                    "executionRoleArn"
                ],
                networkMode=task_def_response["taskDefinition"]["networkMode"],
                containerDefinitions=task_def_response["taskDefinition"][
                    "containerDefinitions"
                ],
                cpu=task_def_response["taskDefinition"]["cpu"],
                memory=task_def_response["taskDefinition"]["memory"],
            )
            response = ecs_client.update_service(
                cluster=ecs_cluster_name,
                service=ecs_service_name,
                taskDefinition=new_task_def_response["taskDefinition"][
                    "taskDefinitionArn"
                ],
                forceNewDeployment=True,
                deploymentConfiguration={
                    "minimumHealthyPercent": 10,
                },
            )
            time.sleep(70)
            with Session.begin() as session:
                session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                    {
                        "status": HostedMLModelStatus.AVAILABLE.value,
                        "latest_deployed_version": ml_model["latest_version"] + 1,
                    }
                )
        except Exception as e:
            log.error(str(e), exc_info=True)
            with Session.begin() as session:
                session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                    {"status": HostedMLModelStatus.AVAILABLE.value}
                )

    def list_hosted_ml_models(
        self,
        ml_model_id: Optional[uuid.UUID] = None,
    ):
        with Session.begin() as session:
            if ml_model_id is None:
                query_results = (
                    session.query(
                        HostedMLModels,
                        AllUsers.email,
                        AllUsers.role,
                        MLModel.ml_model_name,
                        MLModel.latest_deployed_version,
                    )
                    .join(AllUsers, HostedMLModels.user_id == AllUsers.user_id)
                    .join(
                        MLModel,
                        HostedMLModels.ml_model_id == MLModel.id,
                    )
                    .filter(
                        HostedMLModels.user_id.in_(self.access_resolution_list),
                    )
                    .all()
                )
            else:
                query_results = (
                    session.query(
                        HostedMLModels,
                        AllUsers.email,
                        AllUsers.role,
                        MLModel.ml_model_name,
                        MLModel.latest_deployed_version,
                    )
                    .join(AllUsers, HostedMLModels.user_id == AllUsers.user_id)
                    .join(
                        MLModel,
                        HostedMLModels.ml_model_id == MLModel.id,
                    )
                    .filter(
                        HostedMLModels.user_id.in_(self.access_resolution_list),
                        HostedMLModels.ml_model_id == ml_model_id,
                    )
                    .all()
                )

            hosted_ml_models = []
            if not query_results:
                return []

            for row in query_results:
                hosted_ml_models.append(
                    {
                        "id": row[0].id,
                        "ml_model_id": row[0].ml_model_id,
                        "ml_model_name": row[3],
                        "version": row[4] if row[0].version == -1 else row[0].version,
                        "status": row[0].status,
                        "endpoint_url": row[0].endpoint_url,
                        "creation_date": row[0].creation_date,
                        "reason": row[0].reason,
                        "require_api_key": row[0].require_api_key,
                        "owner": row[1]
                        if row[2] == "root"
                        else row[1].split(constants.ORG_ACCOUNT_SPLIT_TOKEN)[1],
                        "is_latest_version": row[0].version == -1,
                    }
                )
            return hosted_ml_models

    def list_training_jobs(
        self,
        job_id: Optional[uuid.UUID] = None,
        ml_model_id: Optional[uuid.UUID] = None,
    ):
        with Session.begin() as session:
            if job_id is None and ml_model_id is None:
                query_results = (
                    session.query(MLModelTrainingJobs, AllUsers.email, AllUsers.role)
                    .join(AllUsers)
                    .filter(
                        MLModelTrainingJobs.user_id.in_(self.access_resolution_list)
                    )
                    .all()
                )
            else:
                if job_id is not None and ml_model_id is None:
                    query_results = (
                        session.query(
                            MLModelTrainingJobs, AllUsers.email, AllUsers.role
                        )
                        .join(AllUsers)
                        .filter(
                            MLModelTrainingJobs.user_id.in_(
                                self.access_resolution_list
                            ),
                            MLModelTrainingJobs.id == job_id,
                        )
                        .all()
                    )

                elif ml_model_id is not None and job_id is None:
                    query_results = (
                        session.query(
                            MLModelTrainingJobs, AllUsers.email, AllUsers.role
                        )
                        .join(AllUsers)
                        .filter(
                            MLModelTrainingJobs.user_id.in_(
                                self.access_resolution_list
                            ),
                            MLModelTrainingJobs.ml_model_id == ml_model_id,
                        )
                        .all()
                    )

                else:
                    return []

            if not query_results:
                return []

            training_jobs = []

            for row in query_results:
                training_jobs.append(
                    {
                        **{
                            key: row[0].__dict__[key]
                            for key in row[0].__dict__
                            if not key.startswith("_sa_")
                        },
                        "owner": row[1]
                        if row[2] == "root"
                        else row[1].split(constants.ORG_ACCOUNT_SPLIT_TOKEN)[1],
                    }
                )

            return training_jobs

    def create_application_load_balancer(self, max_retries=100, retry_interval=5):
        aws_resources = []
        alb_name = "".join(random.choice(string.ascii_lowercase) for i in range(10))
        security_group_name = "".join(
            random.choice(string.ascii_lowercase) for i in range(10)
        )
        ec2_client = boto3.client("ec2")
        elb_client = boto3.client("elbv2")
        # create security group for ALB
        try:
            security_group_response = ec2_client.create_security_group(
                Description="Security group for ALB",
                GroupName=security_group_name,
                VpcId=constants.VPC_ID,
            )
            aws_resources.append(
                {
                    "resource_type": "security_group",
                    "group_id": security_group_response["GroupId"],
                    "priority": 10,
                }
            )
            # Add ingress rule for http/https to security group
            ec2_client.authorize_security_group_ingress(
                GroupId=security_group_response["GroupId"],
                IpPermissions=[
                    {
                        "FromPort": 80,
                        "IpProtocol": "tcp",
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        "ToPort": 80,
                    },
                    {
                        "FromPort": 443,
                        "IpProtocol": "tcp",
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        "ToPort": 443,
                    },
                ],
            )
            response = elb_client.create_load_balancer(
                Name=alb_name,
                Subnets=[constants.PUBLIC_SUBNET_1, constants.PUBLIC_SUBNET_2],
                SecurityGroups=[security_group_response["GroupId"]],
                Scheme="internet-facing",
                Type="application",
                IpAddressType="ipv4",
            )
            aws_resources.append(
                {
                    "resource_type": "load_balancer",
                    "resource_arn": response["LoadBalancers"][0]["LoadBalancerArn"],
                    "priority": 3,
                }
            )
            row_to_insert = {
                "org_id": self.org_id,
                "load_balancer_arn": response["LoadBalancers"][0]["LoadBalancerArn"],
                "num_target_groups": 0,
                "status": response["LoadBalancers"][0]["State"]["Code"],
                "security_group_id": security_group_response["GroupId"],
            }
            with Session.begin() as session:
                session.add(OrgLoadBalancers(**row_to_insert))
            retry = 0
            while retry < max_retries:
                response = elb_client.describe_load_balancers(
                    LoadBalancerArns=[response["LoadBalancers"][0]["LoadBalancerArn"]]
                )
                if response["LoadBalancers"][0]["State"]["Code"] == "active":
                    break
                if response["LoadBalancers"][0]["State"]["Code"] == "failed":
                    raise Exception("Load balancer creation failed")
                retry += 1
                time.sleep(retry_interval)
                if retry == max_retries:
                    raise Exception("Load balancer creation failed")
            if constants.DEPLOY_ENVIRONMENT == "prod":
                http_listener_response = elb_client.create_listener(
                    LoadBalancerArn=response["LoadBalancers"][0]["LoadBalancerArn"],
                    Protocol="HTTP",
                    Port=80,
                    DefaultActions=[
                        {
                            "Type": "redirect",
                            "RedirectConfig": {
                                "Protocol": "HTTPS",
                                "Port": "443",
                                "StatusCode": "HTTP_301",
                            },
                        }
                    ],
                )
                listener_response = elb_client.create_listener(
                    LoadBalancerArn=response["LoadBalancers"][0]["LoadBalancerArn"],
                    Protocol="HTTPS",
                    Port=443,
                    SslPolicy="ELBSecurityPolicy-TLS13-1-2-2021-06",
                    Certificates=[
                        {
                            "CertificateArn": constants.MODEL_ENDPOINT_LOAD_BALANCER_CERTIFICATE_ARN
                        }
                    ],
                    DefaultActions=[
                        {
                            "Type": "fixed-response",
                            "FixedResponseConfig": {
                                "StatusCode": "404",
                                "ContentType": "application/json",
                                "MessageBody": '{"message": "Not Found"}',
                            },
                        }
                    ],
                )
                domain_prefix = "".join(
                    random.choice(string.ascii_lowercase) for _ in range(5)
                )
                route_53_client = boto3.client("route53")
                route_53_record_set = {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": f"{domain_prefix}.model.preloop.co",
                        "Type": "A",
                        "AliasTarget": {
                            "HostedZoneId": response["LoadBalancers"][0][
                                "CanonicalHostedZoneId"
                            ],
                            "DNSName": response["LoadBalancers"][0]["DNSName"],
                            "EvaluateTargetHealth": False,
                        },
                    },
                }
                route_53_response = route_53_client.change_resource_record_sets(
                    HostedZoneId=constants.MODEL_ENDPOINT_ROUTE_53_HOSTED_ZONE_ID,
                    ChangeBatch={"Changes": [route_53_record_set]},
                )
                with Session.begin() as session:
                    session.query(OrgLoadBalancers).filter(
                        OrgLoadBalancers.org_id == self.org_id,
                        OrgLoadBalancers.load_balancer_arn
                        == response["LoadBalancers"][0]["LoadBalancerArn"],
                    ).update(
                        {"route_53_record": route_53_record_set["ResourceRecordSet"]}
                    )
                endpoint_url = f"https://{domain_prefix}.model.preloop.co"
            else:
                listener_response = elb_client.create_listener(
                    LoadBalancerArn=response["LoadBalancers"][0]["LoadBalancerArn"],
                    Protocol="HTTP",
                    Port=80,
                    DefaultActions=[
                        {
                            "Type": "fixed-response",
                            "FixedResponseConfig": {
                                "StatusCode": "404",
                                "ContentType": "application/json",
                                "MessageBody": '{"message": "Not Found"}',
                            },
                        }
                    ],
                )
                endpoint_url = f"http://{response['LoadBalancers'][0]['DNSName']}"
            with Session.begin() as session:
                session.query(OrgLoadBalancers).filter(
                    OrgLoadBalancers.org_id == self.org_id,
                    OrgLoadBalancers.load_balancer_arn
                    == response["LoadBalancers"][0]["LoadBalancerArn"],
                ).update(
                    {
                        "status": response["LoadBalancers"][0]["State"]["Code"],
                        "listener_arn": listener_response["Listeners"][0][
                            "ListenerArn"
                        ],
                        "url": endpoint_url,
                    }
                )
        except Exception as e:
            log.error(str(e), exc_info=True)
            self.clean_up_aws_resources(aws_resources)
            with Session.begin() as session:
                session.query(OrgLoadBalancers).filter(
                    OrgLoadBalancers.load_balancer_arn
                    == response["LoadBalancers"][0]["LoadBalancerArn"]
                ).delete()
            raise Exception("Load balancer creation failed")

    def stop_ml_model(self, hosted_ml_model_id: uuid.UUID):
        with Session.begin() as session:
            hosted_ml_model = (
                session.query(HostedMLModels)
                .join(MLModel)
                .filter(
                    HostedMLModels.id == hosted_ml_model_id,
                    MLModel.user_id.in_(self.access_resolution_list),
                )
                .first()
            )
            if hosted_ml_model is None:
                raise ValueError(f"Hosted Ml model {hosted_ml_model_id} does not exist")
            if hosted_ml_model.status == HostedMLModelStatus.DEPLOYING.value:
                raise ValueError(f"Hosted Ml model {hosted_ml_model_id} is deploying")
            if hosted_ml_model.status == HostedMLModelStatus.FAILED.value:
                with Session.begin() as session:
                    session.query(HostedMLModels).filter(
                        HostedMLModels.id == hosted_ml_model_id
                    ).delete()
                return
            if hosted_ml_model.status == HostedMLModelStatus.STOPPING.value:
                raise ValueError(
                    f"Hosted Ml model {hosted_ml_model_id} is currently being stopped"
                )
            session.query(HostedMLModels).filter(
                HostedMLModels.id == hosted_ml_model_id
            ).update({"status": HostedMLModelStatus.STOPPING.value})

    def stop_ml_model_async(self, hosted_ml_model_id):
        aws_resources = []
        with Session.begin() as session:
            hosted_ml_model = (
                session.query(HostedMLModels)
                .filter(
                    HostedMLModels.id == hosted_ml_model_id,
                )
                .first()
            )
            session.query(OrgLoadBalancers).filter(
                OrgLoadBalancers.id == hosted_ml_model.load_balancer_id
            ).update({"num_target_groups": OrgLoadBalancers.num_target_groups - 1})
            org_load_balancer = (
                session.query(OrgLoadBalancers)
                .filter(OrgLoadBalancers.id == hosted_ml_model.load_balancer_id)
                .first()
            )
            if org_load_balancer.num_target_groups == 0:
                aws_resources.append(
                    {
                        "resource_type": "load_balancer",
                        "resource_arn": org_load_balancer.load_balancer_arn,
                        "priority": 1,
                    }
                )
                aws_resources.append(
                    {
                        "resource_type": "security_group",
                        "group_id": org_load_balancer.security_group_id,
                        "priority": 4,
                    }
                )
                if org_load_balancer.route_53_record is not None:
                    aws_resources.append(
                        {
                            "resource_type": "route_53_record",
                            "record_set": org_load_balancer.route_53_record,
                            "priority": 1,
                        }
                    )
                session.query(OrgLoadBalancers).filter(
                    OrgLoadBalancers.id == org_load_balancer.id
                ).delete()
        try:
            aws_resources.append(
                {
                    "resource_type": "ecs_service",
                    "cluster_name": hosted_ml_model.ecs_cluster_name,
                    "service_name": hosted_ml_model.ecs_service_name,
                    "priority": 2,
                }
            )
            aws_resources.append(
                {
                    "resource_type": "listener_rule",
                    "resource_arn": hosted_ml_model.listener_rule_arn,
                    "priority": 1,
                }
            )
            aws_resources.append(
                {
                    "resource_type": "ecs_task_definition",
                    "task_definition_arn": hosted_ml_model.task_definition_arn,
                    "priority": 1,
                }
            )
            aws_resources.append(
                {
                    "resource_type": "target_group",
                    "resource_arn": hosted_ml_model.target_group_arn,
                    "priority": 2,
                }
            )
            aws_resources.append(
                {
                    "resource_type": "security_group",
                    "group_id": hosted_ml_model.task_security_group_id,
                    "priority": 3,
                }
            )
            self.clean_up_aws_resources(aws_resources)
        except Exception as e:
            log.error(str(e), exc_info=True)
        with Session.begin() as session:
            session.query(HostedMLModels).filter(
                HostedMLModels.id == hosted_ml_model_id
            ).delete()

    def delete_ml_model(self, ml_model_id: uuid.UUID):
        with Session.begin() as session:
            ml_model = (
                session.query(MLModel)
                .filter(MLModel.id == ml_model_id, MLModel.user_id == self.user_id)
                .first()
            )
            if ml_model is None:
                raise ValueError(f"Ml model {ml_model_id} does not exist")
            if (
                ml_model.status == HostedMLModelStatus.TRAINING.value
                or ml_model.status == HostedMLModelStatus.DEPLOYING.value
            ):
                raise ValueError(f"Ml model cannot be deleted while being provisioned")
            if ml_model.status == HostedMLModelStatus.DELETING.value:
                raise ValueError(f"Ml model {ml_model_id} is currently being deleted")
            session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                {"status": HostedMLModelStatus.DELETING.value}
            )

    def delete_ml_model_async(self, ml_model_id):
        aws_resources = []
        with Session.begin() as session:
            hosted_ml_models = (
                session.query(HostedMLModels)
                .filter(
                    HostedMLModels.ml_model_id == ml_model_id,
                    HostedMLModels.status == HostedMLModelStatus.AVAILABLE.value,
                )
                .all()
            )
            session.query(HostedMLModels).filter(
                HostedMLModels.ml_model_id == ml_model_id,
                HostedMLModels.status == HostedMLModelStatus.AVAILABLE.value,
            ).update({"status": HostedMLModelStatus.STOPPING.value})
            for hosted_ml_model in hosted_ml_models:
                session.query(OrgLoadBalancers).filter(
                    OrgLoadBalancers.id == hosted_ml_model.load_balancer_id
                ).update({"num_target_groups": OrgLoadBalancers.num_target_groups - 1})
                org_load_balancer = (
                    session.query(OrgLoadBalancers)
                    .filter(OrgLoadBalancers.id == hosted_ml_model.load_balancer_id)
                    .first()
                )
                if org_load_balancer.num_target_groups == 0:
                    aws_resources.append(
                        {
                            "resource_type": "load_balancer",
                            "resource_arn": org_load_balancer.load_balancer_arn,
                            "priority": 1,
                        }
                    )
                    aws_resources.append(
                        {
                            "resource_type": "security_group",
                            "group_id": org_load_balancer.security_group_id,
                            "priority": 4,
                        },
                    )
                    if org_load_balancer.route_53_record is not None:
                        aws_resources.append(
                            {
                                "resource_type": "route_53_record",
                                "record_set": org_load_balancer.route_53_record,
                                "priority": 1,
                            }
                        )
                    session.query(OrgLoadBalancers).filter(
                        OrgLoadBalancers.id == org_load_balancer.id
                    ).delete()
        try:
            for hosted_ml_model in hosted_ml_models:
                aws_resources.append(
                    {
                        "resource_type": "ecs_service",
                        "cluster_name": hosted_ml_model.ecs_cluster_name,
                        "service_name": hosted_ml_model.ecs_service_name,
                        "priority": 2,
                    }
                )
                aws_resources.append(
                    {
                        "resource_type": "ecs_task_definition",
                        "task_definition_arn": hosted_ml_model.task_definition_arn,
                        "priority": 1,
                    }
                )
                aws_resources.append(
                    {
                        "resource_type": "security_group",
                        "group_id": hosted_ml_model.task_security_group_id,
                        "priority": 3,
                    }
                )
                aws_resources.append(
                    {
                        "resource_type": "listener_rule",
                        "resource_arn": hosted_ml_model.listener_rule_arn,
                        "priority": 1,
                    }
                )
                aws_resources.append(
                    {
                        "resource_type": "target_group",
                        "resource_arn": hosted_ml_model.target_group_arn,
                        "priority": 2,
                    }
                )
            aws_resources.append(
                {
                    "resource_type": "s3_objects",
                    "object_prefix": f"{self.user_id}/{ml_model_id}/",
                    "priority": 1,
                }
            )
            aws_resources.append(
                {
                    "resource_type": "schedule",
                    "name": str(ml_model_id),
                    "priority": 1,
                }
            )
            self.clean_up_aws_resources(aws_resources)
        except Exception as e:
            log.error(str(e), exc_info=True)
        with Session.begin() as session:
            session.query(MLModel).filter(MLModel.id == ml_model_id).delete()

    def store_ml_model_info(
        self,
        ml_model_id,
        ml_model_package,
        ml_model_type,
        prediction_type,
        ml_model_data_flow,
    ):
        with Session.begin() as session:
            session.query(MLModel).filter(
                MLModel.id == ml_model_id, MLModel.user_id == self.user_id
            ).update(
                {
                    "ml_model_details": {
                        "package": ml_model_package,
                        "type": ml_model_type,
                        "prediction_type": prediction_type,
                    }
                }
            )
            session.query(MLModel).filter(
                MLModel.id == ml_model_id, MLModel.user_id == self.user_id
            ).update({"ml_model_data_flow": json.loads(ml_model_data_flow)})

    def store_ml_model_metrics(self, ml_model_id, version, metrics):
        ml_model_metrics = {}
        ml_model_metric_limits = {}
        for metric in metrics:
            ml_model_metrics[metric["metric_name"]] = metric["metric_value"]
        with Session.begin() as session:
            session.query(MLModelVersions).filter(
                MLModelVersions.ml_model_id == ml_model_id,
                MLModelVersions.version == version,
            ).update(
                {
                    "ml_model_metrics": ml_model_metrics,
                }
            )
            if version == 1:
                for metric in metrics:
                    ml_model_metric_limits[metric["metric_name"]] = {
                        "min_val": metric["min_val"],
                        "max_val": metric["max_val"],
                    }
                session.query(MLModel).filter(MLModel.id == ml_model_id).update(
                    {
                        "ml_model_metric_limits": ml_model_metric_limits,
                    }
                )

    def validate_ml_model_metric_limits(self, ml_model_metrics, ml_model_metric_limits):
        limit_breached = False
        limit_breaches = {"metrics_below_minimum": [], "metrics_above_maximum": []}
        if ml_model_metric_limits is None:
            return False, limit_breaches
        for metric_name in ml_model_metric_limits:
            if (
                ml_model_metric_limits[metric_name]["min_val"] is None
                and ml_model_metric_limits[metric_name]["max_val"] is None
            ):
                continue
            if (
                ml_model_metric_limits[metric_name]["min_val"] is not None
                and ml_model_metrics[metric_name]
                < ml_model_metric_limits[metric_name]["min_val"]
            ):
                limit_breaches["metrics_below_minimum"].append(metric_name)
                limit_breached = True
            if (
                ml_model_metric_limits[metric_name]["max_val"] is not None
                and ml_model_metrics[metric_name]
                > ml_model_metric_limits[metric_name]["max_val"]
            ):
                limit_breaches["metrics_above_maximum"].append(metric_name)
                limit_breached = True
        return limit_breached, limit_breaches

    def list_ml_model_versions(self, ml_model_id: uuid.UUID):
        with Session.begin() as session:
            query_results = (
                session.query(MLModelVersions)
                .join(MLModel, MLModel.id == MLModelVersions.ml_model_id)
                .filter(
                    MLModelVersions.ml_model_id == ml_model_id,
                    MLModelVersions.user_id.in_(self.access_resolution_list),
                    MLModelVersions.version <= MLModel.latest_version,
                )
                .all()
            )
            if not query_results:
                raise ValueError(f"Ml model {ml_model_id} does not exist")
            ml_model_versions = []
            for row in query_results:
                ml_model_versions.append(
                    {
                        "id": row.id,
                        "ml_model_id": row.ml_model_id,
                        "version": row.version,
                        "ml_model_metrics": row.ml_model_metrics,
                        "creation_date": row.creation_date,
                        "ml_model_metric_limit_breaches": row.metric_limit_breaches,
                    }
                )
            return ml_model_versions

    def get_ml_model_counts(self):
        with Session.begin() as session:
            ml_model_counts = (
                session.query(MLModel)
                .filter(MLModel.user_id.in_(self.access_resolution_list))
                .count()
            )
            deployed_ml_model_counts = (
                session.query(HostedMLModels)
                .filter(HostedMLModels.user_id.in_(self.access_resolution_list))
                .count()
            )
            return {
                "trained_ml_models": ml_model_counts,
                "deployed_ml_models": deployed_ml_model_counts,
            }

    def view_ml_model_data_flow(self, ml_model_id: uuid.UUID):
        with Session.begin() as session:
            ml_model = (
                session.query(MLModel)
                .filter(
                    MLModel.id == ml_model_id,
                    MLModel.user_id.in_(self.access_resolution_list),
                )
                .first()
            )
            if ml_model is None:
                raise ValueError(f"Ml model {ml_model_id} does not exist")
            return ml_model.ml_model_data_flow

    def list_undeployed_ml_model_versions(self):
        result = []
        with Session.begin() as session:
            ml_models = (
                session.query(MLModel)
                .filter(
                    MLModel.user_id.in_(self.access_resolution_list),
                    or_(
                        MLModel.status == HostedMLModelStatus.AVAILABLE.value,
                        MLModel.status == HostedMLModelStatus.DEPLOYING.value,
                        MLModel.status == HostedMLModelStatus.TRAINING.value,
                    ),
                )
                .all()
            )
        for ml_model in ml_models:
            is_latest_version_deployed = True
            if ml_model.latest_version == None:
                continue
            ml_model_dict = {
                "ml_model_id": ml_model.id,
                "ml_model_name": ml_model.ml_model_name,
                "versions": [],
            }
            with Session.begin() as session:
                latest_hosted_ml_model = (
                    session.query(HostedMLModels)
                    .filter(
                        HostedMLModels.ml_model_id == ml_model.id,
                        HostedMLModels.version == -1,
                        HostedMLModels.status != HostedMLModelStatus.FAILED.value,
                    )
                    .first()
                )
            if latest_hosted_ml_model is None:
                is_latest_version_deployed = False
                ml_model_dict["versions"].append("latest")
            for i in range(1, ml_model.latest_version + 1):
                if i == ml_model.latest_deployed_version and is_latest_version_deployed:
                    continue
                hosted_ml_model = (
                    session.query(HostedMLModels)
                    .filter(
                        HostedMLModels.ml_model_id == ml_model.id,
                        HostedMLModels.version == i,
                        HostedMLModels.status != HostedMLModelStatus.FAILED.value,
                    )
                    .first()
                )
                if hosted_ml_model is None:
                    ml_model_dict["versions"].append(i)
            result.append(ml_model_dict)
        return result

    def get_training_job_logs(
        self,
        job_id: uuid.UUID,
        limit: int,
        start_time: int,
        end_time: int,
        next_token: Optional[str] = None,
    ):
        logs_client = boto3.client("logs")
        with Session.begin() as session:
            ml_model_training_job = (
                session.query(MLModelTrainingJobs)
                .filter(
                    MLModelTrainingJobs.id == job_id,
                    MLModelTrainingJobs.user_id.in_(self.access_resolution_list),
                )
                .first()
            )
        if ml_model_training_job is None:
            raise ValueError(f"Training job {job_id} does not exist")
        log_group_name = ml_model_training_job.cloudwatch_log_group_name
        log_stream_name = ml_model_training_job.cloudwatch_log_stream_name
        if log_group_name is None:
            raise ValueError(
                f"Please wait, training job {job_id} has not registered logs yet"
            )
        if next_token is None:
            response = logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                limit=limit,
                startTime=start_time,
                endTime=end_time,
            )
            return response
        response = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            limit=limit,
            startTime=start_time,
            endTime=end_time,
            nextToken=next_token,
        )
        return response

    def clean_up_aws_resources(self, resources):
        log.info("Cleaning up resources")
        resources = sorted(resources, key=lambda x: x["priority"])
        log.info(resources)
        for resource in resources:
            try:
                if resource["resource_type"] == "schedule":
                    scheduler_client = boto3.client("scheduler")
                    scheduler_client.delete_schedule(Name=resource["name"])
                if resource["resource_type"] == "listener_rule":
                    elb_client = boto3.client("elbv2")
                    elb_client.delete_rule(RuleArn=resource["resource_arn"])
                if resource["resource_type"] == "target_group":
                    elb_client = boto3.client("elbv2")
                    elb_client.delete_target_group(
                        TargetGroupArn=resource["resource_arn"]
                    )
                if resource["resource_type"] == "ecs_service":
                    ecs_client = boto3.client("ecs")
                    ecs_client.delete_service(
                        cluster=resource["cluster_name"],
                        service=resource["service_name"],
                        force=True,
                    )
                    # Wait until service is inactive
                    retry = 0
                    while retry < 100:
                        response = ecs_client.describe_services(
                            cluster=resource["cluster_name"],
                            services=[resource["service_name"]],
                        )
                        if response["services"][0]["status"] == "INACTIVE":
                            break
                        retry += 1
                        time.sleep(10)
                        if retry == 100:
                            raise Exception("Service deletion failed")
                if resource["resource_type"] == "load_balancer":
                    elb_client = boto3.client("elbv2")
                    elb_client.delete_load_balancer(
                        LoadBalancerArn=resource["resource_arn"]
                    )
                if resource["resource_type"] == "security_group":
                    ec2_client = boto3.client("ec2")
                    ec2_client.delete_security_group(GroupId=resource["group_id"])
                if resource["resource_type"] == "ecs_task_definition":
                    ecs_client = boto3.client("ecs")
                    ecs_client.deregister_task_definition(
                        taskDefinition=resource["task_definition_arn"]
                    )
                    ecs_client.delete_task_definitions(
                        taskDefinitions=[resource["task_definition_arn"]]
                    )
                if resource["resource_type"] == "s3_objects":
                    s3_client = boto3.client("s3")
                    # List objects with prefix
                    s3_objects = s3_client.list_objects_v2(
                        Bucket=f"preloop-ml-objects-{constants.DEPLOY_ENVIRONMENT}",
                        Prefix=resource["object_prefix"],
                    )["Contents"]
                    for s3_object in s3_objects:
                        s3_client.delete_object(
                            Bucket=f"preloop-ml-objects-{constants.DEPLOY_ENVIRONMENT}",
                            Key=s3_object["Key"],
                        )
                if resource["resource_type"] == "route_53_record":
                    route_53_client = boto3.client("route53")
                    route_53_client.change_resource_record_sets(
                        HostedZoneId=constants.MODEL_ENDPOINT_ROUTE_53_HOSTED_ZONE_ID,
                        ChangeBatch={
                            "Changes": [
                                {
                                    "Action": "DELETE",
                                    "ResourceRecordSet": resource["record_set"],
                                }
                            ]
                        },
                    )
            except Exception as e:
                log.info("Continue deleting other resources")

    def get_required_libraries(self, library_list):
        permitted_libraries = ["torch", "torchvision"]
        libraries_to_install = set(permitted_libraries).intersection(set(library_list))
        libraries_to_install_string = ",".join(libraries_to_install)
        return libraries_to_install_string

    def encrypt_env_vars(self, env_vars_string: str):
        env_vars_encryption_key = os.getenv(
            "PRELOOP_USER_SCRIPT_ENV_VARS_ENCRYPTION_KEY"
        )
        fernet_encrypter = Fernet(env_vars_encryption_key)
        encrypted_env_vars = fernet_encrypter.encrypt(env_vars_string.encode()).decode()
        return encrypted_env_vars

    def decrypt_env_vars(self, encrypted_env_vars_string: str):
        env_vars_encryption_key = os.getenv(
            "PRELOOP_USER_SCRIPT_ENV_VARS_ENCRYPTION_KEY"
        )
        fernet_decrypter = Fernet(env_vars_encryption_key)
        decrypted_env_vars = fernet_decrypter.decrypt(
            encrypted_env_vars_string
        ).decode()
        return decrypted_env_vars

    def find_smallest_priority_available_in_alb(self, listener_arn):
        elb_client = boto3.client("elbv2")
        response = elb_client.describe_rules(ListenerArn=listener_arn)
        priorities = set()
        for rule in response["Rules"]:
            if rule["Priority"] != "default":
                priorities.add(int(rule["Priority"]))
        for i in range(1, 81):
            if i not in priorities:
                return i
