from __future__ import annotations

import json
import msvcrt
import os
import re
import socket
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import (
    LEGACY_SCHEMA_VERSION,
    EvidenceReference,
    EvidenceValidityClass,
    PromotionReadyHandoff,
    TaskHandoffContract,
)

_PORT_START = 46000
_PORT_END = 60999
_WORK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class OnceThroughStateError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
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
        self.evidence = root / "evidence"
        self.candidates = root / "candidates"
        self.executions = root / "executions"
        self.manual_exits = root / "manual-exits"
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
        self._safe_work_id(work_id)
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

    @staticmethod
    def _safe_work_id(work_id: str) -> str:
        if not isinstance(work_id, str) or _WORK_ID_RE.fullmatch(work_id) is None:
            raise ValueError("work_id must use canonical letters/digits/._- form")
        return work_id

    def contract_path(self, work_id: str) -> Path:
        return self.contracts / f"{self._safe_work_id(work_id)}.json"

    def materialize_contract(
        self,
        *,
        project_id: str,
        work_id: str,
        repository: str,
        requirements: tuple[str, ...],
        acceptance_criteria: tuple[str, ...],
        affected_surfaces: tuple[str, ...],
        obligations: tuple[str, ...],
        source_identity: str,
        change_id: str | None = None,
    ) -> TaskHandoffContract:
        self._safe_work_id(work_id)
        with _exclusive_lock(self.port_lock):
            existing = self.load_contract(work_id, required=False)
            ledger = self._ledger()
            port = ledger.get(work_id)
            if port is None:
                used = set(ledger.values())
                port = next((candidate for candidate in range(_PORT_START, _PORT_END + 1) if candidate not in used), None)
                if port is None:
                    raise OnceThroughStateError("CANDIDATE_PORT_EXHAUSTED", "candidate port range is exhausted")
            contract = TaskHandoffContract(
                project_id=project_id,
                work_id=work_id,
                repository=repository,
                requirements=requirements,
                acceptance_criteria=acceptance_criteria,
                affected_surfaces=affected_surfaces,
                obligations=obligations,
                candidate_port=port,
                source_identity=source_identity,
                change_id=change_id,
            )
            if existing is not None:
                if existing.contract_fingerprint != contract.contract_fingerprint:
                    raise OnceThroughStateError(
                        "HANDOFF_CONTRACT_IMMUTABLE",
                        "task handoff contract already exists with different content",
                    )
                return existing
            if work_id not in ledger:
                ledger[work_id] = port
                _write_json(self.port_ledger, ledger)
            _write_json(self.contract_path(work_id), contract.to_json_dict())
            return contract

    def save_contract(self, contract: TaskHandoffContract) -> TaskHandoffContract:
        existing = self.load_contract(contract.work_id, required=False)
        if existing is not None:
            if existing.contract_fingerprint != contract.contract_fingerprint:
                raise OnceThroughStateError("HANDOFF_CONTRACT_IMMUTABLE", "task handoff contract already exists with different content")
            return existing
        _write_json(self.contract_path(contract.work_id), contract.to_json_dict())
        return contract

    def bind_change_id(self, work_id: str, change_id: str) -> TaskHandoffContract:
        """Bind an unbound handoff to one governed change exactly once."""
        self._safe_work_id(work_id)
        if not isinstance(change_id, str) or not change_id.strip():
            raise ValueError("change_id must be non-empty")
        normalized = change_id.strip()
        with _exclusive_lock(self.port_lock):
            existing = self.load_contract(work_id)
            assert existing is not None
            if existing.change_id is not None:
                if existing.change_id == normalized:
                    return existing
                raise OnceThroughStateError(
                    "HANDOFF_CONTRACT_IMMUTABLE",
                    "task handoff change_id is already bound to a different governed change",
                )
            if self.promotion_path(work_id).exists() or self.candidate_path(work_id).exists():
                raise OnceThroughStateError(
                    "HANDOFF_CHANGE_BIND_TOO_LATE",
                    "task handoff cannot bind change_id after candidate or promotion identity exists",
                )
            bound = replace(existing, change_id=normalized)
            _write_json(self.contract_path(work_id), bound.to_json_dict())
            return bound

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
            schema_version=int(value.get("schema_version", LEGACY_SCHEMA_VERSION)),
        )
        if value.get("contract_fingerprint") != contract.contract_fingerprint:
            raise OnceThroughStateError("HANDOFF_CONTRACT_INVALID", "task handoff fingerprint mismatch")
        return contract

    def evidence_path(self, work_id: str) -> Path:
        return self.evidence / f"{self._safe_work_id(work_id)}.json"

    def evidence_lock_path(self, work_id: str) -> Path:
        return self.evidence / f"{self._safe_work_id(work_id)}.lock"

    def load_evidence(self, work_id: str) -> tuple[EvidenceReference, ...]:
        try:
            value = json.loads(self.evidence_path(work_id).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return ()
        if not isinstance(value, list):
            raise OnceThroughStateError("EVIDENCE_LINEAGE_INVALID", "evidence lineage is not a list")
        try:
            return tuple(
                EvidenceReference(
                    evidence_id=str(item["evidence_id"]),
                    kind=str(item["kind"]),
                    subject=str(item["subject"]),
                    validity_class=EvidenceValidityClass(str(item["validity_class"])),
                    validity_inputs=dict(item.get("validity_inputs", {})),
                    receipt_ref=str(item["receipt_ref"]),
                    applicable_phase=str(item.get("applicable_phase", "implementation")),
                )
                for item in value
                if isinstance(item, dict)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise OnceThroughStateError("EVIDENCE_LINEAGE_INVALID", str(exc)) from exc

    def append_evidence(self, work_id: str, reference: EvidenceReference) -> tuple[EvidenceReference, ...]:
        contract = self.load_contract(work_id)
        assert contract is not None
        with _exclusive_lock(self.evidence_lock_path(work_id)):
            existing = list(self.load_evidence(work_id))
            matches = [item for item in existing if item.evidence_id == reference.evidence_id]
            if matches:
                if matches[0] != reference:
                    raise OnceThroughStateError(
                        "EVIDENCE_ID_IMMUTABLE", f"evidence {reference.evidence_id} already has different content"
                    )
                return tuple(existing)
            existing.append(reference)
            _write_json(self.evidence_path(work_id), [item.to_json_dict() for item in existing])
            return tuple(existing)

    def manual_exit_path(self, work_id: str) -> Path:
        return self.manual_exits / f"{self._safe_work_id(work_id)}.json"

    def save_manual_exit(self, work_id: str) -> dict[str, Any]:
        contract = self.load_contract(work_id)
        assert contract is not None
        existing = self.load_manual_exit(work_id, required=False)
        if existing is not None:
            if existing.get("contract_fingerprint") != contract.contract_fingerprint:
                raise OnceThroughStateError(
                    "ONCE_THROUGH_EXIT_INVALID",
                    "once-through exit contract fingerprint no longer matches the handoff",
                )
            return existing
        evidence = self.load_evidence(work_id)
        payload = {
            "schema_version": 1,
            "status": "manual_closeout",
            "work_id": work_id,
            "change_id": contract.change_id,
            "contract_fingerprint": contract.contract_fingerprint,
            "retained_evidence_ids": [item.evidence_id for item in evidence],
            "retained_evidence_count": len(evidence),
        }
        _write_json(self.manual_exit_path(work_id), payload)
        return payload

    def load_manual_exit(self, work_id: str, *, required: bool = False) -> dict[str, Any] | None:
        try:
            value = json.loads(self.manual_exit_path(work_id).read_text(encoding="utf-8"))
        except FileNotFoundError:
            if required:
                raise OnceThroughStateError("ONCE_THROUGH_EXIT_MISSING", f"no once-through exit exists for {work_id}")
            return None
        if not isinstance(value, dict) or value.get("work_id") != work_id or value.get("status") != "manual_closeout":
            raise OnceThroughStateError("ONCE_THROUGH_EXIT_INVALID", "once-through exit receipt is invalid")
        return dict(value)

    def candidate_path(self, work_id: str) -> Path:
        return self.candidates / f"{self._safe_work_id(work_id)}.json"

    def save_candidate(self, work_id: str, receipt: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(receipt)
        _write_json(self.candidate_path(work_id), payload)
        return payload

    def load_candidate(self, work_id: str, *, required: bool = False) -> dict[str, Any] | None:
        try:
            value = json.loads(self.candidate_path(work_id).read_text(encoding="utf-8"))
        except FileNotFoundError:
            if required:
                raise OnceThroughStateError("CANDIDATE_RUNTIME_MISSING", f"no candidate runtime exists for {work_id}")
            return None
        if not isinstance(value, dict):
            raise OnceThroughStateError("CANDIDATE_RUNTIME_INVALID", "candidate runtime receipt is not an object")
        if value.get("work_id") != work_id:
            raise OnceThroughStateError("CANDIDATE_RUNTIME_INVALID", "candidate Work identity mismatch")
        return dict(value)

    def execution_path(self, work_id: str) -> Path:
        return self.executions / f"{self._safe_work_id(work_id)}.json"

    def save_execution(self, work_id: str, receipt: Mapping[str, Any]) -> dict[str, Any]:
        self.load_contract(work_id)
        payload = dict(receipt)
        if payload.get("work_id") != work_id:
            raise OnceThroughStateError("EXECUTION_RECEIPT_INVALID", "execution Work identity mismatch")
        existing = self.load_execution(work_id, required=False)
        if existing is not None:
            if existing != payload:
                raise OnceThroughStateError(
                    "EXECUTION_RECEIPT_IMMUTABLE",
                    "execution receipt already exists with different content",
                )
            return existing
        _write_json(self.execution_path(work_id), payload)
        return payload

    def load_execution(self, work_id: str, *, required: bool = False) -> dict[str, Any] | None:
        try:
            value = json.loads(self.execution_path(work_id).read_text(encoding="utf-8"))
        except FileNotFoundError:
            if required:
                raise OnceThroughStateError("EXECUTION_RECEIPT_MISSING", f"no execution receipt exists for {work_id}")
            return None
        if not isinstance(value, dict) or value.get("work_id") != work_id:
            raise OnceThroughStateError("EXECUTION_RECEIPT_INVALID", "execution receipt identity mismatch")
        return dict(value)

    def promotion_path(self, work_id: str) -> Path:
        return self.promotions / f"{self._safe_work_id(work_id)}.json"

    @staticmethod
    def promotion_lookup_key(change_id: str, source_commit_sha: str) -> str:
        if not isinstance(change_id, str) or not change_id.strip() or ":" in change_id:
            raise ValueError("change_id is invalid for PromotionReady lookup")
        if not isinstance(source_commit_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit_sha):
            raise ValueError("source_commit_sha is invalid for PromotionReady lookup")
        return f"@change:{change_id}:{source_commit_sha}"

    def save_promotion(self, handoff: PromotionReadyHandoff) -> PromotionReadyHandoff:
        contract = self.load_contract(handoff.work_id)
        assert contract is not None
        if contract.contract_fingerprint != handoff.contract_fingerprint:
            raise OnceThroughStateError("PROMOTION_HANDOFF_INVALID", "contract fingerprint mismatch")
        _write_json(self.promotion_path(handoff.work_id), handoff.to_json_dict())
        return handoff

    def load_promotion(self, work_id: str) -> PromotionReadyHandoff:
        if work_id.startswith("@change:"):
            parts = work_id.split(":", 2)
            if len(parts) != 3:
                raise OnceThroughStateError("PROMOTION_LOOKUP_INVALID", "PromotionReady lookup identity is invalid")
            return self.resolve_promotion(parts[1], parts[2])
        return self._load_promotion_exact(work_id)

    def resolve_promotion(self, change_id: str, source_commit_sha: str) -> PromotionReadyHandoff:
        lookup = self.promotion_lookup_key(change_id, source_commit_sha)
        matches: list[PromotionReadyHandoff] = []
        for path in sorted(self.promotions.glob("*.json")):
            try:
                candidate = self._load_promotion_exact(path.stem)
            except OnceThroughStateError as exc:
                if exc.code == "PROMOTION_HANDOFF_MISSING":
                    continue
                raise
            if candidate.change_id == change_id and candidate.source_commit_sha == source_commit_sha:
                matches.append(candidate)
        if not matches:
            raise OnceThroughStateError("PROMOTION_HANDOFF_MISSING", f"no PromotionReady handoff exists for {lookup}")
        if len(matches) != 1:
            raise OnceThroughStateError("PROMOTION_HANDOFF_AMBIGUOUS", f"multiple PromotionReady handoffs match {lookup}")
        return matches[0]

    def _load_promotion_exact(self, work_id: str) -> PromotionReadyHandoff:
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
            schema_version=int(value.get("schema_version", LEGACY_SCHEMA_VERSION)),
        )
        contract = self.load_contract(work_id)
        assert contract is not None
        if handoff.work_id != work_id or handoff.contract_fingerprint != contract.contract_fingerprint:
            raise OnceThroughStateError("PROMOTION_HANDOFF_INVALID", "PromotionReady identity mismatch")
        return handoff


__all__ = ["OnceThroughStateError", "TaskHandoffStore", "assert_candidate_port_available"]
