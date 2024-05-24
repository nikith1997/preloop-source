"""
Constants that are used throughout the CDK repository, including ids, names 
and resource specific configurations. If you want to change or add a new value,
please use this config file to ensure uniformity.
"""
from typing import Dict, List, Optional

from aws_cdk import aws_ec2 as ec2

### Core Infrastructure ###
# ECR Repos
EXECUTION_ENGINE_ID = "ExecutionEngineRepo"
EXECUTION_ENGINE_REPO_NAME = "preloop-execution-engine"

EXECUTION_ENGINE_LAMBDA_ID = "PreloopExecutionEngineLambdaRepo"
EXECUTION_ENGINE_LAMBDA_REPO_NAME = "preloop-execution-engine-lambda"

EMAILER_LAMBDA_ID = "PreloopEmailerLambdaRepo"
EMAILER_LAMBDA_REPO_NAME = "preloop-emailer-lambda"

BACKEND_ID = "PreloopBackendRepo"
BACKEND_REPO_NAME = "preloop-backend"

FRONTEND_ID = "PreloopFrontendRepo"
FRONTEND_REPO_NAME = "preloop-frontend"

# S3 Buckets
# Common
# CDK S3 Bucket IDs
PRELOOP_CUSTOMER_BUCKET_ID = "PreloopCustomerBucket"
PRELOOP_FEATURE_SCRIPT_BUCKET = "PreloopFeatureScriptBucket"
PRELOOP_PUBLIC_BUCKET = "PreloopPublicBucket"

# Dev
# S3 Bucket Names
PRELOOP_CUSTOMER_BUCKET_NAME_DEV = "preloop-users-dev"
PRELOOP_FEATURE_SCRIPT_BUCKET_NAME_DEV = "preloop-feature-scripts-dev"
PRELOOP_PUBLIC_BUCKET_NAME_DEV = "preloop-public-dev"

# Prod
# S3 Bucket Names
PRELOOP_CUSTOMER_BUCKET_NAME_PROD = "preloop-users-prod"
PRELOOP_FEATURE_SCRIPT_BUCKET_NAME_PROD = "preloop-feature-scripts-prod"
PRELOOP_PUBLIC_BUCKET_NAME_PROD = "preloop-public-prod"

# VPC and Networking
VPC_NAME = "vpc-preloop"
VPC_CIDR = "192.168.0.0/16"
VPC_ID = "vpc"
MAX_AZS = 2
PUBLIC_SUBNET_NAME = "Public"
PUBLIC_SUBNET_CIDR_MASK = 20

COMPUTE_SUBNET_NAME = "Compute"
COMPUTE_SUBNET_CIDR_MASK = 20

DATA_SUBNET_NAME = "Data"
DATA_SUBNET_CIDR_MASK = 20

# RDS Primary
# Common
INBOUND_SECURITY_GROUP_ID = "InboundSecurityRDS"
INBOUND_SECURITY_GROUP_NAME = "preloop-rds-inbound"

INGRESS_RULE_DESCRIPTION = "Allow inbound traffic from anywhere for RDS"
INGRESS_RULE_PORT = 5432
INGRESS_RULE_ADDRESS = "0.0.0.0/0"

RDS_CONSTRUCT_ID = "PreloopRDS"
BACKUP_RETENTION_DAYS = 7
PARAMETER_GROUP_ID = "PreloopRDSParameterGroup"
PARAMETER_GROUP_NAME = "default.postgres15"
INSTANCE_IDENTIFIER = "prelooprds"

# Dev
RDS_INSTANCE_SIZE_DEV = ec2.InstanceType.of(
    ec2.InstanceClass.M7G, ec2.InstanceSize.XLARGE2
)

RDS_MULTI_AZ_DEV = False
RDS_ALLOCATED_STORAGE_DEV = 20

# Prod
RDS_INSTANCE_SIZE_PROD = ec2.InstanceType.of(
    ec2.InstanceClass.M7G, ec2.InstanceSize.XLARGE2
)
RDS_MULTI_AZ_PROD = True
RDS_ALLOCATED_STORAGE_PROD = 100

### Emailer ###
# Lambda Function
EMAILER_LAMBDA_ROLE_ID = "EmailerLambdaRole"
EMAILER_LAMBDA_ROLE_NAME = "emailer-lambda-role"

EMAILER_LAMBDA_ID = "EmailerLambda"
EMAILER_LAMBDA_NAME = "EmailerLambda"
EMAILER_LAMBDA_TIMEOUT = 900

EMAILER_LAMBDA_REST_API_NAME = "emailer_lambda_api"
EMAILER_LAMBDA_DESCRIPTION = "This service is responsible for sending emails to users."

EMAILER_LAMBDA_VPC_ENDPOINT_ID = "EmailerLambdaVpcEndpoint"
