import configparser
import sys
from typing import Annotated

import typer
from rich import print, print_json

from preloop.public_api_stubs import (
    CreateMLModelRequest,
    DeleteMLModelRequest,
    DeployMLModelRequest,
    ListHostedMLModelsRequest,
    ListMLModelsRequest,
    ListMLModelVersionsRequest,
    ListTrainingJobsRequest,
    PreloopClient,
    RetrainMLModelRequest,
    StopMLModelRequest,
)

config = configparser.ConfigParser()
preloop_client = PreloopClient()


def exception_handler(exception_type, exception, traceback):
    print(f"[bold red]{exception_type.__name__}:[/bold red] {exception}")


def callback():
    sys.excepthook = exception_handler


app = typer.Typer(pretty_exceptions_show_locals=False, callback=callback)


# @app.command()
# def list_datasources(datasource_id: Annotated[str, typer.Option()] = None):
#     """
#     List all datasources or a specific datasource if an ID is provided.
#     """
#     if datasource_id is None:
#         print_json(preloop_client.list_datasources().model_dump_json())
#     else:
#         print_json(
#             preloop_client.list_datasources(ListDatasourcesRequest(datasource_id=datasource_id)).model_dump_json()
#         )


# @app.command()
# def delete_datasource(datasource_id: Annotated[str, typer.Option()]):
#     """
#     Delete a specific datasource.
#     """
#     print_json(preloop_client.delete_datasource(
#         DeleteDatasourceRequest(datasource_id=datasource_id)).model_dump_json())


# @app.command()
# def modify_datasource(datasource_id: Annotated[str, typer.Option()], attributes: Annotated[str, typer.Option()]):
#     """
#     Modify a specific datasource.
#     """
#     print_json(
#         preloop_client.modify_datasource(
#             ModifyDatasourceRequest(
#                 fields=DatasourceIdentifierField(datasource_id=datasource_id),
#                 modfield=ModifiableDatasourceFields.model_validate_json(json_data=attributes),
#             )
#         ).model_dump_json()
#     )


# @app.command()
# def list_features(feature_id: Annotated[str, typer.Option()] = None):
#     """
#     List all features or a specific feature if an ID is provided.
#     """
#     if feature_id is None:
#         print_json(preloop_client.list_features().model_dump_json())
#     else:
#         print_json(preloop_client.list_features(ListFeaturesRequest(feature_id=feature_id)).model_dump_json())


# @app.command()
# def delete_feature(feature_id: Annotated[str, typer.Option()]):
#     """
#     Delete a specific feature.
#     """
#     print_json(preloop_client.delete_feature(DeleteFeatureRequest(feature_id=feature_id)).model_dump_json())


# @app.command()
# def modify_feature(feature_id: Annotated[str, typer.Option()], attributes: Annotated[str, typer.Option()]):
#     """
#     Modify a specific feature.
#     """
#     print_json(
#         preloop_client.modify_feature(
#             ModifyFeatureRequest(
#                 fields=FeatureIdentifierField(feature_id=feature_id),
#                 modfield=ModifiableFeatureFields.model_validate_json(json_data=attributes),
#             )
#         ).model_dump_json()
#     )


# @app.command()
# def get_feature(
#     feature_id: Annotated[str, typer.Option()],
#     file_path: Annotated[str, typer.Option(help="The feature data will be saved here")],
#     version: Annotated[int, typer.Option()] = None,
#     file_type: Annotated[GetFeatureFileType, typer.Option()] = GetFeatureFileType.CSV.value,
# ):
#     """
#     Get a specific feature and save it to a file.
#     """
#     df = preloop_client.get_feature(GetFeatureRequest(feature_id=feature_id, version=version))
#     if file_type == GetFeatureFileType.PARQUET:
#         df.to_parquet(file_path)
#     else:
#         df.to_csv(file_path)


# @app.command()
# def upload_feature_script(
#     file_path: Annotated[str, typer.Option()],
#     creation_method: Annotated[CreationMethod, typer.Option()],
#     scheduling_expression: Annotated[str, typer.Option()] = None,
#     versioning: Annotated[bool, typer.Option()] = False,
#     feature_drift_enabled: Annotated[bool, typer.Option()] = False,
# ):
#     """
#     Upload a feature script.
#     """
#     print_json(
#         preloop_client.upload_feature_script(
#             UploadFeatureScriptRequest(
#                 file_path=file_path,
#                 creation_method=creation_method,
#                 scheduling_expression=scheduling_expression,
#                 versioning=versioning,
#                 feature_drift_enabled=feature_drift_enabled,
#             )
#         ).model_dump_json()
#     )


