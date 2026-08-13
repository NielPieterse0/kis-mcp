from __future__ import annotations

import ast
import importlib.metadata
import importlib.util
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


def _line_ending_violations(output: str) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for line in output.splitlines():
        metadata, separator, path = line.partition("\t")
        if not separator:
            continue
        columns = metadata.split()
        if len(columns) < 3:
            continue
        index = columns[0].removeprefix("i/")
        worktree = columns[1].removeprefix("w/")
        attributes = " ".join(columns[2:]).removeprefix("attr/")
        if "eol=lf" not in attributes:
            continue
        if index in {"crlf", "mixed"} or worktree in {"crlf", "mixed"}:
            violations.append(
                {"path": path, "index": index, "worktree": worktree}
            )
    return violations


def verify_repository_line_endings() -> int:
    required_literals = {
        ROOT / ".gitattributes": ("* text=auto eol=lf", "*.cmd text eol=crlf"),
        ROOT / ".editorconfig": ("end_of_line = lf",),
    }
    missing_policy: list[str] = []
    for path, literals in required_literals.items():
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            missing_policy.append(str(path.relative_to(ROOT)))
            continue
        missing_policy.extend(
            f"{path.relative_to(ROOT)}:{literal}"
            for literal in literals
            if literal not in content
        )

    expected_config = {
        "core.autocrlf": "false",
        "core.eol": "lf",
        "core.safecrlf": "true",
    }
    actual_config: dict[str, str] = {}
    for key in expected_config:
        completed = subprocess.run(
            ["git", "config", "--local", "--get", key],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        actual_config[key] = (
            completed.stdout.strip().casefold()
            if completed.returncode == 0
            else "<missing>"
        )

    completed = subprocess.run(
        ["git", "ls-files", "--eol"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        _emit(
            "repository-line-endings",
            False,
            error=completed.stderr.strip() or "git ls-files --eol failed",
        )
        return 1

    violations = _line_ending_violations(completed.stdout)
    config_ok = actual_config == expected_config
    ok = not missing_policy and config_ok and not violations
    _emit(
        "repository-line-endings",
        ok,
        expected_config=expected_config,
        actual_config=actual_config,
        missing_policy=missing_policy,
        violations=violations,
    )
    return 0 if ok else 1


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


def verify_change_governance() -> int:
    governance_path = ROOT / "scripts" / "change-governance.py"
    template_root = ROOT / ".work" / "changes" / "_template"
    required_paths = [
        governance_path,
        ROOT / "scripts" / "change-workflow.ps1",
        *(template_root / name for name in ("scope.json", "spec.md", "plan.md", "tasks.md", "closeout.md", "change.md")),
    ]
    missing = [str(path.relative_to(ROOT)) for path in required_paths if not path.is_file()]
    gitignore_lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    if ".work/worktrees/" not in gitignore_lines:
        missing.append(".gitignore:.work/worktrees/")
    if missing:
        _emit("change-governance", False, missing=missing)
        return 1

    spec = importlib.util.spec_from_file_location("kis_change_governance", governance_path)
    if spec is None or spec.loader is None:
        _emit("change-governance", False, error="Unable to load change-governance.py")
        return 1
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        claims = []
        changes_root = ROOT / ".work" / "changes"
        for scope_path in sorted(changes_root.glob("*/scope.json")):
            if scope_path.parent.name.startswith("_"):
                continue
            claims.append(module.load_claim(scope_path))
        conflicts = module.find_claim_conflicts(claims)
        if conflicts:
            _emit("change-governance", False, conflicts=conflicts)
            return 1
    except Exception as exc:
        _emit("change-governance", False, error=str(exc))
        return 1

    _emit(
        "change-governance",
        True,
        script="scripts/change-governance.py",
        template=".work/changes/_template",
        claims=len(claims),
    )
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
        verify_repository_line_endings,
        verify_configuration,
        verify_interpreter,
        verify_dependency_versions,
        verify_python_syntax,
        verify_change_governance,
        verify_tests,
    ):
        if check() != 0:
            return 1
    _emit("verification", True, service="kis-mcp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
