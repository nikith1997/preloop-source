from aws_cdk import Duration
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from constructs import Construct


class ExecutionEngineLambda(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        self.repository = ecr.Repository.from_repository_name(
            self,
            "ExecutionEngineLambdaRepo",
            repository_name="preloop-execution-engine-lambda",
        )

        self.execution_engine_lambda_role = iam.Role(
            self,
            "ExecutionEngineLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name="execution-engine-lambda-role",
        )

        # Attach the AmazonECSTaskExecutionRolePolicy
        self.execution_engine_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # Attach a custom policy to the role for S3 read access
        self.execution_engine_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "states:StartExecution",
                    "states:DescribeExecution",
                    "states:StopExecution",
                ],
                resources=["*"],
                # Use ["*"] for resources to allow actions on all state machines
            )
        )

        self.execution_engine_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:CreateNetworkInterface",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DeleteNetworkInterface",
                ],
                resources=["*"],
            )
        )

        self.vpc = ec2.Vpc.from_lookup(
            self, "ExecutionEngineVPC", vpc_name="vpc-preloop"
        )

        self._lambda = lambda_.DockerImageFunction(
            self,
            "ExecutionEngineLambda",
            code=lambda_.DockerImageCode.from_ecr(
                repository=self.repository, tag="latest"
            ),
            memory_size=1024,
            timeout=Duration.seconds(900),
            function_name="ExecutionEngineLambda",
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            role=self.execution_engine_lambda_role,
            vpc=self.vpc,
        )
