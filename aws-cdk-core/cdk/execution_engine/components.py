from aws_cdk import Stack
from constructs import Construct

from cdk.execution_engine.core.infrastructure import ECSFargateStack
from cdk.execution_engine.eventbridge.infrastructure import ExecutionEngineScheduler
from cdk.execution_engine.lambda_functions.infrastructure import ExecutionEngineLambda


class CoreExecutionEngine(Stack):
    def __init__(self, scope: Construct, id_: str, deploy_env: str, **kwargs) -> None:
        super().__init__(scope, id_, **kwargs)

        ecs_fargate_stack = ECSFargateStack(self, "ECSFargateStackExecutionEngine")
        ecs_lambda_stack = ExecutionEngineLambda(self, "ExecutionEngineLambdaStack")
        ecs_scheduler_stack = ExecutionEngineScheduler(
            self, "ExecutionEngineSchedulerStack"
        )
