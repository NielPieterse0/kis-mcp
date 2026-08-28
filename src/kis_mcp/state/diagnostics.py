from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import islice
from pathlib import Path, PureWindowsPath

from kis_mcp.quarantine import QuarantineRecord, QuarantineService

from .cleanup_coordination import (
    StateCleanupAdmissionGuard,
    StateCleanupIdempotencyStore,
)
from .contract import SPEC_BY_CLASS, StateOwnershipClass
from .resolver import classify_relative_namespace

_PREVIEW_TTL = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class StateInventoryEntry:
    relative_path: str
    ownership_class: str
    state_key: str | None
    identities: dict[str, str]
    authoritative: bool
    reconstructible: bool
    stale: bool | None
    stale_reason: str | None
    safe_to_cleanup: bool
    provenance: str
    age_seconds: int | None
    generation: str | None = None

    def to_json_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "ownership_class": self.ownership_class,
            "state_key": self.state_key,
            "identities": dict(self.identities),
            "authoritative": self.authoritative,
            "reconstructible": self.reconstructible,
            "stale": self.stale,
            "stale_reason": self.stale_reason,
            "safe_to_cleanup": self.safe_to_cleanup,
            "provenance": self.provenance,
            "age_seconds": self.age_seconds,
            "generation": self.generation,
        }


@dataclass(frozen=True, slots=True)
class StateInventoryResult:
    entries: tuple[StateInventoryEntry, ...]
    unclassified_roots: tuple[str, ...]
    truncated: bool

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "entries": [item.to_json_dict() for item in self.entries],
            "unclassified_roots": list(self.unclassified_roots),
            "truncated": self.truncated,
        }


