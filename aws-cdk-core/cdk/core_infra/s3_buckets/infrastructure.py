import os

from aws_cdk import RemovalPolicy
from aws_cdk import aws_s3 as s3
from constructs import Construct

deploy_env = os.getenv("CDK_DEPLOY_ENVIRONMENT")


class s3Buckets(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        self.preloop_user_bucket = s3.Bucket(
            self,
            "PreloopCustomerBucket",
            bucket_name=f"preloop-users-{deploy_env}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.preloop_feature_script_bucket = s3.Bucket(
            self,
            "PreloopFeatureScriptBucket",
            bucket_name=f"preloop-feature-scripts-{deploy_env}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.preloop_ml_objects_bucket = s3.Bucket(
            self,
            "PreloopMLObjectsBucket",
            bucket_name=f"preloop-ml-objects-{deploy_env}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.preloop_public_bucket = s3.Bucket(
            self,
            "PreloopPublicBucket",
            bucket_name=f"preloop-public-{deploy_env}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
        )
