from aws_cdk import Stack
from constructs import Construct

from cdk.backend_certificates.acm.infrastructure import PreloopCertificates


class BackendCertificates(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        preloop_certificates = PreloopCertificates(self, "PreloopCertificates")
        self.public_domain_certificate = preloop_certificates.public_domain_certificate
        self.subdomain_certificate = preloop_certificates.subdomain_certificate
