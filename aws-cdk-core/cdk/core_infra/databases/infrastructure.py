from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_rds as rds
from aws_cdk import aws_sns as sns
from constructs import Construct


class PreloopRDS(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        deploy_env: str,
        vpc: ec2.Vpc,
        alert_sns_topic: sns.Topic,
    ):
        super().__init__(scope, id)

        if deploy_env == "dev":
            instance_type = ec2.InstanceType.of(
                ec2.InstanceClass.T4G, ec2.InstanceSize.XLARGE
            )
            multi_az = False
            allocated_storage = 20

        elif deploy_env == "prod":
            instance_type = ec2.InstanceType.of(
                ec2.InstanceClass.T4G, ec2.InstanceSize.XLARGE
            )
            multi_az = True
            allocated_storage = 100

        self.vpc = vpc

        self.backend_ecs = ecs.Cluster.from_cluster_attributes(
            self,
            "BackendECS",
            cluster_name="preloop-backend-cluster",
            vpc=self.vpc,
        )

        self.inbound_security_rds = ec2.SecurityGroup(
            self,
            "InboundSecurityRDS",
            vpc=self.vpc,
            allow_all_outbound=False,
            security_group_name="preloop-rds-inbound",
        )

        self.inbound_security_rds.add_ingress_rule(
            peer=ec2.Peer.ipv4("0.0.0.0/0"),
            connection=ec2.Port.tcp(5432),
            description="Allow inbound traffic from anywhere for RDS",
        )

        # define a RDS instance of db.m7g.2xlarge. It should
        # have 20 GB of data, should recide in a private isolated
        # subnet, and should be encrypted at rest. Database should
        # be postgresql. Instance should be multi-az deployment
        # with 1 standby instance. The database should be backed up.
        # define the cdk code below
        self.rds = rds.DatabaseInstance(
            self,
            "PreloopRDS",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_4
            ),
            instance_type=instance_type,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            database_name="prelooprds",
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False,
            backup_retention=Duration.days(7),
            multi_az=multi_az,
            allocated_storage=allocated_storage,
            storage_encrypted=True,
            cloudwatch_logs_exports=["postgresql"],
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self,
                "PreloopRDSParameterGroup",
                parameter_group_name="default.postgres15",
            ),
            security_groups=[self.inbound_security_rds],
            instance_identifier="prelooprds",
        )

        if deploy_env == "prod":
            free_storage_space_metric = self.rds.metric_free_storage_space()

            self.free_storage_space_alarm = free_storage_space_metric.create_alarm(
                self,
                "PreloopRDSFreeStorageSpaceAlarm",
                evaluation_periods=1,
                threshold=10_000_000_000,
                comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
                alarm_name="preloop-rds-free-storage-space-alarm",
                actions_enabled=True,
                alarm_description="Alarm when free storage space is less than 10 GB",
                treat_missing_data=cloudwatch.TreatMissingData.BREACHING,
            )

            self.free_storage_space_alarm.add_alarm_action(
                cloudwatch_actions.SnsAction(alert_sns_topic)
            )

            self.read_io_metric = self.rds.metric_read_iops()

            self.read_io_alarm = self.read_io_metric.create_alarm(
                self,
                "PreloopRDSReadIOAlarm",
                evaluation_periods=5,
                threshold=1000,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                alarm_name="preloop-rds-read-io-alarm",
                actions_enabled=True,
                alarm_description="Alarm when read IOPS is greater than 1000",
                treat_missing_data=cloudwatch.TreatMissingData.BREACHING,
            )

            self.read_io_alarm.add_alarm_action(
                cloudwatch_actions.SnsAction(alert_sns_topic)
            )

            self.cpu_utilization_metric = self.rds.metric_cpu_utilization()

            self.cpu_utilization_alarm = self.cpu_utilization_metric.create_alarm(
                self,
                "PreloopRDSCPUUtilizationAlarm",
                evaluation_periods=5,
                threshold=80,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                alarm_name="preloop-rds-cpu-utilization-alarm",
                actions_enabled=True,
                alarm_description="Alarm when CPU utilization is greater than 90%",
                treat_missing_data=cloudwatch.TreatMissingData.BREACHING,
            )

            self.cpu_utilization_alarm.add_alarm_action(
                cloudwatch_actions.SnsAction(alert_sns_topic)
            )
