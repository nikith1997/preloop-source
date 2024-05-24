from aws_cdk import Stack
from aws_cdk.aws_certificatemanager import Certificate
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationListener
from constructs import Construct

from cdk.public_api.api_gateway.infrastructure import PublicApiGateway


class PreloopPublicApi(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        alb_listener: ApplicationListener,
        preloop_api_certificate: Certificate = None,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        PublicApiGateway(
            self,
            "PublicApiGateway",
            alb_listener=alb_listener,
            preloop_api_certificate=preloop_api_certificate,
        )
