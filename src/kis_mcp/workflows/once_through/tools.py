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
from ...work_management import WorkManagementService
from .contracts import EvidenceReference, EvidenceValidityClass, TaskHandoffContract, fingerprint
from .controller import PromotionController, PromotionStateStore
from .promotion import PromotionStageService
from .service import derive_promotion_ready
from .state import OnceThroughStateError, TaskHandoffStore, assert_candidate_port_available

_READ = {"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True, "open_world_hint": False}
_CHANGE = {"read_only_hint": False, "destructive_hint": False, "idempotent_hint": True, "open_world_hint": False}


def _reference(value: dict[str, Any]) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=str(value["evidence_id"]), kind=str(value["kind"]),
        subject=str(value["subject"]),
        validity_class=EvidenceValidityClass(str(value["validity_class"])),
        validity_inputs=dict(value.get("validity_inputs", {})),
        receipt_ref=str(value["receipt_ref"]),
        applicable_phase=str(value.get("applicable_phase", "implementation")),
    )


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

    async def governed_cleanup(change_id: str, worktree: Path) -> dict[str, Any]:
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
        return {"change_id": change_id, "removed": not worktree.exists(), "output": completed.stdout.strip()}

    async def reconcile_governed_cleanup(change_id: str, worktree: Path) -> dict[str, Any]:
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
        return {"status": "applied", "change_id": change_id, "removed": True, "recovered": True}

    @server.tool(name="candidate_identity", annotations=_READ)
    async def candidate_identity() -> dict[str, Any]:
        """Return exact task-candidate identity when this server is a candidate instance."""
        return {
            "work_id": os.environ.get("KIS_MCP_CANDIDATE_WORK_ID"),
            "contract_fingerprint": os.environ.get("KIS_MCP_CANDIDATE_CONTRACT_FINGERPRINT"),
            "server_instance_id": os.environ.get("KIS_MCP_CANDIDATE_INSTANCE_ID"),
            "source_identity": os.environ.get("KIS_MCP_CANDIDATE_SOURCE_IDENTITY"),
            "runtime_instance": os.environ.get("KIS_MCP_RUNTIME_INSTANCE", "stdio"),
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
            port = store.candidate_port(work_id)
            contract = TaskHandoffContract(
                project_id=project_id, work_id=work_id, repository=repository,
                requirements=tuple(requirements), acceptance_criteria=tuple(acceptance_criteria),
                affected_surfaces=tuple(affected_surfaces), obligations=tuple(obligations),
                candidate_port=port, source_identity=source_identity, change_id=change_id,
            )
            return store.save_contract(contract).to_json_dict()
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
    async def start_task_candidate(work_id: str) -> dict[str, Any]:
        """Launch the exact task source as an isolated localhost MCP candidate."""
        try:
            contract = store.load_contract(work_id)
            assert contract is not None
            source_root = Path(contract.source_identity).resolve()
            if not (source_root / "src" / "kis_mcp").is_dir():
                raise OnceThroughStateError("CANDIDATE_SOURCE_INVALID", "handoff source_identity is not a KIS source checkout")
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
                "--instance-id", instance_id, "--source-identity", contract.source_identity,
            ]
            stream = log_path.open("ab")
            process = subprocess.Popen(command, cwd=source_root, env=env, stdout=stream, stderr=subprocess.STDOUT)
            stream.close()
            receipt = {"status": "started", "work_id": work_id, "port": contract.candidate_port, "pid": process.pid, "server_instance_id": instance_id, "source_identity": contract.source_identity, "contract_fingerprint": contract.contract_fingerprint, "log_path": str(log_path)}
            runtime_path = state_root / "once-through" / "candidates" / f"{work_id.replace(':', '_')}.json"
            runtime_path.parent.mkdir(parents=True, exist_ok=True)
            runtime_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
            return receipt
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
            return {"contract": "live-candidate-verification-v1", "status": "passed", "work_id": work_id, "candidate_identity": identity, "outcomes": outcomes}
        except (ValueError, OSError, OnceThroughStateError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool(name="derive_promotion_ready", annotations=_READ)
    async def derive_promotion_ready_tool(
        work_id: str, source_commit_sha: str, execution: dict[str, Any],
        evidence: list[dict[str, Any]], observed_inputs: dict[str, str],
        candidate_identity: dict[str, Any],
    ) -> dict[str, Any]:
        """Derive PROMOTION_READY from the frozen task contract and existing evidence only."""
        try:
            contract = store.load_contract(work_id)
            assert contract is not None
            handoff = derive_promotion_ready(
                contract, source_commit_sha=source_commit_sha, execution=execution,
                evidence=tuple(_reference(item) for item in evidence),
                observed_inputs=observed_inputs, candidate_identity=candidate_identity,
            )
            store.save_promotion(handoff)
            return handoff.to_json_dict()
        except (KeyError, ValueError, OnceThroughStateError) as exc:
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
                return {
                    "contract": "promotion-execution-v1",
                    "operation_id": operation_id,
                    "completed": list(checkpoint.get("completed", ())),
                    "current_stage": None,
                    "state": "done",
                    "observations": dict(checkpoint.get("observations", {})),
                }
            source_root = Path(contract.source_identity).resolve()
            completed_prefix = list(checkpoint.get("completed", ())) if checkpoint is not None else []
            if checkpoint is not None and len(completed_prefix) == 9 and not source_root.exists():
                cleanup_state = await reconcile_governed_cleanup(str(contract.change_id or ""), source_root)
                observations = dict(checkpoint.get("observations", {}))
                observations["cleanup"] = cleanup_state
                if cleanup_state.get("status") != "applied":
                    return {
                        "contract": "promotion-execution-v1", "operation_id": operation_id,
                        "completed": completed_prefix, "current_stage": "cleanup",
                        "state": "blocked", "observations": observations,
                    }
                recovered = {
                    "contract": "promotion-execution-v1", "operation_id": operation_id,
                    "completed": completed_prefix + ["cleanup"], "current_stage": None,
                    "state": "done", "observations": observations,
                    "handoff_fingerprint": checkpoint.get("handoff_fingerprint"),
                }
                promotion_state.save(operation_id, recovered)
                return {key: value for key, value in recovered.items() if key != "handoff_fingerprint"}
            if work_management_service is None:
                raise ValueError("WORK_MANAGEMENT_UNAVAILABLE: convergence requires configured Work Management")
            source_root = Path(contract.source_identity).resolve()
            change_id = str(contract.change_id or "")
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
            )
            result = await PromotionController(service.invoke, promotion_state).converge(
                operation_id=operation_id,
                promotion_handoff=handoff,
            )
            return result.to_json_dict()
        except (KeyError, OSError, TypeError, json.JSONDecodeError, ValueError, OnceThroughStateError, ToolError) as exc:
            raise ToolError(str(exc)) from exc


__all__ = ["register_once_through_tools"]
