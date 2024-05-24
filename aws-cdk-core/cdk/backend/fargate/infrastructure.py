from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_iam as iam
from aws_cdk import aws_sns as sns
from constructs import Construct


class BackEndServer(Construct):
    def __init__(
        self, scope: Construct, id_: str, deploy_env: str, sns_topic: sns.Topic
    ):
        super().__init__(scope, id_)

        if deploy_env == "dev":
            cpu_fargate = 2048
            memory_fargate = 16384
            desired_count = 1

        elif deploy_env == "prod":
            cpu_fargate = 1024
            memory_fargate = 8192
            desired_count = 1

        self.vpc = ec2.Vpc.from_lookup(
            self, "PreloopBackendVPC", vpc_name="vpc-preloop"
        )

        self.cluster = ecs.Cluster(
            self,
            "PreloopBackendServer",
            vpc=self.vpc,
            cluster_name="preloop-backend-cluster",
        )

        self.backend_repository = ecr.Repository.from_repository_name(
            self, "PreloopBackendRepository", repository_name="preloop-backend"
        )

        self.backend_security_group = ec2.SecurityGroup(
            self,
            "PreloopBackendSecurityGroup",
            vpc=self.vpc,
            security_group_name="preloop-backend-security-group",
            description="Security group for preloop backend server",
            allow_all_outbound=True,
        )

        self.backend_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow inbound HTTP traffic",
        )

        self.backend_execution_role = iam.Role(
            self,
            "BackendFargateRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name="backend-fargate-role",
        )

        # Attach the AmazonECSTaskExecutionRolePolicy
        self.backend_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AmazonECSTaskExecutionRolePolicy"
            )
        )

        # Attach EventbridgeSchedulerFullAccess IAM Policy
        self.backend_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonEventBridgeSchedulerFullAccess"
            )
        )

        self.backend_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2FullAccess")
        )

        self.backend_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonECS_FullAccess")
        )

        self.backend_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonRoute53FullAccess")
        )

        self.backend_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction", "logs:GetLogEvents"], resources=["*"]
            )
        )

        self.backend_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "states:DescribeExecution",
                    "states:StartExecution",
                    "states:GetExecutionHistory",
                ],
                resources=["*"],
            )
        )

        # Attach S3FullAccess IAM Policy
        self.backend_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
        )

        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "PreloopBackendFargateService",
            cpu=cpu_fargate,
            memory_limit_mib=memory_fargate,
            desired_count=desired_count,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(self.backend_repository),
                container_port=80,
                family="preloop-backend-task-definition",
                container_name="preloop-backend",
                task_role=self.backend_execution_role,
            ),
            cluster=self.cluster,
            public_load_balancer=False,
            task_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[self.backend_security_group],
            service_name="backend-service-load-balanced",
        )

        self.fargate_service.target_group.configure_health_check(path="/docs")
        if deploy_env == "dev":
            self.fargate_service.service.node.default_child.add_property_override(
                "DesiredCount", 0
            )

        if deploy_env == "prod":
            self.cpu_utilization_metric = (
                self.fargate_service.service.metric_cpu_utilization()
            )
            self.cpu_utilization_alarm = self.cpu_utilization_metric.create_alarm(
                self,
                "PreloopBackendCPUUtilizationAlarm",
                evaluation_periods=5,
                threshold=90,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                alarm_name="preloop-backend-cpu-utilization-alarm",
                actions_enabled=True,
                alarm_description="Alarm when CPU utilization is greater than 80%",
                treat_missing_data=cloudwatch.TreatMissingData.BREACHING,
            )
            self.cpu_utilization_alarm.add_alarm_action(
                cloudwatch_actions.SnsAction(sns_topic)
            )
