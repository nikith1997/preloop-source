import logging
import os
import sys
from typing import Any, List

import pandas as pd
from preloop_private_api_stubs import (
    CreateFeatureRequest,
    ExecutionType,
    GetDatasourceIdRequest,
    GetFeatureIdRequest,
    InsertFeatureRequest,
    ListDatasourcesRequest,
    PreloopError,
    PreloopPrivateClient,
    StoreFeatureDriftRequest,
)

from preloop.sdk.inception.models import Datasource

preloop_client = PreloopPrivateClient()
log = logging.getLogger(__name__)


class datasources:
    created_datasource_ids = []
    created_datasource_names = []
    decorator_execution_status = False
    decorator_applied_status = False

    def __init__(self, func) -> None:
        if datasources.decorator_applied_status is True:
            raise PreloopError("This decorator can only be applied on one function")
        datasources.decorator_applied_status = True
        self.func = func

    def __call__(self, *args: Any, **kwargs: Any) -> List[Datasource]:
        if datasources.decorator_execution_status is True:
            raise PreloopError("Datasources decorated function can only be executed once")
        datasources.decorator_execution_status = True
        datasource_list: List[Datasource] = list(self.func(*args, **kwargs))
        if os.getenv("EXECUTION_TYPE") == ExecutionType.FIRST_RUN.value:
            for datasource in datasource_list:
                datasource_id = preloop_client.create_datasource(request=datasource).id
                datasources.created_datasource_names.append(datasource.datasource_name)
                datasources.created_datasource_ids.append(datasource_id)
            return datasource_list
        for datasource in datasource_list:
            preloop_client.list_datasources(
                request=ListDatasourcesRequest(
                    datasource_id=preloop_client.get_datasource_id(
                        GetDatasourceIdRequest(datasource_name=datasource.datasource_name)
                    ).details["datasource_id"]
                )
            )
        return datasource_list


class feature:
    decorator_execution_status = False
    decorator_applied_status = False
    created_feature_id = []

    def __init__(
        self,
        name: str,
        description: str,
        id_cols: List[str],
        feature_cols: List[str],
        existing_datasource_names: List[str] = None,
        target_cols: List[str] = None,
    ):
        if feature.decorator_applied_status:
            raise Exception("Feature decorator can only be applied to one function")
        feature.decorator_applied_status = True
        self.name = name
        self.description = description
        self.id_cols = id_cols
        self.feature_cols = feature_cols
        self.target_cols = target_cols
        self.existing_datasource_names = existing_datasource_names
        self.feature_drift_enabled = False if os.getenv("FEATURE_DRIFT_ENABLED").lower() == "false" else True
        self.scheduling_expression = os.getenv("SCHEDULING_EXPRESSION")
        self.versioning = False if os.getenv("VERSIONING").lower() == "false" else True
        self.script_loc = os.getenv("SCRIPT_LOC")
        self.execution_id = os.getenv("EXECUTION_ID")

    def __call__(self, func) -> Any:
        def wrapper(*args, **kwargs):
            if feature.decorator_execution_status:
                raise PreloopError("Feature decorated function can only be called once")
            feature.decorator_execution_status = True
            feature_data = func(*args, **kwargs)
            if not isinstance(feature_data, pd.DataFrame):
                raise PreloopError("Function must return a pandas dataframe")
            feature_data.reset_index(inplace=True)
            column_names = feature_data.columns.to_list()
            for feature_col in self.feature_cols:
                if feature_col not in column_names:
                    raise PreloopError(f"Specifed feature column {feature_col} not a column in dataframe")
            for id_col in self.id_cols:
                if id_col not in column_names:
                    raise PreloopError(f"Specified Id column {id_col} not a column in dataframe")
            if self.target_cols is not None:
                for target_col in self.target_cols:
                    if target_col not in column_names:
                        raise PreloopError(f"Specified target column {target_col} not a column in dataframe")
            feature_data = (
                feature_data[self.feature_cols + self.id_cols + self.target_cols]
                if self.target_cols is not None
                else feature_data[self.feature_cols + self.id_cols]
            )
            try:
                feature_data.set_index(keys=self.id_cols, verify_integrity=True, inplace=True)
            except ValueError:
                raise PreloopError("The provided index columns don't uniquely identify rows in the dataframe") from None
            final_datasource_names = (
                datasources.created_datasource_names + self.existing_datasource_names
                if self.existing_datasource_names is not None
                else datasources.created_datasource_names
            )
            if os.getenv("EXECUTION_TYPE") == ExecutionType.FIRST_RUN.value:
                create_feature_request = CreateFeatureRequest(
                    datasource_names=final_datasource_names,
                    feature_name=self.name,
                    feature_description=self.description,
                    column_types=feature_data.dtypes.astype(str).to_dict(),
                    feature_dest="preloop datastore",
                    feature_cols=self.feature_cols,
                    id_cols=self.id_cols,
                    target_cols=self.target_cols,
                    scheduling_expression_string=self.scheduling_expression,
                    creation_method="inception",
                    versioning=self.versioning,
                    latest_version=1,
                    script_loc=self.script_loc,
                    execution_id=self.execution_id,
                    feature_drift_enabled=self.feature_drift_enabled,
                )
                response = preloop_client.create_feature(request=create_feature_request)
                feature.created_feature_id.append(response.details["id"])
            feature_id = preloop_client.get_feature_id(GetFeatureIdRequest(feature_name=self.name)).details[
                "feature_id"
            ]
            if self.feature_drift_enabled:
                drifts = {}
                means = dict(feature_data.mean(numeric_only=True))
                stds = dict(feature_data.std(numeric_only=True))
                for col in means.keys():
                    drifts[col] = {"mean": means.get(col, 0), "std": stds.get(col, 0)}
                store_feature_drift_request = StoreFeatureDriftRequest(
                    feature_id=feature_id, execution_type=ExecutionType(os.getenv("EXECUTION_TYPE")), drifts=drifts
                )
                preloop_client.store_feature_drift(store_feature_drift_request)
            insert_feature_data_request = InsertFeatureRequest(
                feature_id=feature_id, operation_type=ExecutionType(os.getenv("EXECUTION_TYPE")), data=feature_data
            )
            preloop_client.insert_feature(insert_feature_data_request)
            sys.exit(0)

        return wrapper