# @app.command()
# def list_feature_executions(execution_id: Annotated[str, typer.Option()] = None):
#     """
#     List all feature executions or a specific execution if an ID is provided.
#     """
#     if execution_id is None:
#         print_json(preloop_client.list_feature_executions().model_dump_json())
#     else:
#         print_json(
#             preloop_client.list_feature_executions(
#                 ListFeatureExecutionsRequest(execution_id=execution_id)
#             ).model_dump_json()
#         )


# @app.command()
# def trigger_feature_execution(feature_id: Annotated[str, typer.Option()]):
#     """
#     Trigger a feature execution.
#     """
#     print_json(
#         preloop_client.trigger_feature_execution(
#             request=TriggerFeatureExecutionRequest(feature_id=feature_id)
#         ).model_dump_json()
#     )


# @app.command()
# def view_feature_drifts(feature_id: Annotated[str, typer.Option()]):
#     """
#     View feature drifts.
#     """
#     print_json(
#         preloop_client.view_feature_drifts(request=ViewFeatureDriftsRequest(feature_id=feature_id)).model_dump_json()
#     )


@app.command()
def list_ml_models(ml_model_id: Annotated[str, typer.Option()] = None):
    """
    List all ML models or a specific model if an ID is provided.
    """
    if ml_model_id is None:
        print_json(preloop_client.list_ml_models().model_dump_json())
    else:
        print_json(preloop_client.list_ml_models(ListMLModelsRequest(ml_model_id=ml_model_id)).model_dump_json())


@app.command()
def create_ml_model(
    ml_model_name: Annotated[str, typer.Option()],
    ml_model_description: Annotated[str, typer.Option()],
    training_script_path: Annotated[str, typer.Option()],
    predict_function_name: Annotated[str, typer.Option()] = "predict",
    require_api_key: Annotated[bool, typer.Option()] = True,
    schedule: Annotated[str, typer.Option()] = None,
    env_vars: Annotated[str, typer.Option()] = None,
):
    """
    Create a new ML model.
    """
    print_json(
        preloop_client.create_ml_model(
            CreateMLModelRequest(
                ml_model_name=ml_model_name,
                ml_model_description=ml_model_description,
                training_script_path=training_script_path,
                predict_function_name=predict_function_name,
                require_api_key=require_api_key,
                schedule=schedule,
                env_vars=env_vars,
            )
        ).model_dump_json()
    )


@app.command()
def retrain_ml_model(ml_model_id: Annotated[str, typer.Option()]):
    """
    Retrain an ML model.
    """
    print_json(preloop_client.retrain_ml_model(RetrainMLModelRequest(ml_model_id=ml_model_id)).model_dump_json())


@app.command()
def list_training_jobs(job_id: Annotated[str, typer.Option()] = None):
    """
    List all training jobs or a specific job if an ID is provided.
    """
    if job_id is None:
        print_json(preloop_client.list_training_jobs().model_dump_json())
    else:
        print_json(preloop_client.list_training_jobs(ListTrainingJobsRequest(job_id=job_id)).model_dump_json())


@app.command()
def list_hosted_ml_models(ml_model_id: Annotated[str, typer.Option()] = None):
    """
    List all hosted ML models for a given ML model.
    """
    if ml_model_id is None:
        print_json(preloop_client.list_hosted_ml_models().model_dump_json())
    else:
        print_json(
            preloop_client.list_hosted_ml_models(ListHostedMLModelsRequest(ml_model_id=ml_model_id)).model_dump_json()
        )


@app.command()
def deploy_ml_model(
    ml_model_id: Annotated[str, typer.Option()],
    version: Annotated[str, typer.Option()],
    require_api_key: Annotated[bool, typer.Option()] = True,
):
    """
    Deploy an ML model.
    """
    try:
        version = int(version)
    except ValueError:
        pass
    print_json(
        preloop_client.deploy_ml_model(
            DeployMLModelRequest(ml_model_id=ml_model_id, version=version, require_api_key=require_api_key)
        ).model_dump_json()
    )


@app.command()
def delete_ml_model(ml_model_id: Annotated[str, typer.Option()]):
    """
    Delete a specific ML model.
    """
    print_json(preloop_client.delete_ml_model(DeleteMLModelRequest(ml_model_id=ml_model_id)).model_dump_json())


@app.command()
def stop_ml_model(hosted_ml_model_id: Annotated[str, typer.Option()]):
    """
    Stop a specific ML model.
    """
    print_json(
        preloop_client.stop_ml_model(StopMLModelRequest(hosted_ml_model_id=hosted_ml_model_id)).model_dump_json()
    )


@app.command()
def list_ml_model_versions(ml_model_id: Annotated[str, typer.Option()]):
    """
    List all versions of a specific ML model.
    """
    print_json(
        preloop_client.list_ml_model_versions(ListMLModelVersionsRequest(ml_model_id=ml_model_id)).model_dump_json()
    )


if __name__ == "__main__":
    app()
