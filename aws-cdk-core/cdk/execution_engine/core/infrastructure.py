from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks
from constructs import Construct


class ECSFargateStack(Construct):
    def __init__(self, scope: Construct, id_: str):
        super().__init__(scope, id_)

        self.vpc = ec2.Vpc.from_lookup(
            self, "ExecutionEngineVPC", vpc_name="vpc-preloop"
        )

        self.cluster = ecs.Cluster(
            self,
            "ExecutionEngineCluster",
            vpc=self.vpc,
            cluster_name="ExecutionEngineCluster",
        )

        self.repository = ecr.Repository.from_repository_name(
            self, "ExecutionEngineRepo", repository_name="preloop-execution-engine"
        )

        self.execution_engine_fargate_role = iam.Role(
            self,
            "ExecutionEngineFargateRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name="execution-engine-fargate-role",
        )

        # Attach the AmazonECSTaskExecutionRolePolicy
        self.execution_engine_fargate_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AmazonECSTaskExecutionRolePolicy"
            )
        )

        # Attach a custom policy to the role for S3 read access
        self.execution_engine_fargate_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject"],
                resources=["*"],  # Specify your S3 bucket ARN(s) here
            )
        )

        # Attach a custom policy to the role for step functions permissions
        self.execution_engine_fargate_role.add_to_policy(
            iam.PolicyStatement(
                actions=["states:SendTaskSuccess", "states:SendTaskFailure"],
                resources=["*"],
            )
        )

        self.execution_engine_fargate_role.assume_role_policy.add_statements(
            iam.PolicyStatement(
                actions=["sts:AssumeRole", "sts:TagSession"],
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("pods.eks.amazonaws.com")],
            )
        )

        self.log_group = logs.LogGroup(
            self,
            "ExecutionEngineLogs",
            log_group_name="/ecs/execution-engine",
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.task_definition = ecs.FargateTaskDefinition(
            self,
            "ExecutionEngineTaskDefinition",
            cpu=8192,
            memory_limit_mib=16384,
            ephemeral_storage_gib=100,
            task_role=self.execution_engine_fargate_role,
        )

        self.container = self.task_definition.add_container(
            "ExecutionEngineContainer",
            image=ecs.ContainerImage.from_ecr_repository(self.repository, "latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="ExecutionEngine", log_group=self.log_group
            ),
        )

        self.container.add_port_mappings(ecs.PortMapping(container_port=80))

        self.run_task = sfn_tasks.EcsRunTask(
            self,
            "ExecutionEngineRun",
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            task_timeout=sfn.Timeout.duration(Duration.minutes(100)),
            task_definition=self.task_definition,
            launch_target=sfn_tasks.EcsFargateLaunchTarget(
                platform_version=ecs.FargatePlatformVersion.LATEST
            ),
            cluster=self.cluster,
            container_overrides=[
                sfn_tasks.ContainerOverride(
                    container_definition=self.task_definition.default_container,
                    environment=[
                        sfn_tasks.TaskEnvironmentVariable(
                            name="SCRIPT_LOC",
                            value=sfn.JsonPath.string_at("$.SCRIPT_LOC"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="KEY_ID", value=sfn.JsonPath.string_at("$.KEY_ID")
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="SECRET", value=sfn.JsonPath.string_at("$.SECRET")
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="SCHEDULING_EXPRESSION",
                            value=sfn.JsonPath.string_at("$.SCHEDULING_EXPRESSION"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="VERSIONING",
                            value=sfn.JsonPath.string_at("$.VERSIONING"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="EXECUTION_TYPE",
                            value=sfn.JsonPath.string_at("$.EXECUTION_TYPE"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="EXECUTION_ID",
                            value=sfn.JsonPath.string_at("$.EXECUTION_ID"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="FEATURE_DRIFT_ENABLED",
                            value=sfn.JsonPath.string_at("$.FEATURE_DRIFT_ENABLED"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="ML_MODEL_TRAINING",
                            value=sfn.JsonPath.string_at("$.ML_MODEL_TRAINING"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="ML_MODEL_RETRAINING",
                            value=sfn.JsonPath.string_at("$.ML_MODEL_RETRAINING"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="ML_MODEL_ID",
                            value=sfn.JsonPath.string_at("$.ML_MODEL_ID"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="LATEST_VERSION",
                            value=sfn.JsonPath.string_at("$.LATEST_VERSION"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="VERSION", value=sfn.JsonPath.string_at("$.VERSION")
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="LIBRARIES",
                            value=sfn.JsonPath.string_at("$.LIBRARIES"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="LOOP_LINE_NUMBERS",
                            value=sfn.JsonPath.string_at("$.LOOP_LINE_NUMBERS"),
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="ENV_VARS", value=sfn.JsonPath.string_at("$.ENV_VARS")
                        ),
                        sfn_tasks.TaskEnvironmentVariable(
                            name="TASK_TOKEN",
                            value=sfn.JsonPath.string_at("$$.Task.Token"),
                        ),
                    ],
                )
            ],
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        self.run_task.add_catch(
            handler=sfn.Fail(
                self,
                "Script Execution Fail State",
                error="ScriptExecutionFailed",
                cause_path="$.Cause",
            ),
            errors=["ScriptExecutionFailed"],
        )
        self.run_task.add_catch(
            handler=sfn.Fail(
                self,
                "Script Timeout Fail State",
                error="ScriptExecutionTimedOut",
                cause="Script execution timed out",
            ),
            errors=["States.Timeout"],
        )
        self.run_task.add_catch(
            handler=sfn.Fail(
                self,
                "Catch All Fail State",
                error="StateMachineFailed",
                cause="An unknown error has occurred",
            ),
            errors=["States.ALL"],
        )
        self.success_task = sfn.Succeed(self, "SuccessTask")

        self.definition = sfn.Chain.start(self.run_task).next(self.success_task)
        self.state_machine = sfn.StateMachine(
            self,
            "ExecutionEngineStateMachine",
            definition=self.definition,
            state_machine_name="ExecutionEngineStateMachine",
        )
