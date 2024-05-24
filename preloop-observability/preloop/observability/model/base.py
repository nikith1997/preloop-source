"""
This class implements base functionality used to track model 
metrics. Most metrics are derived from scikit-learn metrics,
but additional metrics can be implemented by 
"""
import os
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel
from sklearn import metrics

from preloop.compiler.runtime.dependencies import utils


# base class for all metrics
class ModelMetric(BaseModel):
    metric_name: str
    arguments: Optional[Dict[str, Any]] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    # if user defines their own metric, format should be as follows
    # def metric(self, y_true, y_pred)


class ModelMetricEvaluator(BaseModel):
    metric_list: List[ModelMetric]
    model: object = None

    def evaluate(self, *, x_test=None, y_test, y_pred=None):
        if self.model is None:
            for metric in self.metric_list:
                if not hasattr(metric, "metric"):
                    raise ValueError(
                        "A custom metric function needs to be supplied for each metric if no model is provided. Override the ModelMetric class to define a custom metric function"
                    )
            if y_pred is None:
                raise ValueError("Predictions must be supplied if no model is provided")
        else:
            model_type = utils.identify_model(self.model)  # pyline: disable=attribute-defined-outside-init
            if model_type is None:
                raise ValueError("Model type not recognized or supported")
            if model_type["package_name"] in ("scikit-learn", "xgboost"):
                if x_test is None:
                    raise ValueError("x_test must be supplied if a scikit-learn or xgboost model is provided")
                if y_pred is None:
                    y_pred = self.model.predict(x_test)  # pylint: disable=no-member
            elif model_type["package_name"] == "pytorch":
                for metric in self.metric_list:
                    if not hasattr(metric, "metric"):
                        raise ValueError(
                            "Pytorch models require custom metrics to be defined as a method on the metric object. Override the ModelMetric class to define a custom metric function"
                        )
                if y_pred is None:
                    raise ValueError("Predictions must be supplied if a pytorch model is provided")

        results = []
        for item in self.metric_list:
            if hasattr(item, "metric"):
                metric_value = item.metric(y_test, y_pred)
                item_to_add = {
                    "metric_name": item.metric_name,
                    "metric_value": metric_value,
                    "min_val": item.min_val,
                    "max_val": item.max_val,
                }
                results.append(item_to_add)

            else:
                metric_function = getattr(metrics, item.metric_name, None)

                if metric_function:
                    if item.arguments is not None:
                        metric_value = metric_function(y_test, y_pred, **item.arguments)

                    else:
                        metric_value = metric_function(y_test, y_pred)

                item_to_add = {
                    "metric_name": item.metric_name,
                    "metric_value": metric_value,
                    "min_val": item.min_val,
                    "max_val": item.max_val,
                }

                results.append(item_to_add)

        response = requests.post(
            url=f"{os.getenv('PRELOOP_API_ENDPOINT')}/api/ml-model/store-metrics",
            headers={
                "User-Agent": "PreloopClient/1.0",
                "key-id": os.getenv("KEY_ID"),
                "secret": os.getenv("SECRET"),
            },
            json={
                "ml_model_id": os.getenv("ML_MODEL_ID"),
                "version": os.getenv("VERSION"),
                "metrics": results,
            },
        )
        response.raise_for_status()

        return results
