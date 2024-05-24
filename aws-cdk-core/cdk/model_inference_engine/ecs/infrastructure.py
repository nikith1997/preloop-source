import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_iam as iam
import aws_cdk.aws_logs as logs
from aws_cdk import RemovalPolicy
from constructs import Construct


class ModelInferenceEngineECS(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        self.vpc = ec2.Vpc.from_lookup(
            self, "ModelInferenceEngineVPC", vpc_name="vpc-preloop"
        )

        self.cluster = ecs.Cluster(
            self,
            "ModelInferenceEngineCluster",
            cluster_name="ModelInferenceEngineCluster",
            vpc=self.vpc,
        )

        self.fargate_execution_role = iam.Role(
            self,
            "ModelInferenceEngineFargateExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name="model-inference-engine-fargate-execution-role",
        )

        # Attach the AmazonECSTaskExecutionRolePolicy
        self.fargate_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AmazonECSTaskExecutionRolePolicy"
            )
        )

        self.fargate_task_role = iam.Role(
            self,
            "ModelInferenceEngineFargateTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name="model-inference-engine-fargate-task-role",
        )

        # Attach a custom policy to the role for S3 read access
        self.fargate_task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "cloudwatch:PutMetricData"],
                resources=["*"],  # Specify your S3 bucket ARN(s) here
            )
        )

        # Create a log group
        self.log_group = logs.LogGroup(
            self,
            "ModelInferenceEngineLogGroup",
            log_group_name="/ecs/model-inference-engine",
            removal_policy=RemovalPolicy.DESTROY,
        )
