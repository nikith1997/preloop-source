from enum import Enum

# class DatasourceAPIPaths(str, Enum):
#     """
#     The different API paths for the datasource API are defined in this
#     enum. There are 4 main endpoints that all start with the parent
#     word datasource:

#     datasource/create: Used to create a new datasource.
#     datasource/list: List all the datasources that are available for a given account.
#     datasource/describe: Used to describe a given datasource.
#     datasource/delete: Used to delete a given datasource.
#     datasource/modify: Used to modify a given datasource.
#     """

#     DATASOURCE_LIST = "/api/datasource/list"
#     DATASOURCE_DELETE = "/api/datasource/delete"
#     DATASOURCE_MODIFY = "/api/datasource/modify"


# class FeatureAPIPaths(str, Enum):
#     """
#     The different API paths for the feature API are defined in this
#     enum. There are 5 main endpoints that all start with the parent
#     word feature:

#     feature/create: Used to create a new feature.
#     feature/list: List all the features that are available for a given account.
#     feature/describe: Used to describe a given feature.
#     feature/delete: Used to delete a given feature.
#     feature/modify: Used to modify a given feature.
#     """

#     FEATURE_LIST = "/api/feature/list"
#     FEATURE_DELETE = "/api/feature/delete"
#     FEATURE_MODIFY = "/api/feature/modify"
#     FEATURE_GET = "/api/feature/get"
#     FEATURE_EXPERIMENTAL_GET = "/api/feature/experimental/get"
#     FEATURE_UPLOAD_SCRIPT = "/api/feature/upload-script"
#     FEATURE_LIST_EXECUTIONS = "/api/feature/list-executions"
#     FEATURE_TRIGGER_EXECUTION = "/api/feature/trigger-execution"
#     FEATURE_VIEW_DRIFTS = "/api/feature/view-drifts"


class MLModelAPIPaths(str, Enum):
    """
    The different API paths for the ML Model API are defined in this
    enum.
    """

    ML_MODEL_CREATE = "/api/ml-model/create"
    ML_MODEL_LIST = "/api/ml-model/list"
    ML_MODEL_RETRAIN = "/api/ml-model/retrain"
    ML_MODEL_LIST_TRAINING_JOBS = "/api/ml-model/list-training-jobs"
    ML_MODEL_LIST_HOSTED_MODELS = "/api/ml-model/list-hosted-models"
    ML_MODEL_DEPLOY = "/api/ml-model/deploy"
    ML_MODEL_DELETE = "/api/ml-model/delete"
    ML_MODEL_STOP = "/api/ml-model/stop"
    ML_MODEL_LIST_VERSIONS = "/api/ml-model/list-versions"
