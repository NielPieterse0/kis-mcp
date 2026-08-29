"""Governed composition for merge queue operations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastmcp.exceptions import ToolError

from ..config import load_runtime_config
from ..projects.github_merge_queue import (
    RegisteredGitHubMergeQueueOperations,
    execute_registered_github_merge_queue_operation,
)
from ..projects.settings import load_project_registry_settings
from ..work_management import evaluate_merge_readiness
from .post_land import build_kis_post_land_hooks
from .project_management.parsing import (
    implementation_trace_from_json,
    work_record_from_json,
)


def _governance_receipt(
    project_id: str,
    pull_number: int,
    expected_head: str,
    record: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        parsed_record = work_record_from_json(dict(record))
        parsed_trace = implementation_trace_from_json(dict(trace))
    except Exception as exc:
        raise ToolError("MERGE_QUEUE_GOVERNANCE_EVIDENCE_INVALID") from exc

    if parsed_record.project_id != project_id or parsed_trace.project_id != project_id:
        raise ToolError("MERGE_QUEUE_GOVERNANCE_PROJECT_MISMATCH")

    matching = [item for item in parsed_trace.pull_requests if item.number == pull_number]
    if len(matching) != 1 or matching[0].head_revision != expected_head:
        raise ToolError("MERGE_QUEUE_GOVERNANCE_HEAD_MISMATCH")

    readiness = evaluate_merge_readiness(parsed_record, parsed_trace, pull_number)
    if not readiness.ready:
        reasons = ",".join(readiness.blocking_reasons)
        raise ToolError(f"MERGE_QUEUE_GOVERNANCE_NOT_READY: {reasons}")

    canonical = json.dumps(
        {"record": dict(record), "trace": dict(trace)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return {
        "ready": True,
        "record_id": parsed_record.record_id,
        "pull_number": pull_number,
        "head_sha": expected_head,
        "evidence_sha256": hashlib.sha256(canonical).hexdigest(),
        "advisories": list(readiness.advisories),
    }


def execute_governed_github_merge_queue_operation(
    operation: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = load_runtime_config()
    projects = load_project_registry_settings(boundary=runtime.project_boundary)
    service = RegisteredGitHubMergeQueueOperations(
        projects,
        gh_config_dir=Path(runtime.github_cli_config_dir),
        governance_validator=_governance_receipt,
        post_land_hooks=build_kis_post_land_hooks(runtime),
    )
    return execute_registered_github_merge_queue_operation(
        operation,
        arguments,
        operations=service,
    )


__all__ = ["execute_governed_github_merge_queue_operation"]
