from enum import Enum


class DatasourceAPIPaths(str, Enum):
    """
    The different API paths for the datasource API are defined in this
    enum. There are 4 main endpoints that all start with the parent
    word datasource:

    datasource/create: Used to create a new datasource.
    datasource/list: List all the datasources that are available for a given account.
    datasource/describe: Used to describe a given datasource.
    datasource/delete: Used to delete a given datasource.
    datasource/modify: Used to modify a given datasource.
    """

    DATASOURCE_CREATE = "/api/datasource"
    DATASOURCE_LIST = "/api/datasource/list"
    DATASOURCE_DESCRIBE = "/api/datasource/describe"
    DATASOURCE_DELETE = "/api/datasource/delete"
    DATASOURCE_MODIFY = "/api/datasource/modify"
    DATASOURCE_CONNECT = "/api/datasource/connect"  # internal use only
    DATASOURCE_GET = "/api/datasource/get"
    DATASOURCE_GET_ID = "/api/datasource/get/id"


class FeatureAPIPaths(str, Enum):
    """
    The different API paths for the feature API are defined in this
    enum. There are 5 main endpoints that all start with the parent
    word feature:

    feature/create: Used to create a new feature.
    feature/list: List all the features that are available for a given account.
    feature/describe: Used to describe a given feature.
    feature/delete: Used to delete a given feature.
    feature/modify: Used to modify a given feature.
    """

    FEATURE_CREATE = "/api/feature/create"
    FEATURE_LIST = "/api/feature/list"
    FEATURE_DESCRIBE = "/api/feature/describe"
    FEATURE_DELETE = "/api/feature/delete"
    FEATURE_MODIFY = "/api/feature/modify"
    FEATURE_RUN = "/api/feature/run"
    FEATURE_INSERT = "/api/feature/insert"
    FEATURE_GET = "/api/feature/get"
    FEATURE_EXPERIMENTAL_GET = "/api/feature/experimental/get"
    FEATURE_EXPERIMENTAL_CREATE = "/api/feature/experimental/create"
    FEATURE_GET_ID = "/api/feature/get/id"
    FEATURE_SCHEDULED_EXECUTION = "/api/feature/scheduled-execution"
    FEATURE_STORE_DRIFT = "/api/feature/store-drift"
