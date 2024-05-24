"""
This class implements base functionality used to track model
metrics. Most metrics are derived from scikit-learn metrics,
but additional metrics can be implemented by
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
        pass
