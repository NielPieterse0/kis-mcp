from __future__ import annotations

import json
import msvcrt
import os
import socket
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from .contracts import (
    EvidenceReference,
    EvidenceValidityClass,
    PromotionReadyHandoff,
    TaskHandoffContract,
)

_PORT_START = 46000
_PORT_END = 60999


class OnceThroughStateError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(dict(payload), sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def assert_candidate_port_available(port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError as exc:
        raise OnceThroughStateError("CANDIDATE_PORT_OCCUPIED", f"assigned port {port} is occupied") from exc
    finally:
        sock.close()


class TaskHandoffStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.contracts = root / "contracts"
        self.promotions = root / "promotions"
        self.port_ledger = root / "candidate-ports.json"
        self.port_lock = root / "candidate-ports.lock"

    def _ledger(self) -> dict[str, int]:
        try:
            value = json.loads(self.port_ledger.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        if not isinstance(value, dict) or any(
            not isinstance(key, str) or type(port) is not int
            for key, port in value.items()
        ):
            raise OnceThroughStateError("CANDIDATE_PORT_LEDGER_INVALID", "candidate port ledger is invalid")
        return dict(value)

    def candidate_port(self, work_id: str) -> int:
        if not isinstance(work_id, str) or not work_id.strip():
            raise ValueError("work_id must be non-empty")
        with _exclusive_lock(self.port_lock):
            ledger = self._ledger()
            existing = ledger.get(work_id)
            if existing is not None:
                return existing
            used = set(ledger.values())
            selected = next(
                (port for port in range(_PORT_START, _PORT_END + 1) if port not in used),
                None,
            )
            if selected is None:
                raise OnceThroughStateError(
                    "CANDIDATE_PORT_EXHAUSTED", "candidate port range is exhausted"
                )
            ledger[work_id] = selected
            _write_json(self.port_ledger, ledger)
            return selected

    def contract_path(self, work_id: str) -> Path:
        safe = work_id.replace("/", "_").replace("\\", "_").replace(":", "_")
        return self.contracts / f"{safe}.json"

    def save_contract(self, contract: TaskHandoffContract) -> TaskHandoffContract:
        existing = self.load_contract(contract.work_id, required=False)
        if existing is not None:
            if existing.contract_fingerprint != contract.contract_fingerprint:
                raise OnceThroughStateError("HANDOFF_CONTRACT_IMMUTABLE", "task handoff contract already exists with different content")
            return existing
        _write_json(self.contract_path(contract.work_id), contract.to_json_dict())
        return contract

    def load_contract(self, work_id: str, *, required: bool = True) -> TaskHandoffContract | None:
        try:
            value = json.loads(self.contract_path(work_id).read_text(encoding="utf-8"))
        except FileNotFoundError:
            if required:
                raise OnceThroughStateError("HANDOFF_CONTRACT_MISSING", f"no task handoff exists for {work_id}")
            return None
        if not isinstance(value, dict):
            raise OnceThroughStateError("HANDOFF_CONTRACT_INVALID", "task handoff is not an object")
        contract = TaskHandoffContract(
            project_id=str(value.get("project_id", "")),
            work_id=str(value.get("work_id", "")),
            repository=str(value.get("repository", "")),
            requirements=tuple(value.get("requirements", ())),
            acceptance_criteria=tuple(value.get("acceptance_criteria", ())),
            affected_surfaces=tuple(value.get("affected_surfaces", ())),
            obligations=tuple(value.get("obligations", ())),
            candidate_port=value.get("candidate_port"),
            source_identity=str(value.get("source_identity", "")),
            change_id=value.get("change_id"),
        )
        if value.get("contract_fingerprint") != contract.contract_fingerprint:
            raise OnceThroughStateError("HANDOFF_CONTRACT_INVALID", "task handoff fingerprint mismatch")
        return contract

    def promotion_path(self, work_id: str) -> Path:
        safe = work_id.replace("/", "_").replace("\\", "_").replace(":", "_")
        return self.promotions / f"{safe}.json"

    def save_promotion(self, handoff: PromotionReadyHandoff) -> PromotionReadyHandoff:
        contract = self.load_contract(handoff.work_id)
        assert contract is not None
        if contract.contract_fingerprint != handoff.contract_fingerprint:
            raise OnceThroughStateError("PROMOTION_HANDOFF_INVALID", "contract fingerprint mismatch")
        _write_json(self.promotion_path(handoff.work_id), handoff.to_json_dict())
        return handoff

    def load_promotion(self, work_id: str) -> PromotionReadyHandoff:
        try:
            value = json.loads(self.promotion_path(work_id).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise OnceThroughStateError("PROMOTION_HANDOFF_MISSING", f"no PromotionReady handoff exists for {work_id}") from exc
        if not isinstance(value, dict):
            raise OnceThroughStateError("PROMOTION_HANDOFF_INVALID", "PromotionReady handoff is not an object")
        evidence = tuple(
            EvidenceReference(
                evidence_id=str(item.get("evidence_id", "")), kind=str(item.get("kind", "")),
                subject=str(item.get("subject", "")),
                validity_class=EvidenceValidityClass(str(item.get("validity_class", ""))),
                validity_inputs=dict(item.get("validity_inputs", {})),
                receipt_ref=str(item.get("receipt_ref", "")),
                applicable_phase=str(item.get("applicable_phase", "implementation")),
            )
            for item in value.get("evidence", ()) if isinstance(item, dict)
        )
        handoff = PromotionReadyHandoff(
            work_id=str(value.get("work_id", "")), change_id=str(value.get("change_id", "")),
            contract_fingerprint=str(value.get("contract_fingerprint", "")),
            source_commit_sha=str(value.get("source_commit_sha", "")),
            candidate_identity=dict(value.get("candidate_identity", {})),
            execution=dict(value.get("execution", {})), evidence=evidence,
            satisfied_obligations=tuple(value.get("satisfied_obligations", ())),
            pending_obligations=tuple(value.get("pending_obligations", ())),
            status=str(value.get("status", "")),
        )
        contract = self.load_contract(work_id)
        assert contract is not None
        if handoff.work_id != work_id or handoff.contract_fingerprint != contract.contract_fingerprint:
            raise OnceThroughStateError("PROMOTION_HANDOFF_INVALID", "PromotionReady identity mismatch")
        return handoff


__all__ = ["OnceThroughStateError", "TaskHandoffStore", "assert_candidate_port_available"]
