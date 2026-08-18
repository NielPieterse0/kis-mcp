from __future__ import annotations

import asyncio
import hashlib
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.execution.settings import (
    ExecutionRunnerSettings,
    LocalProcessProfileSettings,
    RunnerProfileSettings,
)
from kis_mcp.workflows.verification.execution import VerificationExecutionService


@dataclass
class _Inspection:
    verification: dict[str, Any]


class _Inspector:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def inspect(self, request: Any) -> _Inspection:
        self.calls.append(request.path)
        return _Inspection(verification={"declarations": [{
            "id": "exact-python", "title": "Exact Python proof", "category": "test",
            "source_path": "probe.py", "profile": "python",
            "arguments": ["-c", "print('exact-ok')"],
        }]})


class _ShellRunner:
    async def __call__(self, tool: str, arguments: dict[str, Any]) -> Any:
        assert tool == "start_process"
        completed = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", str(arguments["command"])],
            capture_output=True,
            text=True,
            timeout=max(5, int(arguments["timeout_ms"]) // 1000 + 5),
            check=False,
        )
        return {"text": "\n".join((completed.stdout, completed.stderr))}


def _settings(state_root: Path) -> ExecutionRunnerSettings:
    return ExecutionRunnerSettings(
        default_profile="local-process",
        evidence_limit_chars=20_000,
        profiles=(RunnerProfileSettings(
            profile_id="local-process",
            backend_id="local-process",
            enabled=True,
            image_id="host-current",
            toolchain_id="repository-declared",
            local=LocalProcessProfileSettings(
                state_root=str(state_root),
                materialize_timeout_ms=30_000,
                worker_cleanup_grace_ms=5_000,
            ),
        ),),
    )


@pytest.mark.skipif(__import__("sys").platform != "win32", reason="Windows local runner")
def test_exact_revision_runs_in_isolated_job_and_emits_hash_bound_receipt() -> None:
    root = Path(r"C:\Projects\.kis-mcp\temp") / f"exact-run-test-{uuid.uuid4().hex}"
    repository = root / "repo"
    state_root = root / "state"
    repository.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "KIS Test"], check=True)
    (repository / "probe.py").write_text("print('probe')\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "probe.py"], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-q", "-m", "fixture"], check=True)
    revision = subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
    ).strip()
    inspector = _Inspector()
    result = None
    try:
        result = asyncio.run(VerificationExecutionService(
            inspector=inspector,
            runner=_ShellRunner(),
            execution_settings=_settings(state_root),
        ).run(
            project=str(repository),
            verification_id="exact-python",
            exact_revision=revision,
            timeout_ms=10_000,
        ))
        assert result.status == "passed"
        assert result.source_revision == revision
        assert result.source_tree and len(result.source_tree) == 40
        assert result.source_fingerprint and len(result.source_fingerprint) == 64
        assert result.receipt_path and result.receipt_sha256
        receipt_path = Path(result.receipt_path)
        assert receipt_path.is_file()
        assert hashlib.sha256(receipt_path.read_bytes()).hexdigest() == result.receipt_sha256
        assert result.evidence_reference == (
            f"kis-local-verification:{receipt_path}#sha256={result.receipt_sha256}"
        )
        assert inspector.calls == [str(receipt_path.parent / "workspace")]
        assert "exact-ok" in result.evidence
    finally:
        if result is not None and result.receipt_path:
            workspace = Path(result.receipt_path).parent / "workspace"
            subprocess.run(
                ["git", "-C", str(repository), "worktree", "remove", "--force", str(workspace)],
                capture_output=True,
                check=False,
            )
        shutil.rmtree(root, ignore_errors=True)
