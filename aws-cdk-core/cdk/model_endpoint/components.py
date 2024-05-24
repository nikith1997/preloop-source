from aws_cdk import Stack
from constructs import Construct

from cdk.model_endpoint.certificates.infrastructure import ModelEndpointCertificates
from cdk.model_endpoint.route_53.infrastructure import ModelEndpointHostedZone


class ModelEndpoint(Stack):
    def __init__(self, scope: Construct, id_: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)

        model_endpoint_hosted_zone = ModelEndpointHostedZone(
            self, "ModelEndpointHostedZone"
        )
        ModelEndpointCertificates(
            self,
            "ModelEndpointCertificates",
            hosted_zone=model_endpoint_hosted_zone.hosted_zone,
        )
