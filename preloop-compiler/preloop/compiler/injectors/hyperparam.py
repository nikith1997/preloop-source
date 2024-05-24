import ast


class InfoCollector(ast.NodeVisitor):
    def __init__(self, node, target_line):
        self.node = node
        self.hyperparam_grid_line_number = None
        self.hyperparam_grid_var_name = None
        self.target_line = target_line

        self.visit(self.node)

    def visit_Call(self, node):
        # Check if the current node is at the target line number
        if hasattr(node, "lineno") and node.lineno == self.target_line:
            # Now, check if this is a call to GridSearchCV
            for keyword in node.keywords:
                if keyword.arg == "param_grid":
                    if isinstance(keyword.value, ast.Name):
                        self.hyperparam_grid_var_name = keyword.value.id
                        return  # Found the target, no need to continue
        # Continue traversal in case the target line hasn't been reached or for nested calls
        self.generic_visit(node)


class InjectHyperparams(ast.NodeTransformer):
    def __init__(self, training_script: str, target_line: int, new_grid: dict):
        self.node = ast.parse(training_script)
        self.hyperparam_dict_name = InfoCollector(self.node, target_line).hyperparam_grid_var_name
        self.new_grid = new_grid
        self.visit(self.node)
        ast.fix_missing_locations(self.node)
        self.training_script = ast.unparse(self.node)

    def visit_Assign(self, node):
        if any(target.id == self.hyperparam_dict_name for target in node.targets if isinstance(target, ast.Name)):
            new_value = ast.parse(self.new_grid)
            new_value = new_value.body[0].value
            node.value = new_value

        return node
