import os
from enum import Enum

DB_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


class Environment(str, Enum):
    # different envs for development
    LOCAL = "LOCAL"
    STAGING = "STAGING"
    TESTING = "TESTING"
    PRODUCTION = "PRODUCTION"

    @property
    def is_debug(self):
        return self in (self.LOCAL, self.STAGING, self.TESTING)

    @property
    def is_testing(self):
        return self == self.TESTING

    @property
    def is_deployed(self) -> bool:
        return self in (self.STAGING, self.PRODUCTION)


ORG_ACCOUNT_SPLIT_TOKEN = "##$#$$"

# Execution Engine retry constants
EXECUTION_ENGINE_RETRY_COUNT = 1000
EXECUTION_ENGINE_RETRY_DELAY = 6
LB_MAX_RETRIES = 100
LB_RETRY_DELAY = 5

DEPLOY_ENVIRONMENT = os.getenv("DEPLOY_ENVIRONMENT")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID")
COMPUTE_SUBNET_1 = os.getenv("COMPUTE_SUBNET_1")
COMPUTE_SUBNET_2 = os.getenv("COMPUTE_SUBNET_2")
PUBLIC_SUBNET_1 = os.getenv("PUBLIC_SUBNET_1")
PUBLIC_SUBNET_2 = os.getenv("PUBLIC_SUBNET_2")
MODEL_ENDPOINT_LOAD_BALANCER_SECURITY_GROUP = os.getenv(
    "MODEL_ENDPOINT_LOAD_BALANCER_SECURITY_GROUP"
)
MODEL_ENDPOINT_LOAD_BALANCER_CERTIFICATE_ARN = os.getenv(
    "MODEL_ENDPOINT_LOAD_BALANCER_CERTIFICATE_ARN"
)
VPC_ID = os.getenv("VPC_ID")
MODEL_INFERENCE_ENGINE_FARGATE_EXECUTION_ROLE_ARN = (
    f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/model-inference-engine-fargate-execution-role"
)
MODEL_INFERENCE_ENGINE_FARGATE_TASK_ROLE_ARN = (
    f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/model-inference-engine-fargate-task-role"
)
EXECUTION_ENGINE_STATE_MACHINE_EXECUTION_ARN = f"arn:aws:states:{AWS_DEFAULT_REGION}:{AWS_ACCOUNT_ID}:stateMachine:ExecutionEngineStateMachine"
MODEL_ENDPOINT_ROUTE_53_HOSTED_ZONE_ID = os.getenv(
    "MODEL_ENDPOINT_ROUTE_53_HOSTED_ZONE_ID"
)

# Model related constants TODO: put this in its own Python package


class ModelStatus(str, Enum):
    """
    The status of the model.
    """

    AVAILABLE = "available"
    TRAINING = "training"
    PENDING = "pending"
    DELETING = "deleting"
    FAILED = "failed"


class PackageName(str, Enum):
    """
    The package name of the model.
    """

    SCIKIT_LEARN = "scikit-learn"
    XGBOOST = "xgboost"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"


class PredictionType(str, Enum):
    """
    The prediction type of the model.
    """

    REGRESSION = "regression"
    CLASSIFICATION = "classification"


class ScikitLearnModelType(str, Enum):
    """
    The model class of the scikit-learn model.
    """

    LINEAR_MODEL = "linear_model"
