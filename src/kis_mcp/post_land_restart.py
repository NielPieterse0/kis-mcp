"""Schedule the selected development runtime refresh after kis-mcp landing."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn
from uuid import uuid4

from fastmcp.exceptions import ToolError

from kis_mcp.state import resolve_runtime_state_path

_SHA = re.compile(r"^[0-9a-f]{40}$")
_TARGET_PROJECT = "kis-mcp"
_TARGET_BRANCH = "main"
_TARGET_RUNTIME_INSTANCE = "kis-dev"
_RECEIPT_STATE_KEY = "post-land-restart"
_LOGGER = logging.getLogger(__name__)


def _receipt_root(state_root: Path) -> Path:
    return resolve_runtime_state_path(
        state_root,
        runtime_instance_id=_TARGET_RUNTIME_INSTANCE,
        state_key=_RECEIPT_STATE_KEY,
    )


def _write_schedule_failure_receipt(
    state_root: Path, landed_sha: str, detail: str
) -> None:
    try:
        receipt_root = _receipt_root(Path(state_root))
        receipt_root.mkdir(parents=True, exist_ok=True)
        receipt = receipt_root / "latest.json"
        temporary = receipt_root / f"latest.json.next-{uuid4().hex}"
        temporary.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "state": "failed",
                    "landed_sha": landed_sha,
                    "worker_pid": 0,
                    "detail": detail[:500],
                    "updated_utc": datetime.now(UTC).isoformat(),
                }
            ),
            encoding="utf-8",
        )
        temporary.replace(receipt)
    except Exception as exc:
        _LOGGER.error(
            "post-land restart failure evidence fallback: landed_sha=%s detail=%s error=%s",
            landed_sha[:80],
            detail[:300],
            type(exc).__name__,
        )
        return


def record_kis_dev_post_land_restart_failure(
    state_root: Path,
    landed_sha: str,
    detail: str,
) -> None:
    normalized_sha = str(landed_sha).strip().lower()
    if _SHA.fullmatch(normalized_sha) is None:
        normalized_sha = "unknown"
    _write_schedule_failure_receipt(Path(state_root), normalized_sha, detail)


def schedule_kis_dev_post_land_restart(
    project_id: str,
    local_root: Path,
    target_branch: str,
    landed_sha: str,
    *,
    state_root: Path,
) -> dict[str, Any]:
    if project_id != _TARGET_PROJECT or target_branch != _TARGET_BRANCH:
        return {"state": "not_applicable"}
    normalized_sha = str(landed_sha).strip().lower()
    if _SHA.fullmatch(normalized_sha) is None:
        raise ToolError("POST_LAND_RESTART_SHA_INVALID")
    root = Path(local_root)

    def fail(message: str, cause: BaseException | None = None) -> NoReturn:
        _write_schedule_failure_receipt(Path(state_root), normalized_sha, message)
        error = ToolError(message)
        if cause is None:
            raise error
        raise error from cause

    script_name = "restart-kis-dev-after-land.ps1"
    script = root / "scripts" / script_name
    if not script.is_file():
        source_script = Path(__file__).resolve().parents[2] / "scripts" / script_name
        script = source_script if source_script.is_file() else script
    if not script.is_file():
        fail("POST_LAND_RESTART_SCRIPT_MISSING")
    try:
        result = subprocess.run(
            [
                "pwsh.exe",
                "-NoProfile",
                "-File",
                str(script),
                "-ExpectedLandedSha",
                normalized_sha,
                "-RepositoryRoot",
                str(root),
                "-StateRoot",
                str(Path(state_root)),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError, UnicodeError) as exc:
        fail(f"POST_LAND_RESTART_SCHEDULE_FAILED: {type(exc).__name__}", exc)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[:500]
        fail(
            "POST_LAND_RESTART_SCHEDULE_FAILED"
            + (f": {detail}" if detail else "")
        )
    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        fail("POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE", exc)
    if (
        not isinstance(payload, dict)
        or set(payload) != {"state", "pid"}
        or payload.get("state") != "scheduled"
        or isinstance(payload.get("pid"), bool)
        or not isinstance(payload.get("pid"), int)
        or payload["pid"] <= 0
    ):
        fail("POST_LAND_RESTART_SCHEDULE_UNVERIFIABLE")
    return payload


def record_kis_dev_post_land_restart_exception(
    project_id: str,
    local_root: Path,
    target_branch: str,
    landed_sha: str | None,
    exc: BaseException,
    *,
    state_root: Path,
) -> None:
    del local_root
    if project_id != _TARGET_PROJECT or target_branch != _TARGET_BRANCH:
        return
    record_kis_dev_post_land_restart_failure(
        state_root,
        str(landed_sha or ""),
        f"POST_LAND_HOOK_UNEXPECTED: {type(exc).__name__}: {str(exc)[:400]}",
    )


__all__ = [
    "dispatch_kis_dev_post_land_restart",
    "record_kis_dev_post_land_restart_exception",
    "record_kis_dev_post_land_restart_failure",
    "schedule_kis_dev_post_land_restart",
]


def dispatch_kis_dev_post_land_restart(
    project_id: str,
    local_root: Path,
    target_branch: str,
    landed_sha: str | None,
    *,
    state_root: Path,
) -> None:
    if project_id != _TARGET_PROJECT or target_branch != _TARGET_BRANCH:
        return
    normalized_sha = str(landed_sha or "").strip().lower()
    if _SHA.fullmatch(normalized_sha) is None:
        record_kis_dev_post_land_restart_failure(
            state_root, "", "POST_LAND_LANDED_IDENTITY_UNVERIFIABLE"
        )
        return
    try:
        schedule_kis_dev_post_land_restart(
            project_id,
            local_root,
            target_branch,
            normalized_sha,
            state_root=state_root,
        )
    except ToolError:
        return
    except Exception as exc:
        record_kis_dev_post_land_restart_exception(
            project_id,
            local_root,
            target_branch,
            normalized_sha,
            exc,
            state_root=state_root,
        )
