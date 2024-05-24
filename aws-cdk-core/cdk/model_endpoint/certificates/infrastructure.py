from aws_cdk.aws_certificatemanager import Certificate, CertificateValidation
from aws_cdk.aws_route53 import HostedZone
from constructs import Construct


class ModelEndpointCertificates(Construct):
    def __init__(self, scope: Construct, id: str, hosted_zone: HostedZone) -> None:
        super().__init__(scope, id)

        self.public_domain_certificate = Certificate(
            self,
            "ModelEndpointCertificate",
            certificate_name="Preloop Model Endpoint Certificate",
            domain_name="*.model.preloop.co",
            validation=CertificateValidation.from_dns(hosted_zone=hosted_zone),
        )
