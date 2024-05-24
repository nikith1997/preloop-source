import os
import sys
import types
from typing import Dict, List

import pandas as pd
from preloop.compiler.runtime.dependencies import snoop
from sklearn.base import BaseEstimator

# Path to the script you want to trace
script_path = sys.argv[1]

with open(script_path, "r") as file:
    script_content = file.read()

compiled_code = compile(script_content, script_path, "exec")

# Update the globals dictionary for exec
exec_globals = {
    "__file__": script_path,  # Set __file__ to the correct script path
    "__package__": None,
    "__doc__": None,
    "__builtins__": __builtins__,
}

training_script_module = types.ModuleType("training_script_module")
sys.modules["training_script_module"] = training_script_module

training_script_module.__dict__.update(exec_globals)

try:
    import torch

    tracking_list = [pd.DataFrame, BaseEstimator, torch.nn.Module]
except:
    tracking_list = [pd.DataFrame, BaseEstimator]

with snoop(
    depth=2,
    color=False,
    tracking_list=tracking_list,
    output_dir=os.getcwd() + "/",
    file_name="script_trace.pkl",
    script_path=script_path,
    mode="silent",
):
    # Pass the updated globals dictionary to exec
    exec(compiled_code, training_script_module.__dict__)
