from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from ...mcp2026 import LONG_RUNNING_TASK_CONFIG
from ...state import resolve_runtime_state_path
from ...work_management import WorkManagementService
from .contracts import (
    EvidenceReference,
    EvidenceValidityClass,
    TaskHandoffContract,
    fingerprint,
)
from .controller import PromotionController, PromotionStateStore, build_terminal_receipt
from .process_identity import (
    WindowsProcessIdentity,
    read_process_identity,
    terminate_exact_process,
)
from .promotion import PromotionStageService
from .service import derive_promotion_ready
from .state import (
    OnceThroughStateError,
    TaskHandoffStore,
    assert_candidate_port_available,
)

_READ = {"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True, "open_world_hint": False}
_CHANGE = {"read_only_hint": False, "destructive_hint": False, "idempotent_hint": True, "open_world_hint": False}


def _post_land_restart_receipt(state_root: Path, expected_landed_sha: str) -> dict[str, Any]:
    receipt_path = resolve_runtime_state_path(
        state_root,
        runtime_instance_id="kis-dev",
        state_key="post-land-restart",
    ) / "latest.json"
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError("POST_LAND_RESTART_RECEIPT_MISSING") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("POST_LAND_RESTART_RECEIPT_INVALID") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RuntimeError("POST_LAND_RESTART_RECEIPT_INVALID")
    landed = str(payload.get("landed_sha", "")).strip().lower()
    expected = str(expected_landed_sha).strip().lower()
    if landed != expected:
        raise RuntimeError("POST_LAND_RESTART_RECEIPT_LANDED_MISMATCH")
    if payload.get("state") == "failed":
        raise RuntimeError("POST_LAND_RESTART_RECEIPT_FAILED")
    launched = str(payload.get("launched_sha", "")).strip().lower()
    if not launched:
        raise RuntimeError("POST_LAND_RESTART_RECEIPT_PENDING")
    if launched != expected:
        raise RuntimeError("POST_LAND_RESTART_RECEIPT_LAUNCHED_MISMATCH")
    return dict(payload)


def _reference(value: dict[str, Any]) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=str(value["evidence_id"]), kind=str(value["kind"]),
        subject=str(value["subject"]),
        validity_class=EvidenceValidityClass(str(value["validity_class"])),
        validity_inputs=dict(value.get("validity_inputs", {})),
        receipt_ref=str(value["receipt_ref"]),
        applicable_phase=str(value.get("applicable_phase", "implementation")),
    )


def _promotion_reference(
    stage: str,
    *,
    work_id: str,
    subject: str,
    result: dict[str, Any],
    observations: dict[str, Any],
) -> EvidenceReference | None:
    if result.get("status") not in {"passed", "satisfied", "applied"}:
        return None
    if stage == "exact_head_actions":
        head = str(result.get("head_sha", ""))
        reference = str(result.get("reference", ""))
        if not head or not reference:
            return None
        return EvidenceReference(
            evidence_id=f"provider-exact-head-{work_id}-{fingerprint(result)[:20]}",
            kind="provider_exact_head", subject=subject,
            validity_class=EvidenceValidityClass.PROVIDER_EXACT_HEAD,
            validity_inputs={"head": head, "provider": "github"},
            receipt_ref=reference, applicable_phase="pull_request",
        )
    if stage == "merge_exact_head":
        head = str(result.get("head_sha", ""))
        merge_sha = str(result.get("merge_commit_sha") or result.get("merge_commit") or "")
        if not head or not merge_sha:
            return None
        return EvidenceReference(
            evidence_id=f"merge-{work_id}-{fingerprint(result)[:20]}", kind="merge",
            subject=subject, validity_class=EvidenceValidityClass.PROVIDER_EXACT_HEAD,
            validity_inputs={"head": head, "provider": "github"},
            receipt_ref=f"merge:{merge_sha}", applicable_phase="pull_request",
        )
    if stage in {"refresh_landed", "documentation_reconcile", "work_done"}:
        landed = str(
            result.get("landed_sha") or result.get("completion_revision")
            or observations.get("refresh_landed", {}).get("landed_sha") or ""
        )
        if not landed:
            return None
        return EvidenceReference(
            evidence_id=f"{stage}-{work_id}-{fingerprint(result)[:20]}", kind=stage,
            subject=subject, validity_class=EvidenceValidityClass.POST_MERGE,
            validity_inputs={"landed": landed}, receipt_ref=f"promotion:{stage}:{fingerprint(result)[:24]}",
            applicable_phase="post_merge",
        )
    return None


