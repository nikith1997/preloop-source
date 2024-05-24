from aws_cdk import RemovalPolicy
from aws_cdk import aws_ecr as ecr
from constructs import Construct


class ECRRepos(Construct):
    def __init__(self, scope: Construct, id_: str):
        super().__init__(scope, id_)

        self.ecr_execution_engine_repo_name = "preloop-execution-engine"
        self.ecr_execution_engine_lambda_repo = "preloop-execution-engine-lambda"
        self.ecr_emailer_lambda_repo = "preloop-emailer-lambda"
        self.preloop_frontend = "preloop-frontend"

        self.ecr_execution_engine_repo = ecr.Repository(
            self,
            "ExecutionEngineRepo",
            repository_name=self.ecr_execution_engine_repo_name,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_images=True,
        )

        self.ecr_adhoc_init_run_lambda_repo = ecr.Repository(
            self,
            "PreloopExecutionEngineLambdaRepo",
            repository_name=self.ecr_execution_engine_lambda_repo,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_images=True,
        )

        self.ecr_emailer_lambda_repo = ecr.Repository(
            self,
            "PreloopEmailerLambdaRepo",
            repository_name=self.ecr_emailer_lambda_repo,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_images=True,
        )

        self.preloop_backend = ecr.Repository(
            self,
            "PreloopBackendRepo",
            repository_name="preloop-backend",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_images=True,
        )

        self.preloop_frontend = ecr.Repository(
            self,
            "PreloopFrontendRepo",
            repository_name=self.preloop_frontend,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_images=True,
        )

        self.model_inference_engine = ecr.Repository(
            self,
            "ModelInferenceEngineRepo",
            repository_name="preloop-model-inference-engine",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_images=True,
        )
