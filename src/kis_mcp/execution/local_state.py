from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .process import Runner, run_nested_process
from .settings import LocalProcessProfileSettings

_SOURCE_REVISION_MARKER = "__KIS_SOURCE_REVISION="
_SOURCE_TREE_MARKER = "__KIS_SOURCE_TREE="
_SHA = re.compile(r"^[0-9a-f]{40}$")
_NONTERMINAL = frozenset({
    "created", "materializing", "materialized", "starting", "executing", "cancelling"
})
_PROCESS_OWNER_TOKEN = uuid.uuid4().hex


class LocalSourceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LocalExactSource:
    request_id: str
    origin_project: str
    run_dir: Path
    workspace: Path
    revision: str
    tree: str

    @property
    def source_fingerprint(self) -> str:
        payload = json.dumps(
            {"revision": self.revision, "tree": self.tree},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _read_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def reconcile_stale_runs(settings: LocalProcessProfileSettings) -> tuple[str, ...]:
    runs_root = Path(settings.state_root) / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    reconciled: list[str] = []
    for run_dir in sorted(runs_root.iterdir()):
        state_path = run_dir / "state.json"
        if not run_dir.is_dir() or not state_path.is_file():
            continue
        state = _read_state(state_path)
        if not state or state.get("status") not in _NONTERMINAL:
            continue
        if state.get("owner_token") == _PROCESS_OWNER_TOKEN:
            continue
        (run_dir / "cancel.requested").touch(exist_ok=True)
        state.update(
            status="reconciliation_requested",
            authoritative=False,
            reconciled_at=_utc_now(),
        )
        _write_state(state_path, state)
        reconciled.append(run_dir.name)
    return tuple(reconciled)


async def materialize_exact_source(
    runner: Runner,
    settings: LocalProcessProfileSettings,
    *,
    request_id: str,
    project: str,
    revision: str,
) -> LocalExactSource:
    reconcile_stale_runs(settings)
    run_dir = Path(settings.state_root) / "runs" / request_id
    workspace = run_dir / "workspace"
    if run_dir.exists():
        raise LocalSourceError(f"local execution run namespace already exists: {request_id}")
    run_dir.mkdir(parents=True)
    state_path = run_dir / "state.json"
    state = {
        "schema_version": 1,
        "request_id": request_id,
        "origin_project": project,
        "requested_revision": revision,
        "workspace": str(workspace),
        "owner_pid": os.getpid(),
        "owner_token": _PROCESS_OWNER_TOKEN,
        "authoritative": False,
        "status": "materializing",
        "created_at": _utc_now(),
    }
    _write_state(state_path, state)
    outcome = await run_nested_process(
        runner,
        command=_materialize_command(project, revision, workspace),
        timeout_ms=settings.materialize_timeout_ms,
    )
    resolved = _marker(outcome.text, _SOURCE_REVISION_MARKER)
    tree = _marker(outcome.text, _SOURCE_TREE_MARKER)
    if outcome.exit_code != 0 or resolved is None or tree is None:
        state.update(status="source_failed", finished_at=_utc_now())
        _write_state(state_path, state)
        raise LocalSourceError("exact Git source could not be materialized and verified")
    if _SHA.fullmatch(resolved) is None or _SHA.fullmatch(tree) is None:
        state.update(status="source_failed", finished_at=_utc_now())
        _write_state(state_path, state)
        raise LocalSourceError("materialized Git source returned invalid commit/tree identity")
    state.update(status="materialized", resolved_revision=resolved, source_tree=tree)
    _write_state(state_path, state)
    return LocalExactSource(request_id, project, run_dir, workspace, resolved, tree)


def load_run_state(source: LocalExactSource) -> dict[str, Any]:
    state = _read_state(source.run_dir / "state.json")
    if state is None:
        raise LocalSourceError("local execution state is missing or invalid")
    return state


def update_run_state(source: LocalExactSource, **changes: Any) -> None:
    state_path = source.run_dir / "state.json"
    state = load_run_state(source)
    state.update(changes)
    _write_state(state_path, state)


def _marker(text: str, prefix: str) -> str | None:
    for line in reversed(text.splitlines()):
        value = line.strip()
        if value.startswith(prefix):
            return value[len(prefix):].strip().lower()
    return None


def _materialize_command(project: str, revision: str, workspace: Path) -> str:
    project_q = _ps_quote(project)
    revision_q = _ps_quote(revision + "^{commit}")
    workspace_q = _ps_quote(str(workspace))
    return (
        "$ErrorActionPreference='Stop'; "
        f"$resolved = (& git -C {project_q} rev-parse --verify {revision_q}).Trim(); "
        "if ($LASTEXITCODE -ne 0) { exit 91 }; "
        f"& git -C {project_q} worktree add --detach {workspace_q} $resolved; "
        "if ($LASTEXITCODE -ne 0) { exit 92 }; "
        f"$head = (& git -C {workspace_q} rev-parse HEAD).Trim(); "
        f"$tree = (& git -C {workspace_q} rev-parse ($head + '^{{tree}}')).Trim(); "
        "if ($head -ne $resolved) { exit 93 }; "
        'Write-Output ("__KIS_SOURCE_REVISION=" + $head); '
        'Write-Output ("__KIS_SOURCE_TREE=" + $tree); '
        'Write-Output "__KIS_VERIFICATION_EXIT_CODE=0"; exit 0'
    )


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


__all__ = [
    "LocalExactSource",
    "LocalSourceError",
    "load_run_state",
    "materialize_exact_source",
    "reconcile_stale_runs",
    "update_run_state",
]
