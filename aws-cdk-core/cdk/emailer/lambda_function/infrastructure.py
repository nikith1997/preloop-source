from aws_cdk import Duration
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from constructs import Construct


class EmailerLambda(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        self.repository = ecr.Repository.from_repository_name(
            self, "EmailerLambdaRepo", repository_name="preloop-emailer-lambda"
        )

        self.emailer_lambda_role = iam.Role(
            self,
            "EmailerLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name="emailer-lambda-role",
        )

        # Attach the AmazonECSTaskExecutionRolePolicy
        self.emailer_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )

        self.emailer_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail", "ses:SendTemplatedEmail"],
                resources=["*"],
            )
        )

        self.emailer_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:CreateNetworkInterface",
                    "ec2:DeleteNetworkInterface",
                    "ec2:DescribeInstances",
                    "ec2:AttachNetworkInterface",
                ],
                resources=["*"],
            )
        )

        self.emailer_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"], resources=["arn:aws:s3:::*/*"]
            )
        )

        self.vpc = ec2.Vpc.from_lookup(
            self, "ExecutionEngineVPC", vpc_name="vpc-preloop"
        )

        self._lambda = lambda_.DockerImageFunction(
            self,
            "EmailerLambda",
            code=lambda_.DockerImageCode.from_ecr(
                repository=self.repository, tag_or_digest="latest"
            ),
            memory_size=1024,
            timeout=Duration.seconds(900),
            function_name="EmailerLambda",
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            role=self.emailer_lambda_role,
            vpc=self.vpc,
        )

        self.api_gw = apigw.LambdaRestApi(
            self,
            "EmailerLambdaAPI",
            handler=self._lambda,
            proxy=True,
            rest_api_name="emailer_lambda_api",
            endpoint_types=[apigw.EndpointType.PRIVATE],
            description="This service is responsible for sending emails to users.",
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=["execute-api:Invoke"],
                        effect=iam.Effect.ALLOW,
                        resources=["execute-api:/*/*/*"],
                        principals=[iam.AnyPrincipal()],
                    )
                ]
            ),
        )

        self.vpc_endpoint = ec2.InterfaceVpcEndpoint(
            self,
            "EmailerLambdaVpcEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.APIGATEWAY,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )
