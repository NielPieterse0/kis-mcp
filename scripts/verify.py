from __future__ import annotations

import ast
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kis_mcp.config import EXPECTED_RULE_IDS, load_runtime_config  # noqa: E402


def _emit(check: str, ok: bool, **details: object) -> None:
    print(json.dumps({"check": check, "ok": ok, **details}, sort_keys=True))


def _release(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in value.split("."):
        digits = "".join(character for character in part if character.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def verify_configuration() -> int:
    try:
        config = load_runtime_config(ROOT)
    except Exception as exc:
        _emit("configuration", False, error=str(exc))
        return 1
    rule_ids = tuple(rule["id"] for rule in config.raw_policy["rules"])
    ok = rule_ids == EXPECTED_RULE_IDS
    _emit(
        "configuration",
        ok,
        project_boundary=config.project_boundary,
        state_root=config.state_root,
        rules=list(rule_ids),
    )
    return 0 if ok else 1


def verify_interpreter() -> int:
    config = load_runtime_config(ROOT)
    executable = Path(sys.executable).resolve()
    environment_root = Path(config.python_environment_root).resolve()
    try:
        executable.relative_to(environment_root)
        inside = True
    except ValueError:
        inside = False
    _emit(
        "interpreter",
        inside,
        executable=str(executable),
        expected_root=str(environment_root),
    )
    return 0 if inside else 1


def verify_dependency_versions() -> int:
    config = load_runtime_config(ROOT)
    expected_fastmcp = str(config.raw_settings["fastmcp"]["version"])
    try:
        actual_fastmcp = importlib.metadata.version("fastmcp")
        actual_pytest = importlib.metadata.version("pytest")
    except importlib.metadata.PackageNotFoundError as exc:
        _emit("dependencies", False, error=f"Missing dependency: {exc.name}")
        return 1
    pytest_release = _release(actual_pytest)
    ok = actual_fastmcp == expected_fastmcp and (8, 4) <= pytest_release < (9,)
    _emit(
        "dependencies",
        ok,
        fastmcp=actual_fastmcp,
        expected_fastmcp=expected_fastmcp,
        pytest=actual_pytest,
        expected_pytest=">=8.4,<9",
    )
    return 0 if ok else 1


def verify_python_syntax() -> int:
    files = sorted((ROOT / "src").rglob("*.py")) + sorted(
        (ROOT / "scripts").glob("*.py")
    )
    try:
        for path in files:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as exc:
        _emit("python-syntax", False, error=str(exc))
        return 1
    _emit("python-syntax", True, files=len(files))
    return 0


def verify_tests() -> int:
    config = load_runtime_config(ROOT)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(SRC)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-o",
            f"cache_dir={config.pytest_cache_root}",
        ],
        cwd=ROOT,
        env=environment,
        check=False,
    )
    _emit("pytest", completed.returncode == 0, exit_code=completed.returncode)
    return completed.returncode


def main() -> int:
    for check in (
        verify_configuration,
        verify_interpreter,
        verify_dependency_versions,
        verify_python_syntax,
        verify_tests,
    ):
        if check() != 0:
            return 1
    _emit("verification", True, service="kis-mcp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
