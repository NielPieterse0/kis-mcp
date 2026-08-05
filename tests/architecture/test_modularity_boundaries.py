from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "kis_mcp"


def _python_sources(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts))


def _relative(path: Path) -> str:
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def test_infrastructure_settings_do_not_depend_on_code_review_workflow() -> None:
    targets = (
        *_python_sources(SOURCE_ROOT / "providers" / "nvidia"),
        *_python_sources(SOURCE_ROOT / "tools" / "codex_cli"),
        SOURCE_ROOT / "providers" / "platform.py",
    )
    offenders = [
        _relative(path)
        for path in targets
        if "workflows.code_review" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
