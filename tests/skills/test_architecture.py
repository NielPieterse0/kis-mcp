from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPOSITORY_ROOT / "src" / "kis_mcp" / "skills"


def _tree(relative: str) -> ast.Module:
    return ast.parse((REPOSITORY_ROOT / relative).read_text(encoding="utf-8"))


def test_skills_dependency_direction_is_explicit() -> None:
    allowed_local_imports = {
        "config.py": set(),
        "models.py": set(),
        "errors.py": set(),
        "frontmatter.py": {"errors"},
        "source.py": {"config", "errors", "frontmatter"},
        "catalogue.py": {"capabilities", "config", "errors", "metadata", "models", "source"},
        "metadata.py": {"capabilities", "models"},
        "platform.py": {"capabilities", "metadata", "models", "service", "tools"},
        "backend.py": {"errors"},
        "service.py": {"backend", "catalogue", "errors", "models"},
        "tools.py": {"backend", "catalogue", "config", "errors", "models", "service"},
    }

    for file_name, allowed in allowed_local_imports.items():
        tree = ast.parse((SKILLS_ROOT / file_name).read_text(encoding="utf-8"))
        imports = {
            node.module.lstrip(".").split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.level > 0
            and node.module is not None
        }
        assert imports <= allowed, (file_name, imports - allowed)


def test_mutation_layers_do_not_write_filesystem_directly() -> None:
    forbidden_methods = {
        "mkdir",
        "write_text",
        "write_bytes",
        "replace",
        "rename",
        "unlink",
        "rmdir",
        "touch",
    }
    for file_name in ("backend.py", "service.py"):
        tree = ast.parse((SKILLS_ROOT / file_name).read_text(encoding="utf-8"))
        violations: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in forbidden_methods:
                continue
            value = node.func.value
            backend_call = (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and value.value.id == "self"
                and value.attr == "backend"
            )
            if not backend_call:
                violations.append((node.func.attr, node.lineno))
        assert violations == [], (file_name, violations)


def test_gateway_composes_skills_through_platform_entrypoint() -> None:
    source = (
        REPOSITORY_ROOT / "src" / "kis_mcp" / "gateway" / "composition.py"
    ).read_text(encoding="utf-8")
    assert "from ..skills.platform import" in source
    assert "register_platform_skills(server)" in source
    assert "register_skills_tools" not in source
    assert "desktop_commander" not in (
        SKILLS_ROOT / "backend.py"
    ).read_text(encoding="utf-8").casefold()


def test_verifier_accepts_only_the_approved_shared_skills_root() -> None:
    source = (REPOSITORY_ROOT / "scripts" / "verify.ps1").read_text(
        encoding="utf-8"
    )
    assert "active runtime skills catalogue is present" not in source
    assert "C:\\Projects\\.agents\\skills" in source
    assert "C:\\Projects\\.kis-mcp\\temp\\skills" in source
    assert "SKILLS_SETTINGS_INVALID" in source
