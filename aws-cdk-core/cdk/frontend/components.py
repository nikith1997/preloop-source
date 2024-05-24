from aws_cdk import Stack
from aws_cdk.aws_certificatemanager import Certificate
from constructs import Construct

from cdk.frontend.fargate.infrastructure import FrontEndServer
from cdk.frontend.sns.alert_topic import AlertSnsTopic


class FrontEnd(Stack):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        deploy_env: str,
        certificate: Certificate = None,
        **kwargs
    ) -> None:
        super().__init__(scope, id_, **kwargs)

        self.alert_sns_topic = AlertSnsTopic(self, "FrontEndAlertSnsTopic")

        self.ecs_frontend = FrontEndServer(
            self,
            "FrontEndServer",
            deploy_env=deploy_env,
            certificate=certificate,
            alert_topic=self.alert_sns_topic.topic,
        )

        self.load_balancer_listener = self.ecs_frontend.fargate_service.listener
