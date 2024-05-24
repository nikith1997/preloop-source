# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.

import abc
import ast
import re

try:
    import torch.nn

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

import sys

import pandas as pd
import xgboost
from sklearn.base import ClassifierMixin, RegressorMixin
from sklearn.model_selection import GridSearchCV, ParameterGrid, ParameterSampler, RandomizedSearchCV

from .pycompat import ABC, collections_abc, string_types


def _check_methods(C, *methods):
    mro = C.__mro__
    for method in methods:
        for B in mro:
            if method in B.__dict__:
                if B.__dict__[method] is None:
                    return NotImplemented
                break
        else:
            return NotImplemented
    return True


class WritableStream(ABC):
    @abc.abstractmethod
    def write(self, s):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is WritableStream:
            return _check_methods(C, "write")
        return NotImplemented


file_reading_errors = (IOError, OSError, ValueError)  # IronPython weirdness.


def shitcode(s):
    return "".join((c if (0 < ord(c) < 256) else "?") for c in s)


def get_repr_function(item, custom_repr):
    for condition, action in custom_repr:
        if isinstance(condition, type):
            condition = lambda x, y=condition: isinstance(x, y)
        if condition(item):
            return action
    return repr


DEFAULT_REPR_RE = re.compile(r" at 0x[a-f0-9A-F]{4,}")


def normalize_repr(item_repr):
    """Remove memory address (0x...) from a default python repr"""
    return DEFAULT_REPR_RE.sub("", item_repr)


def get_shortish_repr(item, custom_repr=(), max_length=None, normalize=False):
    repr_function = get_repr_function(item, custom_repr)
    try:
        r = repr_function(item)
    except Exception:
        r = "REPR FAILED"
    r = r.replace("\r", "").replace("\n", "")
    if normalize:
        r = normalize_repr(r)
    if max_length:
        r = truncate(r, max_length)
    return r


def truncate(string, max_length):
    if (max_length is None) or (len(string) <= max_length):
        return string
    else:
        left = (max_length - 3) // 2
        right = max_length - 3 - left
        return "{}...{}".format(string[:left], string[-right:])


def ensure_tuple(x):
    if isinstance(x, collections_abc.Iterable) and not isinstance(x, string_types):
        return tuple(x)
    else:
        return (x,)


def find_ast_node_at_lineno(ast_rep, target_line):
    """
    Recursively search for an AST node that starts at the target_line.

    :param ast_node: The AST node to search in.
    :param target_line: The line number to find.
    :return: The first AST node found that starts at the target_line, or None if not found.
    """
    # The `lineno` attribute exists on nodes that correspond to actual lines in the source.
    # Not all AST node types have this attribute (e.g., `ast.Module`).
    if hasattr(ast_rep, "lineno") and ast_rep.lineno == target_line:
        return ast_rep

    # Recursively search through child nodes
    for child in ast.iter_child_nodes(ast_rep):
        result = find_ast_node_at_lineno(child, target_line)
        if result is not None:
            return result

    # If no matching node is found in this branch, return None
    return None


class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self, node):
        self.result = {
            "variable_changed_or_assigned": "",
            "other_variables": set(),  # Use a set to avoid duplicates
            "code": "",
        }
        # Start visiting from the provided node if it's relevant
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.Expr)):
            self.visit(node)
        else:
            self.result = {}  # Return an empty dict for non-relevant nodes

    def visit_Assign(self, node):
        self.generic_visit(node)  # Visit right-hand side first
        self.result["variable_changed_or_assigned"] = self.extract_id(node.targets[0])
        self.result["code"] = ast.unparse(node.value)

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        self.result["variable_changed_or_assigned"] = self.extract_id(node.target)
        self.result["code"] = ast.unparse(node)

    def visit_Expr(self, node):
        # Only process if it's a call (potential modification)
        if isinstance(node.value, ast.Call):
            self.visit_Call(node.value)
        else:
            self.result = {}  # Clear result if it's not a call

    def visit_Call(self, node):
        func_name = self.extract_id(node.func)
        if hasattr(node.func, "value"):
            self.result["variable_changed_or_assigned"] = self.extract_id(node.func.value)
        self.result["other_variables"].add(func_name)
        self.result["code"] = ast.unparse(node)
        self.generic_visit(node)

    def extract_id(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self.extract_id(node.value)
        elif isinstance(node, (ast.Call, ast.Subscript)):
            return ast.unparse(node)
        return ""

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.result["other_variables"].add(node.id)

    def finalize_result(self):
        if self.result:
            self.result["other_variables"] = list(self.result["other_variables"])


def analyze_node(node):
    analyzer = CodeAnalyzer(node)
    analyzer.finalize_result()
    return analyzer.result


def check_torch_model(model):
    if TORCH_AVAILABLE and isinstance(model, torch.nn.Module):
        return {"package_name": "pytorch", "model_type": None, "prediction_type": None}
    return None


def check_sklearn_model(model):
    if isinstance(model, ClassifierMixin):
        return {
            "package_name": "scikit-learn",
            "model_type": str(model.__class__.__name__),
            "prediction_type": "classification",
        }

    elif isinstance(model, RegressorMixin):
        return {
            "package_name": "scikit-learn",
            "model_type": str(model.__class__.__name__),
            "prediction_type": "regression",
        }

    return None


def check_xgboost_model(model):
    if isinstance(model, xgboost.XGBClassifier):
        return {"package_name": "xgboost", "model_type": "XGBClassifier", "prediction_type": "classification"}
    elif isinstance(model, xgboost.XGBRegressor):
        return {"package_name": "xgboost", "model_type": "XGBRegressor", "prediction_type": "regression"}
    return None


def identify_model(model):
    torch_result = check_torch_model(model)
    if torch_result:
        # Additional logic might be required to distinguish between classification and regression for PyTorch models
        return torch_result

    sklearn_result = check_sklearn_model(model)
    if sklearn_result:
        xgboost_result = check_xgboost_model(model)
        if xgboost_result:
            return xgboost_result
        return sklearn_result

    return None


def check_data_type(object_var):
    if isinstance(object_var, pd.DataFrame):
        return {"package_name": "pandas", "object_type": "DataFrame"}

    else:
        None


def check_cv(object_var):
    """
    This function is able to look at model_selection objects and identify
    whether they have been fitted yet. If they have, then the model is saved,
    along with the best values of hyperparameters. If not, then it continues
    execution.
    """
    if isinstance(object_var, GridSearchCV):
        if all(hasattr(object_var, attr) for attr in ["cv_results_", "best_estimator_", "best_params_", "param_grid"]):
            return {
                "hyperparam_search_type": "Grid Search CV",
                "details": {
                    "param_grid": object_var.param_grid,
                    "cv_results_": object_var.cv_results_,
                    "best_params": object_var.best_params_,
                    "model_params": object_var.best_estimator_.get_params(),
                },
            }

        return {"hyperparam_search_type": "Grid Search CV", "state": "partially_initialized"}

    return None
