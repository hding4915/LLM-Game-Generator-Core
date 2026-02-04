import ast
import os
import logging
import importlib.util
import importlib

logger = logging.getLogger("Member3-Fixer")

# Cache for external package symbols to avoid repeated expensive imports
EXTERNAL_SYMBOL_CACHE = {}


def is_local_module(module_name, folder_path):
    """Check if the module exists as a local .py file in the project folder."""
    return os.path.exists(os.path.join(folder_path, f"{module_name}.py"))


def get_external_symbols(module_name):
    """Dynamically import external packages and retrieve their members for validation."""
    if module_name in EXTERNAL_SYMBOL_CACHE:
        return EXTERNAL_SYMBOL_CACHE[module_name]

    try:
        # Check if the module specification exists
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return set()

        # Dynamically import the module to inspect its attributes
        module = importlib.import_module(module_name)
        symbols = set(dir(module))
        EXTERNAL_SYMBOL_CACHE[module_name] = symbols
        return symbols
    except Exception as e:
        logger.warning(f"Failed to analyze external package '{module_name}': {e}")
        return set()


def static_code_check(file_path: str) -> tuple[bool, str]:
    """Perform a static syntax check on a single file using the ast module."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        ast.parse(code)
        return True, "Syntax check passed ✅"
    except SyntaxError as e:
        logger.error(f"Syntax error in {os.path.basename(file_path)}: {e}")
        return False, f"Syntax Error ❌: {e}"
    except Exception as e:
        logger.exception(f"Unexpected error during static check of {os.path.basename(file_path)}")
        return False, f"Other Error ❌: {e}"


def get_project_symbols(folder_path):
    """Scan all local Python files to build a global symbol table of functions, classes, and variables."""
    symbol_table = {}
    for file in os.listdir(folder_path):
        if file.endswith(".py"):
            path = os.path.join(folder_path, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                # defs now includes 'variables' to support constants from files like config.py
                defs = {"functions": set(), "classes": set(), "variables": set()}
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        defs["functions"].add(node.name)
                    elif isinstance(node, ast.ClassDef):
                        defs["classes"].add(node.name)
                    elif isinstance(node, ast.Assign):
                        # Capture global variable assignments
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                defs["variables"].add(target.id)

                # Use filename without extension as the module name
                module_name = os.path.splitext(file)[0]
                symbol_table[module_name] = defs
            except Exception as e:
                logger.error(f"Failed to scan local file {file}: {e}")
    return symbol_table


def check_cross_file_calls(file_path, symbol_table) -> list[str]:
    """Verify if calls to other modules (local or external) are valid."""
    folder_path = os.path.dirname(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except Exception as e:
        return [f"Failed to read file for semantic check: {e}"]

    # 1. Map import aliases to their actual module names
    imported_modules = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules[node.module] = node.module

    errors = []

    # 2. Inspect Attribute nodes (e.g., pygame.display or config.SCREEN_WIDTH)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            # Resolve the base object of the call chain
            base_node = node.value
            while isinstance(base_node, ast.Attribute):
                base_node = base_node.value

            # Check if the base object is an imported module
            if isinstance(base_node, ast.Name) and base_node.id in imported_modules:
                module_alias = base_node.id
                actual_module_name = imported_modules[module_alias]
                member_name = node.attr

                # Case A: Validation against Local Project Modules
                if actual_module_name in symbol_table:
                    local_defs = symbol_table[actual_module_name]
                    all_valid = local_defs["functions"] | local_defs["classes"] | local_defs["variables"]
                    if member_name not in all_valid:
                        errors.append(f"Error: '{member_name}' not found in local module '{actual_module_name}'")

                # Case B: Validation against External Packages (e.g., pygame, math)
                elif not is_local_module(actual_module_name, folder_path):
                    ext_symbols = get_external_symbols(actual_module_name)
                    # If symbols are retrieved, verify the existence of the attribute
                    if ext_symbols and member_name not in ext_symbols:
                        errors.append(f"Error: '{member_name}' not found in external package '{actual_module_name}'")

    return errors