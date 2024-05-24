from aws_cdk import Stack
from constructs import Construct

from cdk.backend.fargate.infrastructure import BackEndServer
from cdk.backend.sns.alert_topic import AlertSnsTopic


class BackEndAPI(Stack):
    def __init__(self, scope: Construct, id_: str, deploy_env: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)

        alert_sns_topic = AlertSnsTopic(self, "BackEndAlertSnsTopic")
        ecs_backend = BackEndServer(
            self,
            "BackEndServer",
            deploy_env=deploy_env,
            sns_topic=alert_sns_topic.topic,
        )

        self.load_balancer_listener = ecs_backend.fargate_service.listener
