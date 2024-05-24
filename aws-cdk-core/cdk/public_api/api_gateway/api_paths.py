from aws_cdk.aws_apigatewayv2 import HttpMethod

PUBLIC_API_PATHS = [
    "/api/datasource/list",
    "/api/datasource/delete",
    "/api/datasource/modify",
    "/api/feature/list",
    "/api/feature/delete",
    "/api/feature/modify",
    "/api/feature/get",
    "/api/feature/upload-script",
    "/api/feature/list-executions",
    "/api/feature/trigger-execution",
    "/api/feature/view-drifts",
    "/api/ml-model/list",
    "/api/ml-model/create",
    "/api/ml-model/retrain",
    "/api/ml-model/list-training-jobs",
    "/api/ml-model/list-hosted-models",
    "/api/ml-model/deploy",
    "/api/ml-model/delete",
    "/api/ml-model/stop",
    "/api/ml-model/list-versions",
]
