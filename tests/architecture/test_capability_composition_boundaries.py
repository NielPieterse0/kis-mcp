from __future__ import annotations

import ast
from pathlib import Path

from kis_mcp.capabilities.settings import load_capability_settings

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "kis_mcp"
DOMAINS = ("providers", "tools", "discover", "skills", "workflows")


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            values.add(node.module)
    return values


def test_domains_never_import_server_composition() -> None:
    violations: list[str] = []
    for domain in DOMAINS:
        for path in (SOURCE_ROOT / domain).rglob("*.py"):
            if "kis_mcp.server" in imports(path):
                violations.append(path.relative_to(REPOSITORY_ROOT).as_posix())
    assert violations == []


def test_gateway_composition_imports_domains_through_platform_entrypoints_only() -> None:
    path = SOURCE_ROOT / "gateway" / "composition.py"
    domain_imports = {
        value
        for value in imports(path)
        if any(value == f"kis_mcp.{domain}" or value.startswith(f"kis_mcp.{domain}.") for domain in DOMAINS)
        or any(value == f"{domain}" or value.startswith(f"{domain}.") for domain in DOMAINS)
    }
    assert domain_imports == {
        "discover.platform",
        "providers.platform",
        "skills.platform",
        "tools.platform",
        "workflows.platform",
    }


def test_workflow_platform_uses_domain_platforms_not_adapter_internals() -> None:
    values = imports(SOURCE_ROOT / "workflows" / "platform.py")
    forbidden = {
        value
        for value in values
        if "codex_cli" in value or ".nvidia" in value or ".github" in value or ".supabase" in value
    }
    assert forbidden == set()


def test_direct_profile_is_bounded_and_contains_only_user_entrypoints() -> None:
    settings = load_capability_settings()
    assert len(settings.direct_operations) <= settings.direct_profile_max <= 24
    assert len(settings.direct_operations) == len(set(settings.direct_operations))
    assert {"search_capabilities", "describe_capability", "recommend_workflow"}.issubset(
        settings.direct_operations
    )
    assert {"execute_read_action", "execute_change_action", "execute_external_action"}.issubset(
        settings.direct_operations
    )
    assert "list_skills" not in settings.direct_operations
    assert "get_code_context" not in settings.direct_operations
    assert "analyze_change" not in settings.direct_operations


def test_server_remains_a_thin_facade() -> None:
    source = (SOURCE_ROOT / "server.py").read_text(encoding="utf-8")
    assert len(source.splitlines()) <= 80
    assert "compose_gateway" in source
    assert "register_" not in source
