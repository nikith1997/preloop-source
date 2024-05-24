import ast
import builtins
import copy
import logging
import os

log = logging.getLogger("uvicorn")


class InfoCollector(ast.NodeVisitor):
    def __init__(self, node):
        self.node = node
        self.import_nodes = []
        self.import_names = set()
        self.libraries = set()
        self.class_and_function_definitions = {}
        self.defined_class_names = set()
        self.variable_types = {}

        self.visit(self.node)

    def visit_Import(self, node):
        self.import_nodes.append(node)
        for alias in node.names:
            self.libraries.add(alias.name.split(".")[0])
            self.import_names.add(alias.name if alias.asname is None else alias.asname)

    def visit_ImportFrom(self, node):
        self.import_nodes.append(node)
        self.libraries.add(node.module.split(".")[0])
        for alias in node.names:
            self.import_names.add(alias.name if alias.asname is None else alias.asname)

    def visit_FunctionDef(self, node):
        self.class_and_function_definitions[node.name] = node

    def visit_ClassDef(self, node):
        self.class_and_function_definitions[node.name] = node
        self.defined_class_names.add(node.name)

    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Tuple) and isinstance(node.value, ast.Tuple):
            for target, value in zip(node.targets[0].elts, node.value.elts):
                if isinstance(target, ast.Name) and isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                    self.variable_types[target.id] = value.func.id
        elif (
            isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
        ):
            self.variable_types[node.targets[0].id] = node.value.func.id


class VariableAnalyzer(ast.NodeVisitor):
    def __init__(self, node, script_info: InfoCollector):
        self.node = node
        self.script_info = script_info
        self.global_vars = set()
        self.temp_global_vars = set()
        self.node_class_name = None

        if isinstance(self.node, ast.ClassDef):
            self.node_class_name = self.node.name
        self.visit(self.node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        local_vars = set()
        if self.node_class_name:
            local_vars.add(self.node_class_name)
        for arg in node.args.posonlyargs:
            local_vars.add(arg.arg)
        for arg in node.args.args:
            local_vars.add(arg.arg)
        if node.args.vararg:
            local_vars.add(node.args.vararg.arg)
        if node.args.kwarg:
            local_vars.add(node.args.kwarg.arg)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, (ast.Tuple, ast.List)):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name):
                                local_vars.add(elt.id)
                    elif isinstance(target, ast.Name):
                        local_vars.add(target.id)
            elif isinstance(child, ast.AnnAssign):
                if isinstance(child.target, ast.Name):
                    local_vars.add(child.target.id)
            elif isinstance(child, ast.For):
                if isinstance(child.target, ast.Tuple):
                    for elt in child.target.elts:
                        if isinstance(elt, ast.Name):
                            local_vars.add(elt.id)
                elif isinstance(child.target, ast.Name):
                    local_vars.add(child.target.id)
        self.generic_visit(node)
        self.temp_global_vars = self.temp_global_vars - local_vars - self.script_info.import_names - set(dir(builtins))
        self.global_vars = self.global_vars.union(self.temp_global_vars)
        self.temp_global_vars.clear()

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, (ast.Load, ast.Store)):
            self.temp_global_vars.add(node.id)
        self.generic_visit(node)


