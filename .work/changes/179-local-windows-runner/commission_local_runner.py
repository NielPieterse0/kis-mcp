from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(r"C:\Projects\kis-mcp\.work\worktrees\179-local-windows-runner")
sys.path.insert(0, str(REPO / "src"))

from kis_mcp.execution.contracts import ExecutionProfile, ExecutionRequest, ExecutionSource
from kis_mcp.execution.local import LocalProcessExecutionProvider
from kis_mcp.execution.settings import load_execution_runner_settings

PYTHON = r"C:\Projects\.kis-mcp\python-env\Scripts\python.exe"
PYTHON311 = r"C:\Users\piete\AppData\Local\Programs\Python\Python311\python.exe"
OUTPUT = REPO / ".work" / "changes" / "179-local-windows-runner" / "commissioning.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _work_runner(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool != "start_process":
        raise AssertionError(f"unexpected nested Work operation: {tool}")
    timeout_s = max(5.0, float(arguments["timeout_ms"]) / 1000.0 + 5.0)

    def invoke() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["pwsh", "-NoProfile", "-Command", str(arguments["command"])],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )

    completed = await asyncio.to_thread(invoke)
    text = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    return {"text": text}


@dataclass(frozen=True, slots=True)
class Case:
    name: str
    project: str
    revision: str
    executable: str
    arguments: tuple[str, ...]
    timeout_ms: int = 180_000


CASES = {
    "small-122": Case(
        "small-122",
        str(REPO),
        "22f5a699e1a8666d8b5a57da3f3f8b1edcba4439",
        "git",
        ("diff", "--check", "HEAD^", "HEAD"),
        30_000,
    ),
    "medium-121": Case(
        "medium-121",
        str(REPO),
        "762164d9fa81adcbb7426f9902ee54d963e8568b",
        PYTHON,
        (
            "-m", "pytest", "-q", "tests/skills/test_catalogue.py",
            "tests/skills/test_config.py", "tests/skills/test_tools.py",
            "tests/capabilities/test_gateway_composition.py",
        ),
    ),
    "critical-251": Case(
        "critical-251", str(REPO),
        "0d5a0185a277c1158c3f2649146e9305755609ff",
        PYTHON, ("-m", "pytest", "-q", "tests/workflows/coordinator"),
    ),
    "critical-252": Case(
        "critical-252", str(REPO),
        "3196590e675abc916cc94e0f1638aef435ac2973",
        PYTHON, ("-m", "pytest", "-q", "tests/workflows/coordinator"),
    ),
    "large-338": Case(
        "large-338", str(REPO),
        "d38db6af5c34220e60fff65c6ca32ca86cff515f",
        PYTHON,
        (
            "-m", "pytest", "-q", "tests/execution",
            "tests/workflows/verification", "tests/workflows/change_execution",
            "tests/workflows/completion",
        ),
    ),
    "product-doc-solution": Case(
        "product-doc-solution", r"C:\Projects\doc-solution",
        "acf9ffd139ee009d3b921d5cd7c24691bb1c4737",
        PYTHON311,
        ("-m", "unittest", "discover", "-s", "tests", "-v"),
    ),
}


