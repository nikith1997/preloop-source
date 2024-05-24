from aws_cdk import Stack  # Duration,; aws_sqs as sqs,
from constructs import Construct

from cdk.core_infra.alert_sns_topic.infrastructure import AlertSnsTopic
from cdk.core_infra.databases.infrastructure import PreloopRDS
from cdk.core_infra.ecr_repos.infrastructure import ECRRepos
from cdk.core_infra.networking.infrastructure import VPCSetup
from cdk.core_infra.s3_buckets.infrastructure import s3Buckets


class CoreInfra(Stack):
    def __init__(self, scope: Construct, id_: str, deploy_env: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)
        alert_sns_topic = AlertSnsTopic(self, "CoreInfraAlertSnsTopic")

        vpc = VPCSetup(self, "MainVPC")
        ecr = ECRRepos(self, "ECRReposExecutionEngine")
        s3 = s3Buckets(self, "S3Buckets")
        rds = PreloopRDS(
            self,
            "PreloopRDS",
            deploy_env=deploy_env,
            vpc=vpc.vpc,
            alert_sns_topic=alert_sns_topic.topic,
        )
