from typing import Any, List

import pandas as pd

from preloop.inception.models import Datasource


class datasources:
    def __init__(self, func) -> None:
        self.func = func

    def __call__(self, *args: Any, **kwargs: Any) -> List[Datasource]:
        datasources_to_be_created: List[Datasource] = self.func(*args, **kwargs)
        return datasources_to_be_created


class feature:
    def __init__(
        self,
        name: str,
        description: str,
        id_cols: List[str],
        feature_cols: List[str],
        existing_datasource_names: List[str] = None,
        target_cols: List[str] = None,
    ):
        pass

    def __call__(self, func) -> Any:
        def wrapper(*args, **kwargs):
            feature_data: pd.DataFrame = func(*args, **kwargs)
            return feature_data

        return wrapper
