from aws_cdk.aws_route53 import HostedZone
from constructs import Construct


class ModelEndpointHostedZone(Construct):
    def __init__(self, scope: Construct, id: str) -> None:
        super().__init__(scope, id)

        self.hosted_zone = HostedZone(self, "HostedZone", zone_name="preloop.co")
