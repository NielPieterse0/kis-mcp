from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import ExecutionRequest
from .local_state import LocalExactSource, load_run_state

_RECEIPT_NAME = "receipt.json"
_RECEIPT_HASH_NAME = "receipt.sha256"
_LOCK_NAMES = (
    "uv.lock", "poetry.lock", "Pipfile.lock", "package-lock.json",
    "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "Cargo.lock",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _combined_file_digest(files: list[Path], root: Path) -> str | None:
    if not files:
        return None
    entries = [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256_file(path)}
        for path in sorted(files)
    ]
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(payload)


def source_lock_digest(workspace: Path) -> str | None:
    return _combined_file_digest(
        [workspace / name for name in _LOCK_NAMES if (workspace / name).is_file()],
        workspace,
    )


def verifier_digest(request: ExecutionRequest, workspace: Path) -> str:
    files: list[Path] = []
    for argument in request.arguments:
        candidate = Path(argument)
        if not candidate.is_absolute():
            candidate = workspace / candidate
        try:
            resolved = candidate.resolve()
            resolved.relative_to(workspace.resolve())
        except (OSError, ValueError):
            continue
        if resolved.is_file():
            files.append(resolved)
    payload = {
        "executable": request.executable,
        "arguments": list(request.arguments),
        "files": [
            {
                "path": path.relative_to(workspace.resolve()).as_posix(),
                "sha256": _sha256_file(path),
            }
            for path in sorted(set(files))
        ],
    }
    return _sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def write_exact_receipt(
    source: LocalExactSource,
    request: ExecutionRequest,
    worker_result: dict[str, Any],
    *,
    stdout_path: Path,
    stderr_path: Path,
) -> tuple[Path, str, str]:
    state = load_run_state(source)
    log_payload = {
        "stdout": _sha256_file(stdout_path) if stdout_path.is_file() else None,
        "stderr": _sha256_file(stderr_path) if stderr_path.is_file() else None,
    }
    log_digest = _sha256_bytes(
        json.dumps(log_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    authoritative = (
        worker_result.get("status") == "completed"
        and worker_result.get("job_assigned") is True
    )
    receipt = {
        "schema_version": 1,
        "contract": "local-verification-receipt-v1",
        "request_id": request.request_id,
        "project_id": request.project_id,
        "origin_project": state.get("origin_project"),
        "workspace": str(source.workspace),
        "requested_revision": state.get("requested_revision"),
        "source_revision": source.revision,
        "source_tree": source.tree,
        "source_fingerprint": source.source_fingerprint,
        "lockfile_digest": source_lock_digest(source.workspace),
        "verifier_digest": verifier_digest(request, source.workspace),
        "runner": {
            "backend_id": request.profile.backend_id,
            "profile_id": request.profile.profile_id,
            "image_id": request.profile.image_id,
            "toolchain_id": request.profile.toolchain_id,
            "containment": "windows-job-object-kill-on-close",
        },
        "started_at": worker_result.get("started_at"),
        "finished_at": worker_result.get("finished_at"),
        "duration_ms": worker_result.get("duration_ms"),
        "worker_status": worker_result.get("status"),
        "exit_code": worker_result.get("exit_code"),
        "log_digest": log_digest,
        "authoritative": authoritative,
        "retained_workspace": True,
        "digest_sidecar": _RECEIPT_HASH_NAME,
    }
    receipt_path = source.run_dir / _RECEIPT_NAME
    encoded = (
        json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    with receipt_path.open("xb") as target:
        target.write(encoded)
    receipt_sha256 = _sha256_bytes(encoded)
    hash_path = source.run_dir / _RECEIPT_HASH_NAME
    with hash_path.open("x", encoding="ascii", newline="\n") as target:
        target.write(receipt_sha256 + "\n")
    reference = f"kis-local-verification:{receipt_path}#sha256={receipt_sha256}"
    return receipt_path, receipt_sha256, reference


__all__ = [
    "source_lock_digest",
    "verifier_digest",
    "write_exact_receipt",
]
