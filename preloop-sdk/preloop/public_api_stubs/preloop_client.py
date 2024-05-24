import json
import os
from typing import Optional

import requests

from preloop.public_api_stubs.api_paths import MLModelAPIPaths
from preloop.public_api_stubs.exceptions import PreloopError
from preloop.public_api_stubs.models import (
    CreateMLModelRequest,
    CreateMLModelResult,
    DeleteMLModelRequest,
    DeleteMLModelResult,
    DeployMLModelRequest,
    DeployMLModelResult,
    ListHostedMLModelsRequest,
    ListHostedMLModelsResult,
    ListMLModelsRequest,
    ListMLModelsResult,
    ListMLModelVersionsRequest,
    ListMLModelVersionsResult,
    ListTrainingJobsRequest,
    ListTrainingJobsResult,
    RetrainMLModelRequest,
    RetrainMLModelResult,
    StopMLModelRequest,
    StopMLModelResult,
)


class PreloopClient:
    def __init__(
        self,
        endpoint_url: str = "https://api.preloop.com",
        key_id: str = os.getenv("PRELOOP_KEY_ID"),
        secret: str = os.getenv("PRELOOP_SECRET"),
    ) -> None:
        """
        Initialize a new instance of the PreloopClient class.

        Args:
            endpoint_url (str, optional): The endpoint URL of the Preloop API. Defaults to "api.preloop.com".
            key_id (str, optional): The key ID for the Preloop API. Defaults to the value of the "PRELOOP_KEY_ID" environment variable.
            secret (str, optional): The secret for the Preloop API. Defaults to the value of the "PRELOOP_SECRET" environment variable.
        """
        self.endpoint_url = endpoint_url
        self.headers = {
            "User-Agent": "PreloopClient/1.0",
            "key-id": key_id,
            "secret": secret,
        }

    # def list_datasources(self, request: Optional[ListDatasourcesRequest] = None) -> ListDatasourcesResult:
    #     """
    #     List all datasources. If a request is provided, the request is used to filter the datasources.

    #     Args:
    #         request (ListDatasourcesRequest, optional): The request object for listing datasources. If None, a default request is made.

    #     Returns:
    #         List[ListDatasourcesResult]: A list of datasources.

    #     Raises:
    #         PreloopError: If an HTTP error occurs.
    #     """
    #     try:
    #         if request is None:
    #             response = requests.post(
    #                 url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_LIST.value}", headers=self.headers
    #             )
    #         else:
    #             response = requests.post(
    #                 url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_LIST.value}",
    #                 headers=self.headers,
    #                 json=json.loads(request.model_dump_json()),
    #             )
    #         response.raise_for_status()
    #     except requests.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     response = ListDatasourcesResult.model_validate_json(json_data=response.text)
    #     return response

    # def delete_datasource(self, request: DeleteDatasourceRequest) -> DeleteDatasourceResult:
    #     """
    #     Delete a specific datasource.

    #     Args:
    #         request (DeleteDatasourceRequest): The request object for deleting a datasource.

    #     Returns:
    #         DeleteDatasourceResult: The result of the delete operation.

    #     Raises:
    #         PreloopError: If an HTTP error occurs.
    #     """
    #     try:
    #         response = requests.post(
    #             url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_DELETE.value}",
    #             headers=self.headers,
    #             json=json.loads(request.model_dump_json()),
    #         )
    #         response.raise_for_status()
    #     except requests.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     response = DeleteDatasourceResult.model_validate_json(json_data=response.text)
    #     return response

    # def modify_datasource(self, request: ModifyDatasourceRequest) -> ModifyDatasourceResult:
    #     """
    #     Modify a specific datasource.

    #     Args:
    #         request (ModifyDatasourceRequest): The request object for modifying a datasource.

    #     Returns:
    #         ModifyDatasourceResult: The result of the modify operation.

    #     Raises:
    #         PreloopError: If an HTTP error occurs.
    #     """
    #     try:
    #         response = requests.post(
    #             url=f"{self.endpoint_url}{DatasourceAPIPaths.DATASOURCE_MODIFY.value}",
    #             headers=self.headers,
    #             json=json.loads(request.model_dump_json()),
    #         )
    #         response.raise_for_status()
    #     except requests.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     response = ModifyDatasourceResult.model_validate_json(json_data=response.text)
    #     return response

    # def list_features(self, request: Optional[ListFeaturesRequest] = None) -> ListFeaturesResult:
    #     """
    #     List all features. If a request is provided, the request is used to filter the features.

    #     Args:
    #         request (ListFeaturesRequest, optional): The request object for listing features. If None, a default request is made.

    #     Returns:
    #         ListFeaturesResult: A list of features.

    #     Raises:
    #         PreloopError: If an HTTP error occurs.
    #     """
    #     try:
    #         if request is None:
    #             response = requests.post(
    #                 url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_LIST.value}", headers=self.headers
    #             )
    #         else:
    #             response = requests.post(
    #                 url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_LIST.value}",
    #                 headers=self.headers,
    #                 json=json.loads(request.model_dump_json()),
    #             )
    #         response.raise_for_status()
    #     except requests.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     response = ListFeaturesResult.model_validate_json(json_data=response.text)
    #     return response

    # def delete_feature(self, request: DeleteFeatureRequest) -> DeleteFeatureResult:
    #     """
    #     Delete a specific feature.

    #     Args:
    #         request (DeleteFeatureRequest): The request object for deleting a feature.

    #     Returns:
    #         DeleteFeatureResult: The result of the delete operation.

    #     Raises:
    #         PreloopError: If an HTTP error occurs.
    #     """
    #     try:
    #         response = requests.post(
    #             url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_DELETE.value}",
    #             headers=self.headers,
    #             json=json.loads(request.model_dump_json()),
    #         )
    #         response.raise_for_status()
    #     except requests.exceptions.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     response = DeleteFeatureResult.model_validate_json(json_data=response.text)
    #     return response

    # def modify_feature(self, request: ModifyFeatureRequest) -> ModifyFeatureResult:
    #     """
    #     Modify a specific feature.

    #     Args:
    #         request (ModifyFeatureRequest): The request object for modifying a feature.

    #     Returns:
    #         ModifyFeatureResult: The result of the modify operation.

    #     Raises:
    #         PreloopError: If an HTTP error occurs.
    #     """
    #     try:
    #         response = requests.post(
    #             url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_MODIFY.value}",
    #             headers=self.headers,
    #             json=json.loads(request.model_dump_json()),
    #         )
    #         response.raise_for_status()
    #     except requests.exceptions.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     response = ModifyFeatureResult.model_validate_json(json_data=response.text)
    #     return response

    # def get_feature(self, request: GetFeatureRequest):
    #     """
    #     Get a specific feature.

    #     Args:
    #         request (GetFeatureRequest): The request object for getting a feature.

    #     Returns:
    #         DataFrame: A DataFrame containing the feature data.

    #     Raises:
    #         PreloopError: If an HTTP error occurs.
    #     """
    #     try:
    #         response = requests.post(
    #             url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_GET.value}",
    #             headers=self.headers,
    #             json=json.loads(request.model_dump_json()),
    #             stream=True,
    #         )
    #         response.raise_for_status()
    #     except requests.exceptions.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     buffer = io.BytesIO()
    #     for chunk in response.iter_content():
    #         buffer.write(chunk)
    #     buffer.seek(0)
    #     df = pd.read_parquet(buffer)
    #     return df

    # def upload_feature_script(self, request: UploadFeatureScriptRequest) -> UploadFeatureScriptResult:
    #     """
    #     Upload a feature script.

    #     Args:
    #         request (UploadFeatureScriptRequest): The request object for uploading a feature script.

    #     Returns:
    #         UploadFeatureScriptResult: The result of the upload operation.

    #     Raises:
    #         PreloopError: If an HTTP error occurs or if there's an issue with the file.
    #     """
    #     try:
    #         with open(request.file_path, "rb") as script:
    #             response = requests.post(
    #                 url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_UPLOAD_SCRIPT.value}",
    #                 headers=self.headers,
    #                 data=json.loads(request.model_dump_json(exclude=["file_path"])),
    #                 files={"script": script},
    #             )
    #             response.raise_for_status()
    #     except requests.exceptions.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     except Exception as e:
    #         raise PreloopError(message=str(e)) from None
    #     response = UploadFeatureScriptResult.model_validate_json(json_data=response.text)
    #     return response

    # def list_feature_executions(
    #     self, request: Optional[ListFeatureExecutionsRequest] = None
    # ) -> ListFeatureExecutionsResult:
    #     """
    #     List all feature executions. If a request is provided, the request is used to filter the executions.

    #     Args:
    #         request (ListExecutionsRequest, optional): The request object for listing executions. If None, a default request is made.

    #     Returns:
    #         ListExecutionsResult: A list of executions.

    #     Raises:
    #         PreloopError: If an HTTP error occurs.
    #     """
    #     try:
    #         if request is None:
    #             response = requests.post(
    #                 url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_LIST_EXECUTIONS.value}", headers=self.headers
    #             )
    #         else:
    #             response = requests.post(
    #                 url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_LIST_EXECUTIONS.value}",
    #                 headers=self.headers,
    #                 json=json.loads(request.model_dump_json()),
    #             )
    #         response.raise_for_status()
    #     except requests.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     response = ListFeatureExecutionsResult.model_validate_json(json_data=response.text)
    #     return response

    # def trigger_feature_execution(self, request: TriggerFeatureExecutionRequest) -> TriggerFeatureExecutionResult:
    #     """
    #     Trigger a manual feature execution.

    #     Args:
    #         request (TriggerFeatureExecutionRequest): The request object for triggering a feature execution.

    #     Returns:
    #         TriggerFeatureExecutionResult: The result of the trigger operation.

    #     Raises:
    #         PreloopError: If an HTTP error occurs.
    #     """
    #     try:
    #         response = requests.post(
    #             url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_TRIGGER_EXECUTION.value}",
    #             headers=self.headers,
    #             json=json.loads(request.model_dump_json()),
    #         )
    #         response.raise_for_status()
    #     except requests.exceptions.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     response = TriggerFeatureExecutionResult.model_validate_json(json_data=response.text)
    #     return response

    # def view_feature_drifts(self, request: ViewFeatureDriftsRequest) -> ViewFeatureDriftsResponse:
    #     """
    #     View feature drift metrics

    #     Args:
    #         request (ViewFeatureDriftsRequest): The request object for viewing feature drifts.

    #     Returns:
    #         ViewFeatureDriftsResponse: The result of the view operation.

    #     Raises:
    #         PreloopError: If an HTTP error occurs.
    #     """
    #     try:
    #         response = requests.post(
    #             url=f"{self.endpoint_url}{FeatureAPIPaths.FEATURE_VIEW_DRIFTS.value}",
    #             headers=self.headers,
    #             json=json.loads(request.model_dump_json()),
    #         )
    #         response.raise_for_status()
    #     except requests.exceptions.HTTPError as http_error:
    #         raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
    #     response = ViewFeatureDriftsResponse.model_validate_json(json_data=response.text)
    #     return response

    def list_ml_models(self, request: Optional[ListMLModelsRequest] = None) -> ListMLModelsResult:
        """
        List all ML models. If a request is provided, the request is used to filter the ML models.

        Args:
            request (ListMLModelsRequest, optional): The request object for listing ML models. If None, a default request is made.

        Returns:
            ListMLModelsResult: A list of ML models.

        Raises:
            PreloopError: If an HTTP error occurs.
        """
        try:
            if request is None:
                response = requests.post(
                    url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_LIST.value}", headers=self.headers
                )
            else:
                response = requests.post(
                    url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_LIST.value}",
                    headers=self.headers,
                    json=json.loads(request.model_dump_json()),
                )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = ListMLModelsResult.model_validate_json(json_data=response.text)
        return response

    def create_ml_model(self, request: CreateMLModelRequest) -> CreateMLModelResult:
        """
        Create a new ML model.

        Args:
            request (CreateMLModelRequest): The request object for creating a new ML model.

        Returns:
            MLModelGenericResponse: The result of the create operation.

        Raises:
            PreloopError: If an HTTP error occurs.
        """
        try:
            with open(request.training_script_path, "rb") as script:
                response = requests.post(
                    url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_CREATE.value}",
                    headers=self.headers,
                    data=json.loads(request.model_dump_json(exclude=["training_script_path"])),
                    files={"training_script": script},
                )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = CreateMLModelResult.model_validate_json(json_data=response.text)
        return response

    def retrain_ml_model(self, request: RetrainMLModelRequest) -> RetrainMLModelResult:
        """
        Retrain an ML model.

        Args:
            request (RetrainMLModelRequest): The request object for retraining an ML model.

        Returns:
            MLModelGenericResponse: The result of the retrain operation.

        Raises:
            PreloopError: If an HTTP error occurs.
        """
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_RETRAIN.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = RetrainMLModelResult.model_validate_json(json_data=response.text)
        return response

    def list_training_jobs(self, request: Optional[ListTrainingJobsRequest] = None) -> ListTrainingJobsResult:
        """
        List all training jobs.

        Args:
            request (ListTrainingJobsRequest): The request object for listing training jobs.

        Returns:
            ListTrainingJobsResult: A list of training jobs.

        Raises:
            PreloopError: If an HTTP error occurs.
        """
        try:
            if request is None:
                response = requests.post(
                    url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_LIST_TRAINING_JOBS.value}", headers=self.headers
                )
            else:
                response = requests.post(
                    url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_LIST_TRAINING_JOBS.value}",
                    headers=self.headers,
                    json=json.loads(request.model_dump_json()),
                )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = ListTrainingJobsResult.model_validate_json(json_data=response.text)
        return response

    def list_hosted_ml_models(self, request: Optional[ListHostedMLModelsRequest] = None) -> ListHostedMLModelsResult:
        """
        List all hosted ML models.

        Args:
            request (ListHostedMLModelsRequest): The request object for listing hosted ML models.

        Returns:
            ListHostedMLModelsResult: A list of hosted ML models.

        Raises:
            PreloopError: If an HTTP error occurs.
        """
        try:
            if request is None:
                response = requests.post(
                    url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_LIST_HOSTED_MODELS.value}", headers=self.headers
                )
            else:
                response = requests.post(
                    url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_LIST_HOSTED_MODELS.value}",
                    headers=self.headers,
                    json=json.loads(request.model_dump_json()),
                )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = ListHostedMLModelsResult.model_validate_json(json_data=response.text)
        return response

    def deploy_ml_model(self, request: DeployMLModelRequest) -> DeployMLModelResult:
        """
        Deploy an ML model.

        Args:
            request (DeployMLModelRequest): The request object for deploying an ML model.

        Returns:
            DeployMLModelResult: The result of the deploy operation.

        Raises:
            PreloopError: If an HTTP error occurs.
        """
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_DEPLOY.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = DeployMLModelResult.model_validate_json(json_data=response.text)
        return response

    def delete_ml_model(self, request: DeleteMLModelRequest) -> DeleteMLModelResult:
        """
        Delete an ML model.

        Args:
            request (DeleteMLModelRequest): The request object for deleting an ML model.

        Returns:
            DeleteMLModelResult: The result of the delete operation.

        Raises:
            PreloopError: If an HTTP error occurs.
        """
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_DELETE.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = DeleteMLModelResult.model_validate_json(json_data=response.text)
        return response

    def stop_ml_model(self, request: StopMLModelRequest) -> StopMLModelResult:
        """
        Stop an ML model.

        Args:
            request (StopMLModelRequest): The request object for stopping an ML model.

        Returns:
            StopMLModelResult: The result of the stop operation.

        Raises:
            PreloopError: If an HTTP error occurs.
        """
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_STOP.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = StopMLModelResult.model_validate_json(json_data=response.text)
        return response

    def list_ml_model_versions(self, request: ListMLModelVersionsRequest) -> ListMLModelVersionsResult:
        """
        List all versions of an ML model.

        Args:
            request (ListMLModelVersionsRequest): The request object for listing ML model versions.

        Returns:
            ListMLModelVersionsResult: A list of ML model versions.

        Raises:
            PreloopError: If an HTTP error occurs.
        """
        try:
            response = requests.post(
                url=f"{self.endpoint_url}{MLModelAPIPaths.ML_MODEL_LIST_VERSIONS.value}",
                headers=self.headers,
                json=json.loads(request.model_dump_json()),
            )
            response.raise_for_status()
        except requests.HTTPError as http_error:
            raise PreloopError(message=json.loads(http_error.response.text)["detail"]) from None
        response = ListMLModelVersionsResult.model_validate_json(json_data=response.text)
        return response