class ScriptGenerator(ast.NodeTransformer):
    def __init__(self, training_script: str, s3_obj_prefix: str, predict_function_name: str):
        self.node = ast.parse(training_script)
        self.script_info = InfoCollector(self.node)
        self.predict_function_name = predict_function_name
        self.predict_function_inputs_and_types = {}
        self.inference_script = None
        self.global_vars_to_be_loaded_from_pickle = set()
        self.s3_obj_prefix = s3_obj_prefix
        self.loop_line_numbers = set()

        if self.predict_function_name not in self.script_info.class_and_function_definitions:
            raise ValueError(f"Predict function {self.predict_function_name} not found in the training script")
        self.generate_inference_script()
        self.visit(self.node)
        ast.fix_missing_locations(self.node)
        self.training_script = ast.unparse(self.node)
        self.collect_loop_line_numbers()

    def visit_FunctionDef(self, node: ast.Call):
        self.generic_visit(node)
        if node.name == self.predict_function_name:
            for arg in node.args.args:
                if type(arg.annotation) == ast.Name:
                    self.predict_function_inputs_and_types[arg.arg] = arg.annotation.id
                elif type(arg.annotation) == ast.Subscript:
                    if type(arg.annotation.slice) == ast.Tuple:
                        subscript = ""
                        for elt in arg.annotation.slice.elts:
                            subscript += f"[{elt.id}]"
                        self.predict_function_inputs_and_types[arg.arg] = f"{arg.annotation.value.id}{subscript}"
                    elif type(arg.annotation.slice) == ast.Name:
                        self.predict_function_inputs_and_types[
                            arg.arg
                        ] = f"{arg.annotation.value.id}[{arg.annotation.slice.id}]"
                    else:
                        self.predict_function_inputs_and_types[arg.arg] = "Unknown Type"
                else:
                    self.predict_function_inputs_and_types[arg.arg] = "Unknown Type"
            s3_upload_code = """
import boto3
import pickle
from io import BytesIO
import os
s3 = boto3.client('s3')
"""
            for var in self.global_vars_to_be_loaded_from_pickle:
                s3_upload_code += f"""
buffer = BytesIO()
pickle.dump({var}, buffer)
buffer.seek(0)
s3.upload_fileobj(buffer, 'preloop-ml-objects-{os.getenv('DEPLOY_ENVIRONMENT')}', f'{self.s3_obj_prefix}{{os.getenv("VERSION")}}/{var}.pkl')
"""
            s3_upload_nodes = ast.parse(s3_upload_code).body
            return [*s3_upload_nodes, node]
        return node

    def generate_inference_script(self):
        pickled_object_download_code = """
import boto3
import pickle
from io import BytesIO
import os
s3 = boto3.client('s3')
class CustomUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "training_script_module":
            module = "src.inference"
        return super().find_class(module, name)
    """
        functions_and_classes_to_be_defined = set()
        temp_stack = [self.predict_function_name]
        while len(temp_stack) > 0:
            def_name = temp_stack.pop()
            functions_and_classes_to_be_defined.add(def_name)
            node = self.script_info.class_and_function_definitions[def_name]
            variable_analyzer = VariableAnalyzer(node, self.script_info)
            for global_var in variable_analyzer.global_vars:
                if global_var in self.script_info.class_and_function_definitions:
                    temp_stack.append(global_var)
                else:
                    self.global_vars_to_be_loaded_from_pickle.add(global_var)
                    if (
                        global_var in self.script_info.variable_types
                        and self.script_info.variable_types[global_var] in self.script_info.defined_class_names
                    ):
                        temp_stack.append(self.script_info.variable_types[global_var])
        inference_code_node = ast.Module(body=[], type_ignores=[])
        inference_code_node.body.extend(self.script_info.import_nodes)
        class_and_function_definitions_dict = copy.deepcopy(self.script_info.class_and_function_definitions)
        for name, node in class_and_function_definitions_dict.items():
            if name in functions_and_classes_to_be_defined and name in self.script_info.defined_class_names:
                inference_code_node.body.append(node)
                functions_and_classes_to_be_defined.remove(name)
        for var in self.global_vars_to_be_loaded_from_pickle:
            pickled_object_download_code += f"""
buffer = BytesIO()
s3.download_fileobj('preloop-ml-objects-{os.getenv('DEPLOY_ENVIRONMENT')}', f'{self.s3_obj_prefix}{{os.getenv("VERSION")}}/{var}.pkl', buffer)
buffer.seek(0)
{var} = CustomUnpickler(buffer).load()
    """
        inference_code_node.body.append(ast.parse(pickled_object_download_code))
        for name, node in class_and_function_definitions_dict.items():
            if name in functions_and_classes_to_be_defined:
                inference_code_node.body.append(node)
        ast.fix_missing_locations(inference_code_node)
        self.inference_script = ast.unparse(inference_code_node)

    def collect_loop_line_numbers(self):
        node = ast.parse(self.training_script)
        for i, child in enumerate(ast.iter_child_nodes(node)):
            if isinstance(child, ast.For) or isinstance(child, ast.While):
                if i < len(node.body) - 1:
                    self.loop_line_numbers.update(range(child.lineno, node.body[i + 1].lineno))
                else:
                    last_line_no = 1
                    for final_node in ast.walk(child):
                        if hasattr(final_node, "lineno") and final_node.lineno > last_line_no:
                            last_line_no = final_node.lineno
                    self.loop_line_numbers.update(range(child.lineno, last_line_no + 1))
