from __future__ import annotations

import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_BOUNDARY = Path(r"C:\Projects")

CREATE_CHANGE_WORKTREE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "repository": {"type": "string"},
        "change_id": {"type": "string"},
        "outcome": {"type": "string"},
        "owned_paths": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "complexity": {"type": "string", "enum": ["small", "medium", "large"]},
        "risk_triggers": {"type": "array", "items": {"type": "string"}},
        "allocate_next": {"type": "boolean"},
    },
    "required": ["repository", "change_id", "outcome", "owned_paths"],
    "additionalProperties": False,
}

COMMIT_CHANGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string"},
        "message": {"type": "string", "minLength": 1},
        "paths": {"type": "array", "items": {"type": "string"}, "minItems": 1},
    },
    "required": ["path", "message", "paths"],
    "additionalProperties": False,
}

LIST_WORKTREES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"repository": {"type": "string"}},
    "required": ["repository"],
    "additionalProperties": False,
}

VALIDATE_CHANGE_CLAIMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "repository": {"type": "string"},
        "claims_only": {"type": "boolean"},
    },
    "required": ["repository"],
    "additionalProperties": False,
}

CLEANUP_CHANGE_WORKTREE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "repository": {"type": "string"},
        "change_id": {"type": "string", "minLength": 1},
    },
    "required": ["repository", "change_id"],
    "additionalProperties": False,
}

RETIRE_CLOSED_ORPHAN_WORKTREE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "repository": {"type": "string"},
        "change_id": {"type": "string", "minLength": 1},
        "terminal_work_confirmed": {"type": "boolean"},
    },
    "required": ["repository", "change_id", "terminal_work_confirmed"],
    "additionalProperties": False,
}


def _within_project_boundary(raw: str) -> Path:
    path = Path(raw).resolve(strict=True)
    boundary = PROJECT_BOUNDARY.resolve(strict=True)
    if path != boundary and boundary not in path.parents:
        raise ValueError(f"PROJECT_BOUNDARY_VIOLATION: {path}")
    return path


def _run(argv: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(f"GOVERNED_CHANGE_OPERATION_FAILED: {detail}")
    return result


def _validate_pathspec(pathspec: str) -> str:
    normalized = pathspec.replace("\\", "/").strip()
    candidate = PurePosixPath(normalized)
    if not normalized or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"INVALID_CHANGE_PATHSPEC: {pathspec}")
    return normalized


def _create_change_worktree(arguments: dict[str, Any]) -> dict[str, Any]:
    repository = _within_project_boundary(str(arguments["repository"]))
    script = repository / "scripts" / "change-workflow.ps1"
    if not script.is_file():
        raise ValueError(f"CHANGE_WORKFLOW_NOT_FOUND: {script}")

    argv = [
        "pwsh",
        "-NoProfile",
        "-File",
        str(script),
        "new",
        str(arguments["change_id"]),
        "--outcome",
        str(arguments["outcome"]),
    ]
    if bool(arguments.get("allocate_next", False)):
        argv.append("--allocate-next")
    for pathspec in arguments["owned_paths"]:
        argv.extend(("--owned", _validate_pathspec(str(pathspec))))
    complexity = arguments.get("complexity")
    if complexity:
        argv.extend(("--complexity", str(complexity)))
    for trigger in arguments.get("risk_triggers", []):
        argv.extend(("--risk-trigger", str(trigger)))

    result = _run(argv, cwd=repository)
    return {
        "operation": "create_change_worktree",
        "repository": str(repository),
        "output": result.stdout.strip(),
    }


