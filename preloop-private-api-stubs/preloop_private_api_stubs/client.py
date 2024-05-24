import io
import json
import os
from typing import Optional

import pandas as pd
import requests

from .api_paths import DatasourceAPIPaths, FeatureAPIPaths
from .exceptions import PreloopError
from .models import (
    CreateDatasourceRequest,
    CreateDatasourceResult,
    CreateFeatureRequest,
    CreateFeatureResult,
    DeleteDatasourceRequest,
    DeleteDatasourceResult,
    DeleteFeatureRequest,
    DeleteFeatureResult,
    ExperimentalCreateFeatureRequest,
    ExperimentalCreateFeatureResult,
    ExperimentalGetFeatureRequest,
    GetDatasourceIdRequest,
    GetDatasourceIdResult,
    GetDatasourceRequest,
    GetFeatureIdRequest,
    GetFeatureIdResult,
    GetFeatureRequest,
    InsertFeatureRequest,
    InsertFeatureResult,
    ListDatasourcesRequest,
    ListDatasourcesResult,
    ListFeaturesRequest,
    ListFeaturesResult,
    ModifyDatasourceRequest,
    ModifyDatasourceResult,
    ModifyFeatureRequest,
    ModifyFeatureResult,
    ScheduledFeatureExecutionRequest,
    ScheduledFeatureExecutionResult,
    StoreFeatureDriftRequest,
    StoreFeatureDriftResult,
)


class PreloopPrivateClient:
    def __init__(
        self,
        endpoint_url: str = os.getenv("PRELOOP_API_ENDPOINT"),
        key_id: str = os.getenv("KEY_ID"),
        secret: str = os.getenv("SECRET"),
    ) -> None:
        self.endpoint_url = endpoint_url
        self.headers = {
            "User-Agent": "PreloopPrivateClient/1.0",
            "key-id": key_id,
            "secret": secret,
        }

    # Datasource methods
    def list_datasources(self, request: Optional[ListDatasourcesRequest] = None) -> ListDatasourcesResult:
        try:
            if request is None:
                response = requests.post(
                    url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_LIST.value}", headers=self.headers
                )
            else:
                response = requests.post(
                    url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_LIST.value}",
                    headers=self.headers,
                    json=json.loads(request.model_dump_json()),
                )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = ListDatasourcesResult.model_validate_json(json_data=response.text)
        return response

    def create_datasource(self, request: CreateDatasourceRequest) -> CreateDatasourceResult:
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_CREATE.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = CreateDatasourceResult.model_validate_json(json_data=response.text)
        return response

    def delete_datasource(self, request: DeleteDatasourceRequest) -> DeleteDatasourceResult:
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_DELETE.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = DeleteDatasourceResult.model_validate_json(json_data=response.text)
        return response

    def modify_datasource(self, request: ModifyDatasourceRequest) -> ModifyDatasourceResult:
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_MODIFY.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = ModifyDatasourceResult.model_validate_json(json_data=response.text)
        return response

    def get_datasource(self, request: GetDatasourceRequest):
        try:
            response = requests.get(
                url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_GET.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
                stream=True,
            )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        buffer = io.BytesIO()
        for chunk in response.iter_content():
            buffer.write(chunk)
        buffer.seek(0)
        df = pd.read_parquet(buffer)
        return df

    def get_datasource_id(self, request: GetDatasourceIdRequest) -> GetDatasourceIdResult:
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_GET_ID.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = GetDatasourceIdResult.model_validate_json(json_data=response.text)
        return response

    # Feature methods
    def list_features(self, request: Optional[ListFeaturesRequest] = None) -> ListFeaturesResult:
        try:
            if request is None:
                response = requests.post(
                    url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_LIST.value}", headers=self.headers
                )
                response.raise_for_status()
            else:
                response = requests.post(
                    url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_LIST.value}",
                    headers=self.headers,
                    json=json.loads(request.model_dump_json()),
                )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = ListFeaturesResult.model_validate_json(json_data=response.text)
        return response

    def create_feature(self, request: CreateFeatureRequest) -> CreateFeatureResult:
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_CREATE.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = CreateFeatureResult.model_validate_json(json_data=response.text)
        return response

    def delete_feature(self, request: DeleteFeatureRequest) -> DeleteFeatureResult:
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_DELETE.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = DeleteFeatureResult.model_validate_json(json_data=response.text)
        return response

    def modify_feature(self, request: ModifyFeatureRequest) -> ModifyFeatureResult:
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_MODIFY.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = ModifyFeatureResult.model_validate_json(json_data=response.text)
        return response

    def insert_feature(self, request: InsertFeatureRequest):
        bytes_obj = io.BytesIO()
        df: pd.DataFrame = request.data
        df.to_parquet(bytes_obj)
        bytes_obj.seek(0)
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_INSERT.value}",
                headers=self.headers,
                data=request.model_dump(exclude=["data"]),
                files={"data": bytes_obj},
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = InsertFeatureResult.model_validate_json(json_data=response.text)
        return response

    def get_feature(self, request: GetFeatureRequest):
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_GET.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
                stream=True,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        buffer = io.BytesIO()
        for chunk in response.iter_content():
            buffer.write(chunk)
        buffer.seek(0)
        df = pd.read_parquet(buffer)
        return df

    def experimental_create_feature(self, request: ExperimentalCreateFeatureRequest) -> ExperimentalCreateFeatureResult:
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_EXPERIMENTAL_CREATE.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = ExperimentalCreateFeatureResult.model_validate_json(json_data=response.text)
        return response

    def experimental_get_feature(self, request: ExperimentalGetFeatureRequest):
        try:
            response = requests.get(
                url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_EXPERIMENTAL_GET.value}",
                headers=self.headers,
                data=request.model_dump(),
                stream=True,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        try:
            buffer = io.BytesIO()
            for chunk in response.iter_content():
                buffer.write(chunk)
            buffer.seek(0)
            df = pd.read_parquet(buffer)
        except Exception as e:
            raise PreloopError(message=str(e)) from None
        return df

    def get_feature_id(self, request: GetFeatureIdRequest):
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_GET_ID.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = GetFeatureIdResult.model_validate_json(json_data=response.text)
        return response

    def scheduled_feature_execution(self, request: ScheduledFeatureExecutionRequest) -> ScheduledFeatureExecutionResult:
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_SCHEDULED_EXECUTION.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = ScheduledFeatureExecutionResult.model_validate_json(json_data=response.text)
        return response

    def store_feature_drift(self, request: StoreFeatureDriftRequest) -> StoreFeatureDriftResult:
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_STORE_DRIFT.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = StoreFeatureDriftResult.model_validate_json(json_data=response.text)
        return response
