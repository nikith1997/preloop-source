from aws_cdk import Stack
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationLoadBalancer
from constructs import Construct

from cdk.waf.web_acl.infrastructure import WebAcl


class PreloopWaf(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        front_end_alb: ApplicationLoadBalancer,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        WebAcl(
            self,
            "WebAcl",
            front_end_alb=front_end_alb,
        )
