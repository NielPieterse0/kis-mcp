from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from .contracts import EvidenceReference, EvidenceValidityClass, TaskHandoffContract
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
    raise ValueError("candidate tool result is not structured mapping output")


def register_once_through_tools(server: FastMCP, state_root: Path) -> None:
    store = TaskHandoffStore(state_root / "once-through")

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


__all__ = ["register_once_through_tools"]
