import ast
import os
import tempfile
from bandit.core import config as b_config
from bandit.core import manager as b_manager

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket", "pty", "shlex", "importlib", "ctypes"
}
FORBIDDEN_BUILTINS = {"eval", "exec"}

def validate_python_tool_code(code: str) -> None:
    """
    Parses Python code using the AST module and runs Bandit static analysis to enforce:
    1. The code is syntactically valid.
    2. No forbidden modules (os, sys, subprocess, socket, pty, shlex, importlib, ctypes) are imported.
    3. No forbidden built-ins (eval, exec) are referenced/called.
    4. Bandit static analysis returns zero Medium/High severity findings.
    5. At least one function definition is decorated with @tool.
    
    Raises ValueError if any security or boilerplate validation fails.
    """
    # 1. AST Validation
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in Python script: {e.msg} on line {e.lineno}")

    has_tool_decorator = False
    
    for node in ast.walk(tree):
        # Check standard imports (e.g. import os)
        if isinstance(node, ast.Import):
            for alias in node.names:
                base_module = alias.name.split('.')[0]
                if base_module in FORBIDDEN_MODULES:
                    raise ValueError(f"Security Check Failed: Import of module '{base_module}' is prohibited.")
        
        # Check from imports (e.g. from os import path)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base_module = node.module.split('.')[0]
                if base_module in FORBIDDEN_MODULES:
                    raise ValueError(f"Security Check Failed: Import of module '{base_module}' is prohibited.")
        
        # Check forbidden builtins
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_BUILTINS:
                raise ValueError(f"Security Check Failed: Access to '{node.id}' is prohibited.")
        
        # Check for function decorated with @tool
        elif isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == "tool":
                    has_tool_decorator = True
                elif isinstance(decorator, ast.Attribute) and decorator.attr == "tool":
                    has_tool_decorator = True
                    
    if not has_tool_decorator:
        raise ValueError("Boilerplate Restriction: Your script must define at least one function decorated with '@tool'.")

    # 2. Bandit Static Security Scan
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        f.write(code.encode('utf-8'))
        temp_path = f.name
        
    try:
        b_conf = b_config.BanditConfig()
        b_mgr = b_manager.BanditManager(b_conf, "info")
        b_mgr.discover_files([temp_path])
        b_mgr.run_tests()
        
        results = b_mgr.get_issue_list()
        for issue in results:
            if issue.severity in ("MEDIUM", "HIGH"):
                raise ValueError(f"Static Analysis Failed: {issue.text} (Severity: {issue.severity})")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