class StateDiagnosticsService:
    def __init__(
        self,
        *,
        state_root: Path,
        project_boundary: Path,
        quarantine_root: Path,
        current_sources: Mapping[str, set[str] | frozenset[str]] | None = None,
        current_sources_provider: Callable[[], Mapping[str, set[str] | frozenset[str]]] | None = None,
        project_roots: Mapping[str, Path] | None = None,
    ) -> None:
        self.state_root = state_root.absolute()
        self.project_boundary = project_boundary.absolute()
        self.quarantine_root = quarantine_root.absolute()
        self._current_sources = {
            str(project_id): frozenset(str(source) for source in sources)
            for project_id, sources in (current_sources or {}).items()
        }
        self._current_sources_provider = current_sources_provider
        roots = project_roots or {
            project_id: self.project_boundary / project_id
            for project_id in self._current_sources
        }
        self.admission_guard = StateCleanupAdmissionGuard(
            state_root=self.state_root,
            project_roots=roots,
            fallback_project_root=self.project_boundary if project_roots is None else None,
        )
        self.idempotency = StateCleanupIdempotencyStore(state_root=self.state_root)
        self._preview_key = secrets.token_bytes(32)
        self.quarantine = QuarantineService(
            project_boundary=str(self.project_boundary),
            quarantine_root=str(self.quarantine_root),
        )

    def inventory(self, *, limit: int = 200) -> StateInventoryResult:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        if not self.state_root.exists():
            return StateInventoryResult((), (), False)
        current_sources = self._resolve_current_sources()
        scan_budget = max(64, min(4096, (limit + 1) * 16))
        entries, scan_truncated = self._scan_namespaces(limit + 1, scan_budget, current_sources)
        entries.sort(key=lambda item: item.relative_path.casefold())
        roots, roots_truncated = self._scan_unclassified_roots(limit + 1)
        return StateInventoryResult(
            entries=tuple(entries[:limit]),
            unclassified_roots=tuple(roots[:limit]),
            truncated=scan_truncated or roots_truncated or len(entries) > limit or len(roots) > limit,
        )

    def cleanup(
        self,
        relative_path: str,
        *,
        apply: bool = False,
        idempotency_key: str | None = None,
        preview_token: str | None = None,
    ) -> dict[str, object]:
        replay_key = None if idempotency_key is None else idempotency_key.strip()
        if not apply or not replay_key:
            return self._cleanup_unlocked(
                relative_path,
                apply=apply,
                idempotency_key=idempotency_key,
                preview_token=preview_token,
            )
        lock_handle = self.idempotency.acquire_lock(replay_key)
        try:
            return self._cleanup_unlocked(
                relative_path,
                apply=apply,
                idempotency_key=idempotency_key,
                preview_token=preview_token,
            )
        finally:
            self.idempotency.release_lock(lock_handle)

    def _cleanup_unlocked(
        self,
        relative_path: str,
        *,
        apply: bool = False,
        idempotency_key: str | None = None,
        preview_token: str | None = None,
    ) -> dict[str, object]:
        target = self._target(relative_path)
        replay_key = None if idempotency_key is None else idempotency_key.strip()
        target_key = os.path.normcase(os.path.abspath(target))
        if apply and replay_key and self.idempotency.has_binding(replay_key):
            _, prior_result, _ = self._bind_idempotency(replay_key, target, target_key)
            if prior_result is not None:
                return prior_result
        if apply and not target.exists():
            raise ValueError("state entry is not eligible for stale-state cleanup")
        request = classify_relative_namespace(self._relative(target))
        if request is None:
            raise ValueError("state entry is not eligible for stale-state cleanup")
        current_sources = self._resolve_current_sources()
        entry = self._entry(target, request.ownership, request.state_key, dict(request.identities), current_sources)
        validated_identity = self._path_identity(target)
        if not entry.safe_to_cleanup:
            raise ValueError("state entry is not eligible for stale-state cleanup")
        if not apply:
            return {
                "schema_version": 1,
                "mode": "preview",
                "action": "would_quarantine",
                "entry": entry.to_json_dict(),
                "quarantine_operation_id": None,
                "preview_token": self._issue_preview_token(target_key, validated_identity),
            }
        self._validate_preview_token(preview_token, target_key, validated_identity)
        project_id = request.identities.get("project_id")
        if not project_id:
            raise ValueError("cleanup project identity is required")
        with self.admission_guard.hold(project_id):
            refreshed_sources = self._resolve_current_sources()
            refreshed = self._entry(target, request.ownership, request.state_key, dict(request.identities), refreshed_sources)
            if not refreshed.safe_to_cleanup or self._path_identity(target) != validated_identity:
                raise ValueError("state entry changed or is no longer eligible for stale-state cleanup")
            reservation_created = False
            operation_id: str | None = None
            if replay_key:
                operation_id = self.quarantine.allocate_operation_id()
                reservation_created, prior_result, operation_id = self._bind_idempotency(
                    replay_key,
                    target,
                    target_key,
                    operation_id=operation_id,
                )
                if prior_result is not None:
                    return prior_result
            try:
                record = self.quarantine.quarantine(
                    str(target),
                    expected_identity=validated_identity,
                    post_move_validator=lambda: self._assert_cleanup_still_eligible(
                        request.ownership,
                        dict(request.identities),
                    ),
                    operation_id=operation_id,
                )
            except Exception:
                if reservation_created and target.exists():
                    active_reserved = (
                        None if operation_id is None else self._bound_quarantine(target, operation_id)
                    )
                    if active_reserved is None:
                        self.idempotency.release(replay_key)
                raise
            result = self._cleanup_result("apply", "quarantined", record, entry=entry)
            if replay_key:
                self.idempotency.complete(replay_key, target_key, result)
            return result

    def _assert_cleanup_still_eligible(
        self,
        ownership: StateOwnershipClass,
        identities: Mapping[str, str],
    ) -> None:
        stale, _ = self._staleness(ownership, identities, self._resolve_current_sources())
        if ownership is not StateOwnershipClass.RECONSTRUCTIBLE_CACHE or stale is not True:
            raise ValueError("state entry became current during stale-state cleanup")

    def _issue_preview_token(self, target_key: str, identity: tuple[int, int, int]) -> str:
        payload = json.dumps(
            {
                "target": target_key,
                "identity": list(identity),
                "issued_at": datetime.now(UTC).isoformat(),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        signature = hmac.new(self._preview_key, payload, hashlib.sha256).hexdigest()
        return f"{encoded}.{signature}"

    def _validate_preview_token(
        self,
        token: str | None,
        target_key: str,
        identity: tuple[int, int, int],
    ) -> None:
        if not isinstance(token, str) or not token.strip():
            raise ValueError("preview_token from a prior cleanup preview is required")
        try:
            encoded, signature = token.strip().split(".", 1)
            padding = "=" * (-len(encoded) % 4)
            payload = base64.urlsafe_b64decode(encoded + padding)
            expected = hmac.new(self._preview_key, payload, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("preview token signature mismatch")
            document = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("preview_token is invalid") from exc
        if not isinstance(document, dict):
            raise TypeError("preview_token is invalid")
        if document.get("target") != target_key or document.get("identity") != list(identity):
            raise ValueError("preview_token does not match the current state entry")
        issued_at = document.get("issued_at")
        if not isinstance(issued_at, str):
            raise TypeError("preview_token is invalid")
        try:
            issued = datetime.fromisoformat(issued_at)
        except ValueError as exc:
            raise ValueError("preview_token is invalid") from exc
        if issued.tzinfo is None:
            raise ValueError("preview_token is invalid")
        age = datetime.now(UTC) - issued.astimezone(UTC)
        if age < timedelta(seconds=-5) or age > _PREVIEW_TTL:
            raise ValueError("preview_token is expired")

    def _scan_namespaces(
        self,
        entry_limit: int,
        scan_budget: int,
        current_sources: Mapping[str, frozenset[str]],
    ) -> tuple[list[StateInventoryEntry], bool]:
        entries: list[StateInventoryEntry] = []
        queue: deque[Path] = deque([self.state_root])
        scanned = 0
        traversal_truncated = False
        while queue and len(entries) < entry_limit and scanned < scan_budget:
            root = queue.popleft()
            if not self._safe_traversal_directory(root):
                continue
            remaining = max(1, scan_budget - scanned)
            children, children_truncated = self._bounded_children(root, remaining)
            traversal_truncated = traversal_truncated or children_truncated
            for child in children:
                if not self._safe_traversal_directory(child):
                    continue
                scanned += 1
                relative = self._relative(child)
                request = classify_relative_namespace(relative)
                if request is not None:
                    entries.append(
                        self._entry(
                            child,
                            request.ownership,
                            request.state_key,
                            dict(request.identities),
                            current_sources,
                        )
                    )
                    if len(entries) >= entry_limit:
                        break
                    continue
                if scanned >= scan_budget:
                    break
                queue.append(child)
        return entries, traversal_truncated or bool(queue) or scanned >= scan_budget

    def _safe_traversal_directory(self, path: Path) -> bool:
        try:
            if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                return False
            if not path.is_dir():
                return False
            resolved = path.resolve(strict=True)
            state_root = self.state_root.resolve(strict=True)
            resolved.relative_to(state_root)
            return True
        except (OSError, ValueError):
            return False

    @staticmethod
    def _bounded_children(root: Path, limit: int) -> tuple[list[Path], bool]:
        try:
            candidates = list(islice(root.iterdir(), limit + 1))
        except OSError:
            return [], False
        truncated = len(candidates) > limit
        candidates = candidates[:limit]
        candidates.sort(key=lambda item: item.name.casefold())
        return candidates, truncated

    def _scan_unclassified_roots(self, limit: int) -> tuple[list[str], bool]:
        canonical = {"global", "projects", "runtime", "quarantine"}
        try:
            candidates = list(islice(self.state_root.iterdir(), limit + 1))
        except OSError:
            return [], False
        candidates.sort(key=lambda item: item.name.casefold())
        roots = [path.name for path in candidates if path.name.casefold() not in canonical]
        return roots[:limit], len(candidates) > limit or len(roots) > limit


    def _bind_idempotency(
        self,
        key: str,
        target: Path,
        target_key: str,
        *,
        operation_id: str | None = None,
    ) -> tuple[bool, dict[str, object] | None, str]:
        if self.idempotency.has_binding(key):
            created = False
            existing = self.idempotency.read(key)
        else:
            if operation_id is None:
                raise ValueError("idempotency reservation requires quarantine operation identity")
            created, existing = self.idempotency.reserve(key, target_key, operation_id)
        if existing.get("target") != target_key:
            raise ValueError("idempotency_key was already used for a different state path")
        bound_operation_id = existing.get("quarantine_operation_id")
        if not isinstance(bound_operation_id, str) or not bound_operation_id:
            raise ValueError("idempotency binding is missing quarantine operation identity")
        result = existing.get("result")
        if isinstance(result, dict):
            active = self._bound_quarantine(target, bound_operation_id)
            expected_operation_id = result.get("quarantine_operation_id")
            if active is None or expected_operation_id != bound_operation_id:
                raise ValueError("idempotency replay conflicts with current state")
            return False, dict(result), bound_operation_id
        active = self._bound_quarantine(target, bound_operation_id)
        if active is not None:
            reconciled = self._cleanup_result("apply", "already_quarantined", active)
            self.idempotency.complete(key, target_key, reconciled)
            return False, reconciled, bound_operation_id
        if not target.exists():
            raise ValueError("idempotency replay conflicts with current state")
        self.idempotency.rewrite_reservation(key, existing)
        return created, None, bound_operation_id

    @staticmethod
    def _path_identity(path: Path) -> tuple[int, int, int]:
        stat = path.stat()
        return (stat.st_dev, stat.st_ino, stat.st_mode)

    def _bound_quarantine(self, target: Path, operation_id: str) -> QuarantineRecord | None:
        record = self.quarantine.get_active_record(operation_id)
        if record is None:
            return None
        expected = os.path.normcase(os.path.abspath(target))
        actual = os.path.normcase(os.path.abspath(record.original_path))
        return record if actual == expected else None

    def _prior_quarantine(self, target: Path) -> QuarantineRecord | None:
        return self.quarantine.find_active_record_by_original_path(str(target))

    def _cleanup_result(
        self,
        mode: str,
        action: str,
        record: QuarantineRecord,
        *,
        entry: StateInventoryEntry | None = None,
    ) -> dict[str, object]:
        return {
            "schema_version": 1,
            "mode": mode,
            "action": action,
            "entry": None if entry is None else entry.to_json_dict(),
            "quarantine_operation_id": record.operation_id,
        }

    def _target(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("relative_path must be non-empty")
        relative = PureWindowsPath(relative_path.strip().replace("/", "\\"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("relative_path must stay beneath the state root")
        target = self.state_root.joinpath(*relative.parts).absolute()
        try:
            target.relative_to(self.state_root)
        except ValueError as exc:
            raise ValueError("relative_path must stay beneath the state root") from exc
        return target

    def _relative(self, path: Path) -> str:
        return str(PureWindowsPath(*path.relative_to(self.state_root).parts))

    def _entry(
        self,
        path: Path,
        ownership: StateOwnershipClass,
        state_key: str | None,
        identities: dict[str, str],
        current_sources: Mapping[str, frozenset[str]],
    ) -> StateInventoryEntry:
        spec = SPEC_BY_CLASS[ownership]
        stale, reason = self._staleness(ownership, identities, current_sources)
        safe = (
            ownership is StateOwnershipClass.RECONSTRUCTIBLE_CACHE
            and stale is True
            and reason == "source_not_current"
        )
        try:
            age_seconds = max(0, int(datetime.now(UTC).timestamp() - path.stat().st_mtime))
        except OSError:
            age_seconds = None
        return StateInventoryEntry(
            relative_path=self._relative(path),
            ownership_class=ownership.value,
            state_key=state_key,
            identities=dict(identities),
            authoritative=spec.authoritative,
            reconstructible=spec.reconstructible,
            stale=stale,
            stale_reason=reason,
            safe_to_cleanup=safe,
            provenance="canonical_state_path_contract",
            age_seconds=age_seconds,
        )

    def _resolve_current_sources(self) -> dict[str, frozenset[str]]:
        source_map = self._current_sources_provider() if self._current_sources_provider is not None else self._current_sources
        return {
            str(project_id): frozenset(str(source) for source in sources)
            for project_id, sources in source_map.items()
        }

    def _staleness(
        self,
        ownership: StateOwnershipClass,
        identities: Mapping[str, str],
        current_sources: Mapping[str, frozenset[str]],
    ) -> tuple[bool | None, str | None]:
        if ownership in {StateOwnershipClass.RUNTIME_INSTANCE_SPECIFIC, StateOwnershipClass.EPHEMERAL}:
            return None, "runtime_liveness_not_inferred_from_storage"
        project_id = identities.get("project_id")
        source_id = identities.get("source_id")
        if project_id is not None:
            if project_id not in current_sources:
                return True, "project_not_registered"
            if source_id is not None and "*" in current_sources[project_id]:
                return None, "source_inventory_truncated"
            if source_id is not None and source_id not in current_sources[project_id]:
                return True, "source_not_current"
            return False, None
        return False, None


__all__ = ["StateDiagnosticsService", "StateInventoryEntry", "StateInventoryResult"]
