import os


class Constants:
    DEPLOY_ENVIRONMENT = os.getenv("DEPLOY_ENVIRONMENT")
    S3_FEATURE_SCRIPTS_BUCKET = f"preloop-feature-scripts-{DEPLOY_ENVIRONMENT}"
    EXECUTION_ENGINE_LAMBDA_NAME = "ExecutionEngineLambda"
