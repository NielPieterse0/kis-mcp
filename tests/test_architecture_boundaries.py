from __future__ import annotations

import ast
from pathlib import Path

from kis_mcp.desktop_commander import (
    COMMAND_TOOLS,
    DELETE_PATH_KEYS,
    NETWORK_ONLY_TOOLS,
    WRITE_PATH_KEYS,
)


SOURCE_ROOT = Path(__file__).parents[1] / "src" / "kis_mcp"
CORE_MODULES = ("models.py", "contracts.py", "paths.py", "policy.py")
PROVIDER_TOOL_NAMES = frozenset(
    {
        *COMMAND_TOOLS,
        *DELETE_PATH_KEYS,
        *NETWORK_ONLY_TOOLS,
        *WRITE_PATH_KEYS,
        "move_file",
        "set_config_value",
        "write_pdf",
    }
)


def _tree(name: str) -> ast.Module:
    return ast.parse((SOURCE_ROOT / name).read_text(encoding="utf-8"), filename=name)


def _imports(name: str) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(_tree(name)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            imported.add(prefix + (node.module or ""))
    return imported


def _string_literals(name: str) -> set[str]:
    return {
        node.value.casefold()
        for node in ast.walk(_tree(name))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_core_modules_do_not_import_fastmcp_or_provider_adapter() -> None:
    for name in CORE_MODULES:
        imports = _imports(name)
        assert not any(module.lstrip(".").startswith("fastmcp") for module in imports), name
        assert ".desktop_commander" not in imports, name


def test_contract_module_does_not_import_implementation_services() -> None:
    imports = _imports("contracts.py")
    assert ".quarantine" not in imports


def test_middleware_depends_on_contracts_not_concrete_implementations() -> None:
    imports = _imports("middleware.py")
    assert ".contracts" in imports
    assert ".desktop_commander" not in imports
    assert ".policy" not in imports


def test_policy_and_middleware_do_not_embed_provider_tool_names() -> None:
    provider_names = {name.casefold() for name in PROVIDER_TOOL_NAMES}
    assert not (_string_literals("policy.py") & provider_names)
    assert not (_string_literals("middleware.py") & provider_names)
