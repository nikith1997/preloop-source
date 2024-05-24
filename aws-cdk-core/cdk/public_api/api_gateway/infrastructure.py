import os

from aws_cdk.aws_apigatewayv2 import (
    DomainMappingOptions,
    DomainName,
    HttpApi,
    HttpMethod,
    VpcLink,
)
from aws_cdk.aws_apigatewayv2_integrations import HttpAlbIntegration
from aws_cdk.aws_certificatemanager import Certificate
from aws_cdk.aws_ec2 import SecurityGroup, Vpc
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationListener, ApplicationProtocol
from constructs import Construct

from cdk.public_api.api_gateway.api_paths import PUBLIC_API_PATHS


class PublicApiGateway(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        alb_listener: ApplicationListener,
        preloop_api_certificate: Certificate,
    ) -> None:
        super().__init__(scope, id)

        vpc = Vpc.from_lookup(self, "PreloopBackendVPC", vpc_name="vpc-preloop")

        deploy_env = os.getenv("CDK_DEPLOY_ENVIRONMENT")

        vpc_link_security_group = SecurityGroup(
            self,
            "VpcLinkSecurityGroup",
            vpc=vpc,
            description="Security group for API GW VPC Link",
        )

        vpc_link = VpcLink(
            self,
            "VpcLink",
            vpc=vpc,
            vpc_link_name="PreloopPublicApiVpcLink",
            security_groups=[vpc_link_security_group],
        )

        alb_integration = HttpAlbIntegration(
            "AlbIntegration", alb_listener, vpc_link=vpc_link
        )

        if deploy_env == "prod":
            preloop_api_domain_name = DomainName(
                self,
                "PreloopApiDomainName",
                domain_name="api.preloop.com",
                certificate=preloop_api_certificate,
            )

            preloop_public_api = HttpApi(
                self,
                "PreloopPublicApi",
                api_name="Preloop Public API",
                description="Http API for public endpoints",
                default_domain_mapping=DomainMappingOptions(
                    domain_name=preloop_api_domain_name
                ),
            )
        else:
            preloop_public_api = HttpApi(
                self,
                "PreloopPublicApi",
                api_name="Preloop Public API",
                description="Http API for public endpoints",
            )
        for path in PUBLIC_API_PATHS:
            preloop_public_api.add_routes(
                path=path, methods=[HttpMethod.ANY], integration=alb_integration
            )
