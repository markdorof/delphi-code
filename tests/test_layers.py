import ast
from pathlib import Path
import unittest

PACKAGE = Path(__file__).resolve().parent.parent / "delphi_code"
TERMINAL_LIBRARIES = {"questionary", "prompt_toolkit", "rich", "tqdm"}
WEB_LIBRARIES = {"fastapi", "starlette", "pydantic", "uvicorn"}
TERMINAL_STREAMS = {"stdout", "stderr"}
CORE_LAYERS_EACH_MAY_IMPORT = {
    "domain": {"domain"},
    "infrastructure": {"domain", "infrastructure"},
    "services": {"domain", "infrastructure", "services"},
}
FRONT_ENDS = ("cli", "mcp_server", "http_api")
PORTS_AND_FOUNDATIONS_FOR_TERMINAL_UI = ("domain.", "services.progress")
VIEW_BUILDING_BLOCKS_FOR_CONTROLLERS = ("cli.terminal.views", "cli.terminal.text_layout")
LAYERS_WITHOUT_TERMINAL_ACCESS = (
    "domain",
    "infrastructure",
    "services",
    "cli/controllers",
    "cli/main.py",
    "mcp_server",
    "http_api",
)


def modules_of(layer):
    location = PACKAGE / layer
    paths = [location] if location.suffix == ".py" else sorted(location.rglob("*.py"))
    return [(path, ast.parse(path.read_text())) for path in paths]


def package_imports(path, tree):
    importing_package = path.parent.relative_to(PACKAGE).parts
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level:
            base_package = importing_package[: len(importing_package) - (node.level - 1)]
            module = ".".join([*base_package, *(node.module or "").split(".")]).strip(".")
            yield from (f"{module}.{alias.name}".strip(".") for alias in node.names)


def third_party_imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            yield node.module.split(".")[0]


def terminal_uses(tree):
    return [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and (
            node.attr == "isatty"
            or (isinstance(node.value, ast.Name) and node.value.id == "sys" and node.attr in TERMINAL_STREAMS)
        )
    ]


class Layers(unittest.TestCase):
    def test_each_core_layer_imports_only_the_layers_beneath_it(self):
        for layer, allowed_layers in CORE_LAYERS_EACH_MAY_IMPORT.items():
            for path, tree in modules_of(layer):
                for imported in package_imports(path, tree):
                    with self.subTest(module=str(path.relative_to(PACKAGE)), imports=imported):
                        self.assertIn(imported.split(".")[0], allowed_layers)

    def test_front_ends_use_the_core_and_only_start_each_other(self):
        for front_end in FRONT_ENDS:
            allowed_layers = {*CORE_LAYERS_EACH_MAY_IMPORT, front_end}
            started_servers = {f"{other}.serve" for other in FRONT_ENDS if other != front_end}
            for path, tree in modules_of(front_end):
                for imported in package_imports(path, tree):
                    with self.subTest(module=str(path.relative_to(PACKAGE)), imports=imported):
                        self.assertTrue(imported.split(".")[0] in allowed_layers or imported in started_servers)

    def test_other_front_ends_load_only_when_their_server_starts(self):
        for front_end in FRONT_ENDS:
            for path, tree in modules_of(front_end):
                imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]
                module_level = ast.Module(body=imports, type_ignores=[])
                for imported in package_imports(path, module_level):
                    with self.subTest(module=str(path.relative_to(PACKAGE)), imports=imported):
                        self.assertFalse(imported.split(".")[0] in set(FRONT_ENDS) - {front_end}, imported)

    def test_terminal_ui_knows_only_ports_and_foundations(self):
        for path, tree in modules_of("cli/terminal"):
            for imported in package_imports(path, tree):
                if not imported.startswith("cli.terminal."):
                    with self.subTest(module=str(path.relative_to(PACKAGE)), imports=imported):
                        self.assertTrue(imported.startswith(PORTS_AND_FOUNDATIONS_FOR_TERMINAL_UI), imported)

    def test_controllers_use_only_views_from_the_terminal_ui(self):
        for path, tree in modules_of("cli/controllers"):
            for imported in package_imports(path, tree):
                if imported.startswith("cli.") and not imported.startswith("cli.controllers"):
                    with self.subTest(module=path.name, imports=imported):
                        self.assertTrue(imported.startswith(VIEW_BUILDING_BLOCKS_FOR_CONTROLLERS), imported)

    def test_only_the_terminal_ui_uses_terminal_libraries_and_streams(self):
        for layer in LAYERS_WITHOUT_TERMINAL_ACCESS:
            for path, tree in modules_of(layer):
                with self.subTest(module=str(path.relative_to(PACKAGE))):
                    self.assertFalse(TERMINAL_LIBRARIES & set(third_party_imports(tree)))
                    self.assertEqual(terminal_uses(tree), [])

    def test_only_the_http_api_uses_web_libraries(self):
        for layer in (*CORE_LAYERS_EACH_MAY_IMPORT, "cli", "mcp_server"):
            for path, tree in modules_of(layer):
                with self.subTest(module=str(path.relative_to(PACKAGE))):
                    self.assertFalse(WEB_LIBRARIES & set(third_party_imports(tree)))


if __name__ == "__main__":
    unittest.main()
