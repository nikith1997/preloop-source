from aws_cdk.aws_certificatemanager import Certificate, CertificateValidation
from constructs import Construct


class PreloopCertificates(Construct):
    def __init__(self, scope: Construct, id: str) -> None:
        super().__init__(scope, id)

        self.public_domain_certificate = Certificate(
            self,
            "PublicDomainCertificate",
            certificate_name="Preloop Public Domain Certificate",
            domain_name="preloop.com",
            subject_alternative_names=["www.preloop.com"],
            validation=CertificateValidation.from_dns(),
        )

        self.subdomain_certificate = Certificate(
            self,
            "SubdomainCertificate",
            certificate_name="Preloop Subdomain Certificate",
            domain_name="*.preloop.com",
            validation=CertificateValidation.from_dns(),
        )