def _commit_change(arguments: dict[str, Any]) -> dict[str, Any]:
    worktree = _within_project_boundary(str(arguments["path"]))
    branch = _run(["git", "branch", "--show-current"], cwd=worktree).stdout.strip()
    if not branch.startswith("change/"):
        raise ValueError(f"CHANGE_WORKTREE_REQUIRED: current branch is {branch!r}")

    pathspecs = [_validate_pathspec(str(item)) for item in arguments["paths"]]
    preexisting = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--exit-code"],
        cwd=str(worktree),
        check=False,
        timeout=30,
    )
    if preexisting.returncode == 1:
        raise ValueError("PREEXISTING_STAGED_CHANGES: commit_change requires a clean index")
    if preexisting.returncode != 0:
        raise ValueError("GOVERNED_CHANGE_OPERATION_FAILED: unable to inspect staged changes")

    _run(["git", "add", "--", *pathspecs], cwd=worktree)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--exit-code"],
        cwd=str(worktree),
        check=False,
        timeout=30,
    )
    if staged.returncode == 0:
        raise ValueError("NO_STAGED_CHANGE: selected paths contain no changes")
    if staged.returncode != 1:
        raise ValueError("GOVERNED_CHANGE_OPERATION_FAILED: unable to inspect staged changes")

    _run(["git", "commit", "-m", str(arguments["message"])], cwd=worktree)
    head = _run(["git", "rev-parse", "HEAD"], cwd=worktree).stdout.strip()
    return {
        "operation": "commit_change",
        "path": str(worktree),
        "branch": branch,
        "head": head,
    }


def _change_workflow_script(repository: Path) -> Path:
    script = repository / "scripts" / "change-workflow.ps1"
    if not script.is_file():
        raise ValueError(f"CHANGE_WORKFLOW_NOT_FOUND: {script}")
    return script


def _run_change_workflow(
    repository: Path,
    *arguments: str,
) -> Any:
    result = _run(
        ["pwsh", "-NoProfile", "-File", str(_change_workflow_script(repository)), *arguments],
        cwd=repository,
    )
    text = result.stdout.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("GOVERNED_CHANGE_INVALID_OUTPUT") from exc


def _list_worktrees(arguments: dict[str, Any]) -> dict[str, Any]:
    repository = _within_project_boundary(str(arguments["repository"]))
    claims = _run_change_workflow(repository, "list")
    return {"operation": "list_worktrees", "repository": str(repository), "claims": claims}


def _validate_change_claims(arguments: dict[str, Any]) -> dict[str, Any]:
    repository = _within_project_boundary(str(arguments["repository"]))
    argv = ["validate"]
    if bool(arguments.get("claims_only", True)):
        argv.append("--claims-only")
    result = _run_change_workflow(repository, *argv)
    return {"operation": "validate_change_claims", "repository": str(repository), **result}


def _cleanup_change_worktree(arguments: dict[str, Any]) -> dict[str, Any]:
    repository = _within_project_boundary(str(arguments["repository"]))
    result = _run_change_workflow(repository, "cleanup", str(arguments["change_id"]))
    return {"operation": "cleanup_change_worktree", "repository": str(repository), **result}


def _retire_closed_orphan_worktree(arguments: dict[str, Any]) -> dict[str, Any]:
    repository = _within_project_boundary(str(arguments["repository"]))
    argv = ["retire-orphan", str(arguments["change_id"])]
    if bool(arguments.get("terminal_work_confirmed", False)):
        argv.append("--terminal-work-confirmed")
    result = _run_change_workflow(repository, *argv)
    return {"operation": "retire_closed_orphan_worktree", "repository": str(repository), **result}


def execute_governed_change_operation(operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if operation == "create_change_worktree":
        return _create_change_worktree(arguments)
    if operation == "commit_change":
        return _commit_change(arguments)
    if operation == "list_worktrees":
        return _list_worktrees(arguments)
    if operation == "validate_change_claims":
        return _validate_change_claims(arguments)
    if operation == "cleanup_change_worktree":
        return _cleanup_change_worktree(arguments)
    if operation == "retire_closed_orphan_worktree":
        return _retire_closed_orphan_worktree(arguments)
    raise ValueError(f"UNKNOWN_GOVERNED_CHANGE_OPERATION: {operation}")


__all__ = [
    "CLEANUP_CHANGE_WORKTREE_SCHEMA",
    "COMMIT_CHANGE_SCHEMA",
    "CREATE_CHANGE_WORKTREE_SCHEMA",
    "LIST_WORKTREES_SCHEMA",
    "RETIRE_CLOSED_ORPHAN_WORKTREE_SCHEMA",
    "VALIDATE_CHANGE_CLAIMS_SCHEMA",
    "execute_governed_change_operation",
]