def _candidate_matches(
    contract: TaskHandoffContract,
    receipt: dict[str, Any],
    identity: dict[str, Any] | None,
) -> bool:
    if identity is None:
        return False
    expected = {
        "work_id": contract.work_id,
        "contract_fingerprint": contract.contract_fingerprint,
        "source_identity": contract.source_identity,
        "source_path": receipt.get("source_path"),
        "change_id": receipt.get("change_id"),
        "server_instance_id": receipt.get("server_instance_id"),
        "pid": receipt.get("pid"),
    }
    return all(identity.get(key) == value for key, value in expected.items())


def _owned_candidate_stop_pid(
    contract: TaskHandoffContract,
    receipt: dict[str, Any],
    identity: dict[str, Any] | None,
    evidence: tuple[EvidenceReference, ...],
) -> tuple[int, EvidenceReference]:
    if not _candidate_matches(contract, receipt, identity):
        raise OnceThroughStateError(
            "CANDIDATE_OWNER_MISMATCH",
            "candidate endpoint does not prove ownership of the recorded PID/instance",
        )
    durable = tuple(
        item for item in evidence
        if item.kind == "live_candidate_verification"
        and item.validity_inputs.get("server_instance_id") == receipt.get("server_instance_id")
    )
    if len(durable) != 1:
        raise OnceThroughStateError(
            "CANDIDATE_EVIDENCE_NOT_DURABLE",
            "exact candidate cannot stop before its live proof is durably recorded",
        )
    pid = receipt.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise OnceThroughStateError("CANDIDATE_PID_INVALID", "recorded candidate PID is invalid")
    return pid, durable[0]


def _result_mapping(result: Any) -> dict[str, Any]:
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return dict(data)
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        value = structured.get("result", structured)
        if isinstance(value, dict):
            return dict(value)
    text = "\n".join(
        block_text
        for block in getattr(result, "content", ())
        if isinstance((block_text := getattr(block, "text", None)), str)
    ).strip()
    if text:
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            return decoded
    raise ValueError("tool result is not a structured mapping output")


def _project_field(item: Any, name: str) -> Any:
    target = name.casefold()
    for field in getattr(item, "field_values", ()):
        if getattr(field, "field_name", "").casefold() == target:
            return getattr(field, "value", None)
    return None


