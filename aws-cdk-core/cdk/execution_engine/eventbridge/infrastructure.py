from aws_cdk import aws_iam as iam
from constructs import Construct


class ExecutionEngineScheduler(Construct):
    def __init__(self, scope: Construct, id: str) -> None:
        super().__init__(scope, id)

        self.scheduler_role = iam.Role(
            self,
            "ExecutionEngineSchedulerRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
            role_name="execution-engine-scheduler-role",
        )

        self.scheduler_role.add_to_policy(
            iam.PolicyStatement(actions=["lambda:InvokeFunction"], resources=["*"])
        )
