import json
import logging
import os
import pickle

import boto3
import numpy as np
import requests
import simplejson

log = logging.getLogger(__name__)


def default(obj):
    if type(obj).__module__ == np.__name__:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj.item()


sfn_client = boto3.client("stepfunctions", region_name="us-east-1")
script_exit_code = int(os.getenv("SCRIPT_EXIT_CODE"))
task_token = os.getenv("TASK_TOKEN")
ml_model_training = os.getenv("ML_MODEL_TRAINING")
ml_model_retraining = os.getenv("ML_MODEL_RETRAINING")
if script_exit_code == 0:
    if ml_model_training:
        try:
            model = None
            file_exists = os.path.exists("script_trace.pkl")
            if file_exists:
                with open("script_trace.pkl", "rb") as file:
                    script_trace = pickle.load(file)
                for variable in script_trace:
                    if script_trace[variable]["variable_category"] == "model":
                        model = script_trace[variable]
                        break
                if model:
                    response = requests.post(
                        url=f"{os.getenv('PRELOOP_API_ENDPOINT')}/api/ml-model/store-info",
                        headers={
                            "User-Agent": "PreloopClient/1.0",
                            "key-id": os.getenv("KEY_ID"),
                            "secret": os.getenv("SECRET"),
                        },
                        json={
                            "ml_model_id": os.getenv("ML_MODEL_ID"),
                            "ml_model_package": model["package_name"],
                            "ml_model_type": model["model_type"],
                            "prediction_type": model["prediction_type"],
                            "ml_model_data_flow": simplejson.dumps(script_trace, ignore_nan=True, default=default),
                        },
                    )
                else:
                    response = requests.post(
                        url=f"{os.getenv('PRELOOP_API_ENDPOINT')}/api/ml-model/store-info",
                        headers={
                            "User-Agent": "PreloopClient/1.0",
                            "key-id": os.getenv("KEY_ID"),
                            "secret": os.getenv("SECRET"),
                        },
                        json={
                            "ml_model_id": os.getenv("ML_MODEL_ID"),
                            "ml_model_package": None,
                            "ml_model_type": None,
                            "prediction_type": None,
                            "ml_model_data_flow": simplejson.dumps(script_trace, ignore_nan=True, default=default),
                        },
                    )
        except Exception as e:
            sfn_client.send_task_failure(taskToken=task_token, error="ScriptExecutionFailed", cause=str(e))
            raise e
    output_message = {
        "message": "Success",
        "detail": "The script executed successfully",
    }
    sfn_client.send_task_success(taskToken=task_token, output=json.dumps(output_message))
else:
    error_message = "The feature script failed during execution"
    with open("error.txt", "r") as f:
        for line in f:
            pass
        error_line = line
    error_message = error_line.strip()
    sfn_client.send_task_failure(taskToken=task_token, error="ScriptExecutionFailed", cause=error_message)