def _choice(value: Any, default: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return default
    return value.strip().casefold().replace(" ", "_").replace("-", "_")


def _risk_triggers(value: Any) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    return sorted({part.strip().casefold().replace("-", "_") for part in value.split(",") if part.strip()})


_RECORD_TYPE_PREFIX = {
    "idea": "IDEA", "task": "TASK", "specification_slice": "SPEC",
    "review_run": "REV", "finding": "FIND", "decision": "DEC",
    "assumption": "ASM", "risk": "RISK", "approval": "APP",
    "hold": "HOLD", "research": "RES", "defect": "BUG",
    "security_finding": "SEC",
}


def _typed_record_id(record_type: str, source_number: int) -> str:
    prefix = _RECORD_TYPE_PREFIX.get(record_type)
    if prefix is None:
        raise ValueError(f"WORK_RECORD_TYPE_UNSUPPORTED: {record_type}")
    return f"{prefix}-{source_number}"


def _governed_source_binding(
    contract: TaskHandoffContract,
    source_path: str,
) -> tuple[Path, str, dict[str, Any]]:
    source_root = Path(source_path).resolve()
    if source_root.parent.name != "worktrees" or source_root.parent.parent.name != ".work":
        raise OnceThroughStateError(
            "CANDIDATE_SOURCE_NOT_GOVERNED",
            "candidate source must be a governed .work/worktrees checkout",
        )
    change_id = source_root.name
    scope_path = source_root / ".work" / "changes" / change_id / "scope.json"
    try:
        scope = json.loads(scope_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OnceThroughStateError("CANDIDATE_SCOPE_INVALID", str(exc)) from exc
    if not isinstance(scope, dict) or scope.get("change_id") != change_id:
        raise OnceThroughStateError("CANDIDATE_SCOPE_INVALID", "change identity mismatch")
    work = scope.get("work_management")
    if not isinstance(work, dict) or work.get("record_id") != contract.work_id:
        raise OnceThroughStateError("CANDIDATE_SCOPE_INVALID", "Work identity mismatch")
    repository = str(work.get("source_repository") or contract.repository)
    if repository.casefold() != contract.repository.casefold():
        raise OnceThroughStateError("CANDIDATE_SCOPE_INVALID", "repository identity mismatch")
    if not (source_root / "src" / "kis_mcp").is_dir():
        raise OnceThroughStateError("CANDIDATE_SOURCE_INVALID", "source is not a KIS checkout")
    return source_root, change_id, scope


async def _resolve_work_record(
    service: WorkManagementService,
    contract: TaskHandoffContract,
    scope: dict[str, Any],
) -> dict[str, Any]:
    source = dict(scope.get("work_management") or {})
    number = source.get("source_number")
    repository = source.get("source_repository") or contract.repository
    source_work_id = source.get("record_id")
    if source_work_id != contract.work_id:
        raise ValueError("WORK_SOURCE_IDENTITY_MISMATCH: scope record_id must match the handoff Work ID")
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise ValueError("scope source_number is invalid")
    fields = ("Status", "Record Type", "Priority", "Effort", "Delivery Stage", "Execution Owner", "Documentation Impact", "Complexity", "Risk Triggers")
    inventory = await service.read_inventory(contract.project_id, field_names=fields, item_limit=1000)
    matches = [item for item in inventory.items if item.number == number and item.repository and item.repository.casefold() == str(repository).casefold()]
    if len(matches) != 1:
        raise ValueError(f"WORK_RECORD_UNRESOLVED: expected one Project item for {repository}#{number}")
    item = matches[0]
    record_type = _choice(_project_field(item, "Record Type"), "task")
    return {
        "schema_version": 1, "record_id": _typed_record_id(record_type, number), "project_id": contract.project_id,
        "title": item.title, "record_type": record_type,
        "state": _choice(_project_field(item, "Status"), "inbox"),
        "priority": _choice(_project_field(item, "Priority"), "medium"),
        "effort": _choice(_project_field(item, "Effort"), "medium"),
        "delivery_stage": _choice(_project_field(item, "Delivery Stage"), "none"),
        "execution_owner": _project_field(item, "Execution Owner"),
        "complexity": _choice(_project_field(item, "Complexity"), "medium"),
        "risk_triggers": _risk_triggers(_project_field(item, "Risk Triggers")),
        "documentation_mode": "required",
        "documentation_impact": _choice(_project_field(item, "Documentation Impact"), "not_assessed"),
        "traceability_required": True,
    }


def register_once_through_tools(
    server: FastMCP,
    state_root: Path,
    work_management_service: WorkManagementService | None = None,
) -> None:
    store = TaskHandoffStore(state_root / "once-through")
    promotion_state = PromotionStateStore(state_root / "once-through" / "promotion-controller")

    async def nested_invoker(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await server.call_tool(tool_name, arguments, run_middleware=True)
        if getattr(result, "is_error", False):
            detail = "\n".join(
                text for block in getattr(result, "content", ())
                if isinstance((text := getattr(block, "text", None)), str)
            ).strip()
            raise ToolError(detail or f"nested tool failed: {tool_name}")
        return _result_mapping(result)

    async def governed_cleanup(
        change_id: str, worktree: Path, landed_sha: str | None
    ) -> dict[str, Any]:
        if worktree.parent.name != "worktrees" or worktree.parent.parent.name != ".work":
            raise ValueError("CLEANUP_WORKTREE_IDENTITY_INVALID")
        repository = worktree.parent.parent.parent
        script = repository / "scripts" / "change-workflow.ps1"
        if not script.is_file():
            raise ValueError("CLEANUP_GOVERNANCE_SCRIPT_MISSING")
        completed = await asyncio.to_thread(
            subprocess.run,
            ["pwsh", "-NoProfile", "-File", str(script), "cleanup", change_id],
            cwd=repository,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "cleanup failed").strip()
            raise ValueError(f"PROMOTION_CLEANUP_FAILED: {detail}")
        result: dict[str, Any] = {
            "change_id": change_id,
            "removed": not worktree.exists(),
            "output": completed.stdout.strip(),
        }
        if landed_sha is not None:
            try:
                result["post_land_restart"] = _post_land_restart_receipt(state_root, landed_sha)
            except RuntimeError as exc:
                return {
                    "status": "blocked",
                    "reason": "post_land_restart_pending",
                    **result,
                    "post_land_restart_error": str(exc),
                }
        return result

    async def reconcile_governed_cleanup(
        change_id: str, worktree: Path, landed_sha: str | None
    ) -> dict[str, Any]:
        repository = worktree.parent.parent.parent
        script = repository / "scripts" / "change-workflow.ps1"
        completed = await asyncio.to_thread(
            subprocess.run,
            ["pwsh", "-NoProfile", "-File", str(script), "list"],
            cwd=repository,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0:
            return {"status": "blocked", "reason": "cleanup_reconciliation_failed"}
        try:
            records = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {"status": "blocked", "reason": "cleanup_reconciliation_invalid"}
        matches = [item for item in records if isinstance(item, dict) and item.get("change_id") == change_id]
        if len(matches) != 1 or matches[0].get("status") != "closed" or worktree.exists():
            return {"status": "blocked", "reason": "cleanup_not_authoritatively_closed"}
        result: dict[str, Any] = {
            "status": "applied",
            "change_id": change_id,
            "removed": True,
            "recovered": True,
        }
        if landed_sha is not None:
            try:
                result["post_land_restart"] = _post_land_restart_receipt(state_root, landed_sha)
            except RuntimeError as exc:
                return {
                    "status": "blocked",
                    "reason": "post_land_restart_pending",
                    **result,
                    "post_land_restart_error": str(exc),
                }
        return result

    async def read_candidate_identity(contract: TaskHandoffContract) -> dict[str, Any] | None:
        try:
            async with Client(
                f"http://127.0.0.1:{contract.candidate_port}/mcp",
                timeout=5,
                init_timeout=3,
            ) as client:
                return _result_mapping(await client.call_tool("candidate_identity", {}))
        except Exception:
            return None

    async def stop_owned_candidate(work_id: str) -> dict[str, Any]:
        contract = store.load_contract(work_id)
        assert contract is not None
        receipt = store.load_candidate(work_id, required=True)
        assert receipt is not None
        identity = await read_candidate_identity(contract)
        pid, durable = _owned_candidate_stop_pid(
            contract, receipt, identity, store.load_evidence(work_id)
        )
        raw_process = receipt.get("process_identity")
        if not isinstance(raw_process, dict):
            raise OnceThroughStateError(
                "CANDIDATE_PROCESS_IDENTITY_MISSING",
                "candidate receipt has no exact OS process identity",
            )
        expected_process = WindowsProcessIdentity(
            pid=pid,
            creation_time_100ns=int(raw_process.get("creation_time_100ns", 0)),
            image_path=str(raw_process.get("image_path", "")),
        )
        terminated = await asyncio.to_thread(terminate_exact_process, expected_process)
        stopped = {
            **receipt,
            "status": "stopped",
            "terminated": terminated,
            "stopped_after_evidence": durable.evidence_id,
        }
        store.save_candidate(work_id, stopped)
        return stopped

    @server.tool(name="candidate_identity", annotations=_READ)
    async def candidate_identity() -> dict[str, Any]:
        """Return exact task-candidate identity when this server is a candidate instance."""
        process_identity = await asyncio.to_thread(read_process_identity, os.getpid())
        return {
            "work_id": os.environ.get("KIS_MCP_CANDIDATE_WORK_ID"),
            "contract_fingerprint": os.environ.get("KIS_MCP_CANDIDATE_CONTRACT_FINGERPRINT"),
            "server_instance_id": os.environ.get("KIS_MCP_CANDIDATE_INSTANCE_ID"),
            "source_identity": os.environ.get("KIS_MCP_CANDIDATE_SOURCE_IDENTITY"),
            "source_path": os.environ.get("KIS_MCP_CANDIDATE_SOURCE_PATH"),
            "change_id": os.environ.get("KIS_MCP_CANDIDATE_CHANGE_ID"),
            "runtime_instance": os.environ.get("KIS_MCP_RUNTIME_INSTANCE", "stdio"),
            "pid": os.getpid(),
            "process_identity": (
                process_identity.to_json_dict() if process_identity is not None else None
            ),
        }

    @server.tool(name="materialize_task_handoff", annotations=_CHANGE)
    async def materialize_task_handoff(
        project_id: str, work_id: str, repository: str,
        requirements: list[str], acceptance_criteria: list[str],
        affected_surfaces: list[str], obligations: list[str],
        source_identity: str, change_id: str | None = None,
    ) -> dict[str, Any]:
        """Freeze one Work-ID-derived implementation handoff and permanent candidate endpoint."""
        try:
            contract = store.materialize_contract(
                project_id=project_id, work_id=work_id, repository=repository,
                requirements=tuple(requirements), acceptance_criteria=tuple(acceptance_criteria),
                affected_surfaces=tuple(affected_surfaces), obligations=tuple(obligations),
                source_identity=source_identity, change_id=change_id,
            )
            return contract.to_json_dict()
        except (ValueError, OnceThroughStateError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(name="get_task_handoff", annotations=_READ)
    async def get_task_handoff(work_id: str) -> dict[str, Any]:
        """Resolve a frozen implementation handoff by Work item identity."""
        try:
            contract = store.load_contract(work_id)
            assert contract is not None
            return contract.to_json_dict()
        except (ValueError, OnceThroughStateError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(name="candidate_endpoint_status", annotations=_READ)
    async def candidate_endpoint_status(work_id: str) -> dict[str, Any]:
        """Check whether the assigned candidate endpoint is available for its exact Work item."""
        try:
            contract = store.load_contract(work_id)
            assert contract is not None
            assert_candidate_port_available(contract.candidate_port)
            return {"status": "available", "work_id": work_id, "port": contract.candidate_port}
        except OnceThroughStateError as exc:
            return {"status": "blocked", "work_id": work_id, "code": exc.code, "reason": str(exc)}

    @server.tool(name="start_task_candidate", annotations=_CHANGE)
    async def start_task_candidate(work_id: str, source_path: str | None = None) -> dict[str, Any]:
        """Launch or reuse the exact owned localhost candidate for one Work identity."""
        try:
            contract = store.load_contract(work_id)
            assert contract is not None
            existing = store.load_candidate(work_id)
            if existing is not None and existing.get("status") != "stopped":
                identity = await read_candidate_identity(contract)
                if _candidate_matches(contract, existing, identity):
                    return {**existing, "status": "reused"}
            if not isinstance(source_path, str) or not source_path.strip():
                raise OnceThroughStateError(
                    "CANDIDATE_SOURCE_REQUIRED",
                    "first candidate start requires the governed change worktree path",
                )
            source_root, change_id, _scope = _governed_source_binding(contract, source_path)
            assert_candidate_port_available(contract.candidate_port)
            instance_id = uuid4().hex
            logs = state_root / "once-through" / "logs"
            logs.mkdir(parents=True, exist_ok=True)
            log_path = logs / f"{work_id.replace(':', '_')}-{instance_id}.log"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(source_root / "src") + os.pathsep + env.get("PYTHONPATH", "")
            command = [
                sys.executable, "-m", "kis_mcp.workflows.once_through.candidate_runtime",
                "--port", str(contract.candidate_port), "--work-id", work_id,
                "--contract-fingerprint", contract.contract_fingerprint,
                "--instance-id", instance_id,
                "--source-identity", contract.source_identity,
                "--source-path", str(source_root),
                "--change-id", change_id,
            ]
            stream = log_path.open("ab")
            try:
                process = await asyncio.to_thread(
                    subprocess.Popen,
                    command,
                    cwd=source_root,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
            finally:
                stream.close()
            process_identity = await asyncio.to_thread(read_process_identity, process.pid)
            if process_identity is None:
                raise OnceThroughStateError(
                    "CANDIDATE_PROCESS_IDENTITY_MISSING",
                    "candidate process exited before exact identity could be recorded",
                )
            receipt = {
                "status": "started",
                "work_id": work_id,
                "port": contract.candidate_port,
                "pid": process.pid,
                "server_instance_id": instance_id,
                "source_identity": contract.source_identity,
                "source_path": str(source_root),
                "change_id": change_id,
                "contract_fingerprint": contract.contract_fingerprint,
                "process_identity": process_identity.to_json_dict(),
                "log_path": str(log_path),
            }
            return store.save_candidate(work_id, receipt)
        except (ValueError, OSError, OnceThroughStateError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(name="verify_task_candidate", annotations=_READ)
    async def verify_task_candidate(work_id: str, scenarios: list[dict[str, Any]]) -> dict[str, Any]:
        """Exercise required scenarios through the real isolated MCP candidate transport."""
        try:
            contract = store.load_contract(work_id)
            assert contract is not None
            url = f"http://127.0.0.1:{contract.candidate_port}/mcp"
            async with Client(url, timeout=60, init_timeout=30) as client:
                identity = _result_mapping(await client.call_tool("candidate_identity", {}))
                expected = {"work_id": work_id, "contract_fingerprint": contract.contract_fingerprint, "source_identity": contract.source_identity}
                for key, value in expected.items():
                    if identity.get(key) != value:
                        raise OnceThroughStateError("CANDIDATE_IDENTITY_MISMATCH", f"candidate {key} does not match handoff")
                tools = {item.name: item for item in await client.list_tools()}
                outcomes: list[dict[str, Any]] = []
                for scenario in scenarios:
                    tool_name = str(scenario.get("tool", ""))
                    if tool_name not in tools:
                        raise OnceThroughStateError("CANDIDATE_SCENARIO_INVALID", f"unknown candidate tool: {tool_name}")
                    annotations = getattr(tools[tool_name], "annotations", None)
                    read_only = bool(getattr(annotations, "read_only_hint", False)) if annotations is not None else False
                    if not read_only and scenario.get("approved_effect_boundary") is not True:
                        raise OnceThroughStateError("CANDIDATE_EFFECT_BOUNDARY_REQUIRED", f"scenario {tool_name} is not read-only")
                    expect_error = scenario.get("expect_error") is True
                    try:
                        result = await client.call_tool(tool_name, dict(scenario.get("arguments", {})))
                        observed_error = bool(getattr(result, "is_error", False))
                    except Exception:
                        observed_error = True
                    if observed_error != expect_error:
                        raise OnceThroughStateError("LIVE_CANDIDATE_VERIFICATION_FAILED", f"scenario {tool_name} error expectation mismatched")
                    outcomes.append({"tool": tool_name, "status": "passed", "expected_error": expect_error})
            receipt = store.load_candidate(work_id, required=True)
            assert receipt is not None
            if not _candidate_matches(contract, receipt, identity):
                raise OnceThroughStateError("CANDIDATE_OWNER_MISMATCH", "verified endpoint is not the recorded candidate owner")
            source_root = Path(str(receipt.get("source_path", ""))).resolve()
            commit_result = await asyncio.to_thread(
                subprocess.run,
                ["git", "rev-parse", "HEAD"],
                cwd=source_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            tree_result = await asyncio.to_thread(
                subprocess.run,
                ["git", "rev-parse", "HEAD^{tree}"],
                cwd=source_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            commit = commit_result.stdout.strip().lower()
            tree = tree_result.stdout.strip().lower()
            evidence_id = f"live-candidate-{work_id}-{identity['server_instance_id']}-{commit[:12]}"
            reference = EvidenceReference(
                evidence_id=evidence_id,
                kind="live_candidate_verification",
                subject=contract.source_identity,
                validity_class=EvidenceValidityClass.RUNTIME_SENSITIVE,
                validity_inputs={
                    "tree": tree,
                    "runtime": str(identity["server_instance_id"]),
                    "source_commit": commit,
                    "server_instance_id": str(identity["server_instance_id"]),
                    "contract_fingerprint": contract.contract_fingerprint,
                },
                receipt_ref=f"candidate:{work_id}:{identity['server_instance_id']}",
            )
            store.append_evidence(work_id, reference)
            return {
                "contract": "live-candidate-verification-v1", "status": "passed",
                "work_id": work_id, "source_commit_sha": commit, "source_tree": tree,
                "candidate_identity": identity, "outcomes": outcomes,
                "evidence": reference.to_json_dict(),
            }
        except (ValueError, OSError, subprocess.SubprocessError, OnceThroughStateError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(name="stop_task_candidate", annotations=_CHANGE)
    async def stop_task_candidate(work_id: str) -> dict[str, Any]:
        """Stop only the exact owned candidate after its live evidence is durable."""
        try:
            return await stop_owned_candidate(work_id)
        except (ValueError, OSError, OnceThroughStateError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(name="derive_promotion_ready", annotations=_CHANGE)
    async def derive_promotion_ready_tool(work_id: str) -> dict[str, Any]:
        """Derive PromotionReady only from governed source and canonical execution evidence."""
        try:
            contract = store.load_contract(work_id)
            assert contract is not None
            try:
                existing_promotion = store.load_promotion(work_id)
            except OnceThroughStateError as exc:
                if exc.code != "PROMOTION_HANDOFF_MISSING":
                    raise
            else:
                return existing_promotion.to_json_dict()
            if work_management_service is None:
                raise ValueError(
                    "WORK_MANAGEMENT_UNAVAILABLE: PromotionReady requires Work authority"
                )
            receipt = store.load_candidate(work_id, required=True)
            assert receipt is not None
            source_path = receipt.get("source_path")
            if not isinstance(source_path, str) or not source_path.strip():
                raise OnceThroughStateError(
                    "CANDIDATE_SOURCE_INVALID", "candidate source binding is missing"
                )
            source_root, change_id, scope = _governed_source_binding(contract, source_path)
            if receipt.get("change_id") != change_id:
                raise OnceThroughStateError(
                    "CANDIDATE_SCOPE_INVALID", "candidate change binding mismatch"
                )
            identity = await read_candidate_identity(contract)
            if not _candidate_matches(contract, receipt, identity):
                raise OnceThroughStateError(
                    "CANDIDATE_OWNER_MISMATCH",
                    "live candidate does not match the persisted governed binding",
                )
            references = store.load_evidence(work_id)
            live_matches = tuple(
                item for item in references
                if item.kind == "live_candidate_verification"
                and item.validity_inputs.get("server_instance_id")
                == receipt.get("server_instance_id")
            )
            if len(live_matches) != 1:
                raise ValueError(
                    "PROMOTION_NOT_READY: exact live-candidate evidence is required"
                )
            live = live_matches[0]
            source_commit = live.validity_inputs.get("source_commit", "")
            tree = live.validity_inputs.get("tree", "")
            if len(source_commit) != 40 or not tree:
                raise ValueError("PROMOTION_NOT_READY: live source identity is incomplete")
            record = await _resolve_work_record(work_management_service, contract, scope)
            execution = await nested_invoker(
                "execute_change_workflow",
                {
                    "project": str(source_root),
                    "source": "commit",
                    "commit_ref": source_commit,
                    "complexity": record["complexity"],
                    "risk_triggers": list(record["risk_triggers"]),
                },
            )
            if execution.get("contract") != "change-execution-result-v2":
                raise ValueError("PROMOTION_NOT_READY: execution contract is invalid")
            if execution.get("status") != "passed":
                raise ValueError("PROMOTION_NOT_READY: canonical execution has not passed")
            execution_receipt = {
                "work_id": work_id,
                "change_id": change_id,
                "source_path": str(source_root),
                "source_commit_sha": source_commit,
                "source_tree": tree,
                "contract_fingerprint": contract.contract_fingerprint,
                "execution": execution,
            }
            stored_execution = store.save_execution(work_id, execution_receipt)
            execution_ref = fingerprint(stored_execution)[:24]
            current_kinds = {item.kind for item in references}
            if "verification" not in current_kinds:
                store.append_evidence(
                    work_id,
                    EvidenceReference(
                        evidence_id=f"verification-{work_id}-{execution_ref}",
                        kind="verification",
                        subject=contract.source_identity,
                        validity_class=EvidenceValidityClass.CONTENT_STABLE,
                        validity_inputs={"tree": tree},
                        receipt_ref=f"execution-receipt:{execution_ref}",
                    ),
                )
            material_findings = []
            for review in execution.get("reviews", ()):
                if not isinstance(review, dict) or review.get("status") != "completed":
                    raise ValueError("PROMOTION_NOT_READY: specialist review is incomplete")
                payload = review.get("payload")
                if isinstance(payload, dict):
                    for finding in payload.get("findings", ()):
                        if isinstance(finding, dict) and str(
                            finding.get("severity", "")
                        ).casefold() in {"critical", "high", "medium"}:
                            material_findings.append(finding)
            if material_findings:
                raise ValueError("PROMOTION_NOT_READY: material review findings remain")
            if "review_closed" not in current_kinds:
                store.append_evidence(
                    work_id,
                    EvidenceReference(
                        evidence_id=f"review-closed-{work_id}-{execution_ref}",
                        kind="review_closed",
                        subject=contract.source_identity,
                        validity_class=EvidenceValidityClass.CONTENT_STABLE,
                        validity_inputs={"tree": tree},
                        receipt_ref=f"execution-receipt:{execution_ref}",
                    ),
                )
            references = store.load_evidence(work_id)
            observed = {
                "tree": tree,
                "runtime": live.validity_inputs["runtime"],
                "source_commit": source_commit,
                "server_instance_id": live.validity_inputs["server_instance_id"],
                "contract_fingerprint": contract.contract_fingerprint,
            }
            handoff = derive_promotion_ready(
                contract,
                source_commit_sha=source_commit,
                execution=execution,
                evidence=references,
                observed_inputs=observed,
                candidate_identity=dict(identity or {}),
                change_id=change_id,
            )
            store.save_promotion(handoff)
            payload = handoff.to_json_dict()
            payload["candidate_cleanup"] = await stop_owned_candidate(work_id)
            return payload
        except (KeyError, ValueError, OSError, OnceThroughStateError, ToolError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(
        name="converge_change_to_done",
        annotations=_CHANGE,
        task=LONG_RUNNING_TASK_CONFIG,
    )
    async def converge_change_to_done(work_id: str, approved: bool) -> dict[str, Any]:
        """Converge one persisted PromotionReady Work item through governed promotion to Done."""
        try:
            if approved is not True:
                raise ValueError("APPROVAL_REQUIRED: approved must be true")
            contract = store.load_contract(work_id)
            assert contract is not None
            handoff = store.load_promotion(work_id).to_json_dict()
            operation_id = "promotion-" + fingerprint({
                "work_id": work_id,
                "contract_fingerprint": handoff["contract_fingerprint"],
                "source_commit_sha": handoff["source_commit_sha"],
            })[:32]
            checkpoint = promotion_state.load(operation_id)
            if checkpoint is not None and (
                checkpoint.get("state") == "done"
                or len(checkpoint.get("completed", ())) == 10
            ):
                observations = dict(checkpoint.get("observations", {}))
                terminal_receipt = checkpoint.get("terminal_receipt")
                if not isinstance(terminal_receipt, dict):
                    if contract.project_id == "kis-mcp":
                        landed_observation = observations.get("refresh_landed")
                        landed_sha = (
                            str(landed_observation.get("landed_sha", "")).strip().lower()
                            if isinstance(landed_observation, dict)
                            else ""
                        )
                        cleanup_observation = observations.get("cleanup")
                        cleanup = (
                            dict(cleanup_observation)
                            if isinstance(cleanup_observation, dict)
                            else {}
                        )
                        cleanup["post_land_restart"] = _post_land_restart_receipt(
                            state_root, landed_sha
                        )
                        observations["cleanup"] = cleanup
                    terminal_receipt = build_terminal_receipt(
                        operation_id, handoff, observations
                    )
                    checkpoint = {
                        **checkpoint,
                        "state": "done",
                        "current_stage": None,
                        "observations": observations,
                        "terminal_receipt": terminal_receipt,
                    }
                    promotion_state.save(operation_id, checkpoint)
                return {
                    "contract": "promotion-execution-v1",
                    "operation_id": operation_id,
                    "completed": list(checkpoint.get("completed", ())),
                    "current_stage": None,
                    "state": "done",
                    "observations": observations,
                    "terminal_receipt": dict(terminal_receipt),
                }
            candidate_receipt = store.load_candidate(work_id, required=True)
            assert candidate_receipt is not None
            source_path = candidate_receipt.get("source_path")
            if not isinstance(source_path, str) or not source_path.strip():
                raise ValueError("PROMOTION_SOURCE_PATH_MISSING: candidate source path is unavailable")
            source_root = Path(source_path).resolve()
            completed_prefix = list(checkpoint.get("completed", ())) if checkpoint is not None else []
            change_id = str(handoff.get("change_id") or contract.change_id or "")
            if not change_id:
                raise ValueError("PROMOTION_CHANGE_ID_MISSING: PromotionReady change identity is unavailable")
            if checkpoint is not None and len(completed_prefix) == 9 and not source_root.exists():
                cleanup_observations = dict(checkpoint.get("observations", {}))
                landed_observation = cleanup_observations.get("refresh_landed")
                landed_sha = (
                    str(landed_observation.get("landed_sha", "")).strip().lower()
                    if isinstance(landed_observation, dict)
                    else ""
                )
                restart_landed_sha = landed_sha if contract.project_id == "kis-mcp" else None
                cleanup_state = await reconcile_governed_cleanup(
                    change_id, source_root, restart_landed_sha
                )
                observations = dict(checkpoint.get("observations", {}))
                observations["cleanup"] = cleanup_state
                if cleanup_state.get("status") != "applied":
                    return {
                        "contract": "promotion-execution-v1", "operation_id": operation_id,
                        "completed": completed_prefix, "current_stage": "cleanup",
                        "state": "blocked", "observations": observations,
                    }
                terminal_receipt = build_terminal_receipt(operation_id, handoff, observations)
                recovered = {
                    "contract": "promotion-execution-v1", "operation_id": operation_id,
                    "completed": completed_prefix + ["cleanup"], "current_stage": None,
                    "state": "done", "observations": observations,
                    "terminal_receipt": terminal_receipt,
                    "handoff_fingerprint": checkpoint.get("handoff_fingerprint"),
                }
                promotion_state.save(operation_id, recovered)
                return {key: value for key, value in recovered.items() if key != "handoff_fingerprint"}
            if work_management_service is None:
                raise ValueError("WORK_MANAGEMENT_UNAVAILABLE: convergence requires configured Work Management")
            scope_path = source_root / ".work" / "changes" / change_id / "scope.json"
            scope = json.loads(scope_path.read_text(encoding="utf-8"))
            if not isinstance(scope, dict) or scope.get("change_id") != change_id:
                raise ValueError("PROMOTION_SCOPE_INVALID: governed change scope is unavailable or mismatched")
            record = await _resolve_work_record(work_management_service, contract, scope)
            service = PromotionStageService(
                invoker=nested_invoker,
                contract=contract,
                scope=scope,
                work_record=record,
                approved=True,
                cleanup=governed_cleanup,
                change_id=change_id,
                source_root=source_root,
            )
            async def invoke_and_record(
                stage: str, promotion_handoff: dict[str, Any], observations: dict[str, Any]
            ) -> dict[str, Any]:
                stage_result = await service.invoke(stage, promotion_handoff, observations)
                reference = _promotion_reference(
                    stage,
                    work_id=work_id,
                    subject=contract.source_identity,
                    result=stage_result,
                    observations=observations,
                )
                if reference is not None:
                    store.append_evidence(work_id, reference)
                return stage_result

            result = await PromotionController(invoke_and_record, promotion_state).converge(
                operation_id=operation_id,
                promotion_handoff=handoff,
            )
            return result.to_json_dict()
        except (KeyError, OSError, TypeError, json.JSONDecodeError, ValueError, OnceThroughStateError, ToolError) as exc:
            raise ToolError(str(exc)) from exc


__all__ = ["register_once_through_tools"]
