import os

from aws_cdk import Tags
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_sns as sns
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class FrontEndServer(Construct):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        deploy_env: str,
        certificate: acm.Certificate,
        alert_topic: sns.Topic,
    ):
        super().__init__(scope, id_)

        self.vpc = ec2.Vpc.from_lookup(
            self, "PreloopBackendVPC", vpc_name="vpc-preloop"
        )

        self.cluster = ecs.Cluster(
            self,
            "PreloopFrontendServer",
            vpc=self.vpc,
            cluster_name="preloop-frontend-cluster",
        )

        self.frontend_repository = ecr.Repository.from_repository_name(
            self, "PreloopFrontendRepository", repository_name="preloop-frontend"
        )

        self.frontend_security_group = ec2.SecurityGroup(
            self,
            "PreloopFrontendSecurityGroup",
            vpc=self.vpc,
            security_group_name="preloop-frontend-security-group",
            description="Security group for preloop frontend server",
            allow_all_outbound=True,
        )

        self.frontend_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(3000),
            description="Allow inbound HTTP traffic",
        )

        if deploy_env == "dev":
            self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
                self,
                "PreloopFrontendFargateService",
                cpu=2048,
                memory_limit_mib=16384,
                desired_count=1,
                task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                    image=ecs.ContainerImage.from_ecr_repository(
                        self.frontend_repository
                    ),
                    container_port=3000,
                    family="preloop-frontend-task-definition",
                    container_name="preloop-frontend",
                ),
                cluster=self.cluster,
                public_load_balancer=False,
                task_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
                security_groups=[self.frontend_security_group],
                service_name="frontend-service-load-balanced",
            )
            self.load_balancer = self.fargate_service.load_balancer
            self.fargate_service.service.node.default_child.add_property_override(
                'DesiredCount', 0
            )

        elif deploy_env == "prod":
            self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
                self,
                "PreloopFrontendFargateService",
                cpu=1024,
                memory_limit_mib=8192,
                desired_count=1,
                task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                    image=ecs.ContainerImage.from_ecr_repository(
                        self.frontend_repository
                    ),
                    container_port=3000,
                    family="preloop-frontend-task-definition",
                    container_name="preloop-frontend",
                ),
                cluster=self.cluster,
                public_load_balancer=True,
                task_subnets=ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                ),
                security_groups=[self.frontend_security_group],
                service_name="frontend-service-load-balanced",
                certificate=certificate,
                redirect_http=True,
            )

            self.load_balancer = self.fargate_service.load_balancer
            ssm.StringParameter(
                self,
                "LoadBalancerARN",
                parameter_name="/preloop/frontend/load-balancer-arn",
                string_value=self.load_balancer.load_balancer_arn,
            )
            self.cpu_utilization_metric = (
                self.fargate_service.service.metric_cpu_utilization()
            )
            self.cpu_utilization_alarm = self.cpu_utilization_metric.create_alarm(
                self,
                "PreloopFrontendCPUUtilizationAlarm",
                evaluation_periods=5,
                threshold=90,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                alarm_name="preloop-frontend-cpu-utilization-alarm",
                actions_enabled=True,
                alarm_description="Alarm when CPU utilization is greater than 80%",
                treat_missing_data=cloudwatch.TreatMissingData.BREACHING,
            )
            self.cpu_utilization_alarm.add_alarm_action(
                cloudwatch_actions.SnsAction(alert_topic)
            )

        self.fargate_service.target_group.configure_health_check(path="/")