def _receipt_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def _run_case(
    provider: LocalProcessExecutionProvider,
    profile: Any,
    case: Case,
) -> dict[str, Any]:
    request_id = f"commission-{case.name}-{uuid.uuid4().hex[:10]}"
    started_at = _utc_now()
    started = time.perf_counter()
    source = await provider.prepare_exact_source(
        request_id=request_id,
        project=case.project,
        revision=case.revision,
    )
    request = ExecutionRequest(
        request_id=request_id,
        project_id="commissioning",
        verification_profile_id="commissioning",
        source=ExecutionSource(
            project_path=str(source.workspace),
            revision=source.revision,
            exact=True,
        ),
        profile=ExecutionProfile(
            profile_id=profile.profile_id,
            backend_id=profile.backend_id,
            image_id=profile.image_id,
            toolchain_id=profile.toolchain_id,
        ),
        executable=case.executable,
        arguments=case.arguments,
        timeout_ms=case.timeout_ms,
        evidence_limit_chars=20_000,
    )
    result = await provider.execute(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    receipt = Path(result.evidence.receipt_path or "")
    state = json.loads((source.run_dir / "state.json").read_text(encoding="utf-8"))
    record = {
        "name": case.name,
        "project": case.project,
        "requested_revision": case.revision,
        "resolved_revision": result.source_revision,
        "source_tree": result.evidence.source_tree,
        "source_fingerprint": result.evidence.source_fingerprint,
        "request_id": request_id,
        "run_dir": str(source.run_dir),
        "workspace": str(source.workspace),
        "status": result.status,
        "exit_code": result.exit_code,
        "elapsed_ms": elapsed_ms,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "receipt_path": str(receipt),
        "receipt_sha256": result.evidence.receipt_sha256,
        "evidence_reference": result.evidence.evidence_reference,
        "authoritative": state.get("authoritative"),
        "worker_diagnostics": list(result.evidence.diagnostics),
    }
    assert result.status == "passed", record
    assert result.source_revision == case.revision, record
    assert result.evidence.source_tree == source.tree, record
    assert result.evidence.source_fingerprint == source.source_fingerprint, record
    assert receipt.is_file(), record
    assert _receipt_hash(receipt) == result.evidence.receipt_sha256, record
    assert state.get("authoritative") is True, record
    return record


async def _run_pair(
    provider: LocalProcessExecutionProvider,
    profile: Any,
    names: tuple[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    started_at = _utc_now()
    started = time.perf_counter()
    results = await asyncio.gather(
        *(_run_case(provider, profile, CASES[name]) for name in names)
    )
    pair = {
        "cases": list(names),
        "started_at": started_at,
        "finished_at": _utc_now(),
        "wall_ms": round((time.perf_counter() - started) * 1000),
    }
    return pair, list(results)


async def main() -> int:
    settings = load_execution_runner_settings(
        REPO / "settings" / "execution-runners.settings.json"
    )
    profile = settings.profile(settings.default_profile)
    provider = LocalProcessExecutionProvider(_work_runner, profile)
    results: dict[str, dict[str, Any]] = {}
    pairs: list[dict[str, Any]] = []

    for names in (
        ("critical-251", "product-doc-solution"),
        ("critical-252", "large-338"),
    ):
        pair, pair_results = await _run_pair(provider, profile, names)
        pairs.append(pair)
        for result in pair_results:
            results[result["name"]] = result

    for name in ("small-122", "medium-121"):
        results[name] = await _run_case(provider, profile, CASES[name])

    workspaces = [result["workspace"] for result in results.values()]
    run_dirs = [result["run_dir"] for result in results.values()]
    assert len(workspaces) == len(set(workspaces))
    assert len(run_dirs) == len(set(run_dirs))

    payload = {
        "schema_version": 1,
        "commissioning": "local-windows-runner-338",
        "generated_at": _utc_now(),
        "runner_profile": {
            "profile_id": profile.profile_id,
            "backend_id": profile.backend_id,
            "image_id": profile.image_id,
            "toolchain_id": profile.toolchain_id,
        },
        "github_actions_calls": 0,
        "concurrency_pairs": pairs,
        "cases": results,
        "assertions": {
            "all_passed": all(item["status"] == "passed" for item in results.values()),
            "unique_workspaces": len(workspaces) == len(set(workspaces)),
            "unique_run_dirs": len(run_dirs) == len(set(run_dirs)),
            "all_authoritative": all(item["authoritative"] is True for item in results.values()),
            "all_receipts_hash_verified": True,
        },
        "coverage": {
            "small": "small-122",
            "medium": "medium-121",
            "large": "large-338",
            "critical_parallel_backlog": ["critical-251", "critical-252"],
            "registered_product_repo": "product-doc-solution",
            "process_tree_tests": "tests/execution/test_local_worker.py",
            "stale_reconciliation_tests": "tests/execution/test_local_state.py",
        },
    }
    OUTPUT.write_bytes(
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
