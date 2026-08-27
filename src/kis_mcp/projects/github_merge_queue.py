"""KIS speculative landing queue for centrally registered GitHub repositories."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from fastmcp.exceptions import ToolError

from ..config import load_runtime_config
from ..paths import (
    PathValidationError,
    is_within_windows_boundary,
    normalize_windows_path,
)
from ..state import StateNamespaceRequest, StateNamespaceResolver, StateOwnershipClass
from .github_exact import CommandRunner, RegisteredGitHubOperations
from .post_land import PostLandHooks, dispatch_post_land_non_interfering
from .registry import ProjectRegistry
from .settings import load_project_registry_settings

_SHA = re.compile(r"^[0-9a-f]{40}$")
_PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_QUEUE_STATES = frozenset({"QUEUED", "AWAITING_CHECKS", "MERGEABLE"})


@dataclass(frozen=True, slots=True)
class MergeQueueSettings:
    enabled: bool
    state_root: Path
    target_branch: str
    merge_method: str
    grouping_strategy: str
    build_concurrency: int
    status_check_timeout_minutes: int
    min_entries_to_merge: int
    max_entries_to_merge: int
    min_entries_to_merge_wait_minutes: int
    allow_jump: bool
    candidate_ref_prefix: str
    verification_workflow: str


@dataclass(frozen=True, slots=True)
class QueueTarget:
    project_id: str
    repository: str
    local_root: Path
    remote_url: str


@dataclass(frozen=True, slots=True)
class PullRequestSnapshot:
    pull_number: int
    head_sha: str
    head_ref: str
    base_ref: str
    state: str
    is_draft: bool
    url: str
    review_decision: str | None = None
    merge_state_status: str | None = None


@dataclass(frozen=True, slots=True)
class CandidateCheck:
    state: str
    run_id: str | None
    url: str | None
    observed_at: str | None


@dataclass(frozen=True, slots=True)
class _LandingOutcome:
    result: dict[str, Any]
    landed_sha: str


GovernanceValidator = Callable[
    [str, int, str, Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]
]


class MergeQueueBackend(Protocol):
    def target(self, project_id: str) -> QueueTarget: ...
    def prepare(self, target: QueueTarget, target_branch: str) -> str: ...
    def pull_request(self, target: QueueTarget, pull_number: int) -> PullRequestSnapshot: ...
    def build_candidate(
        self,
        target: QueueTarget,
        pull_number: int,
        parent: str,
        head: str,
        message: str,
    ) -> str | None: ...
    def publish_candidate(self, target: QueueTarget, branch: str, candidate_sha: str) -> None: ...
    def candidate_check(self, target: QueueTarget, branch: str, candidate_sha: str) -> CandidateCheck: ...
    def is_ancestor(self, target: QueueTarget, ancestor: str, descendant: str) -> bool: ...
    def advance_base(self, target: QueueTarget, target_branch: str, expected_base: str, candidate_sha: str) -> None: ...


def _default_settings_path() -> Path:
    return Path(__file__).resolve().parents[3] / "settings" / "github-merge-queue.settings.json"


def _full_sha(value: object, label: str) -> str:
    normalized = str(value).strip().lower()
    if _SHA.fullmatch(normalized) is None:
        raise ToolError(f"INVALID_GITHUB_SHA: {label} must be a full 40-character SHA")
    return normalized


def _positive_int(value: object, label: str, *, minimum: int = 1, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ToolError(f"MERGE_QUEUE_SETTINGS_INVALID: {label} must be an integer >= {minimum}")
    if maximum is not None and value > maximum:
        raise ToolError(f"MERGE_QUEUE_SETTINGS_INVALID: {label} must be <= {maximum}")
    return value


def load_merge_queue_settings(path: Path | None = None) -> MergeQueueSettings:
    source = path or _default_settings_path()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolError(f"MERGE_QUEUE_SETTINGS_INVALID: unable to read {source}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ToolError("MERGE_QUEUE_SETTINGS_INVALID: schema_version must be 1")
    expected = {
        "schema_version", "enabled", "state_root", "target_branch", "merge_method",
        "grouping_strategy", "build_concurrency", "status_check_timeout_minutes",
        "min_entries_to_merge", "max_entries_to_merge", "min_entries_to_merge_wait_minutes",
        "allow_jump", "candidate_ref_prefix", "verification_workflow",
    }
    if set(payload) != expected:
        raise ToolError("MERGE_QUEUE_SETTINGS_INVALID: settings keys do not match the versioned contract")
    if not isinstance(payload["enabled"], bool):
        raise ToolError("MERGE_QUEUE_SETTINGS_INVALID: enabled must be boolean")
    if payload["merge_method"] != "merge" or payload["grouping_strategy"] != "allgreen":
        raise ToolError("MERGE_QUEUE_SETTINGS_INVALID: v1 requires merge + allgreen")
    if payload["allow_jump"] is not False:
        raise ToolError("MERGE_QUEUE_SETTINGS_INVALID: v1 does not permit queue jumps")
    branch = str(payload["target_branch"]).strip()
    prefix = str(payload["candidate_ref_prefix"]).strip().strip("/")
    workflow = str(payload["verification_workflow"]).strip()
    if not branch or not prefix or not workflow:
        raise ToolError("MERGE_QUEUE_SETTINGS_INVALID: branch, ref prefix, and workflow must be non-empty")
    minimum = _positive_int(payload["min_entries_to_merge"], "min_entries_to_merge")
    maximum = _positive_int(payload["max_entries_to_merge"], "max_entries_to_merge")
    if minimum > maximum:
        raise ToolError("MERGE_QUEUE_SETTINGS_INVALID: min_entries_to_merge exceeds max_entries_to_merge")
    wait = payload["min_entries_to_merge_wait_minutes"]
    if wait != 0:
        raise ToolError("MERGE_QUEUE_SETTINGS_INVALID: v1 requires a zero merge wait")
    try:
        state_root = normalize_windows_path(
            str(payload["state_root"]), base=r"C:\Projects"
        )
    except PathValidationError as exc:
        raise ToolError("MERGE_QUEUE_SETTINGS_INVALID: invalid state_root") from exc
    if not is_within_windows_boundary(state_root, boundary=r"C:\Projects"):
        raise ToolError("MERGE_QUEUE_SETTINGS_INVALID: state_root is outside the project boundary")
    return MergeQueueSettings(
        enabled=payload["enabled"],
        state_root=Path(state_root),
        target_branch=branch,
        merge_method="merge",
        grouping_strategy="allgreen",
        build_concurrency=_positive_int(payload["build_concurrency"], "build_concurrency", maximum=100),
        status_check_timeout_minutes=_positive_int(payload["status_check_timeout_minutes"], "status_check_timeout_minutes"),
        min_entries_to_merge=minimum,
        max_entries_to_merge=maximum,
        min_entries_to_merge_wait_minutes=wait,
        allow_jump=False,
        candidate_ref_prefix=prefix,
        verification_workflow=workflow,
    )


def _queue_state_key(target_branch: str) -> str:
    raw_branch = target_branch.strip()
    readable_branch = raw_branch.casefold()
    digest = hashlib.sha256(raw_branch.encode("utf-8")).hexdigest()[:16]
    readable = re.sub(r"[^a-z0-9]+", "-", readable_branch).strip("-")[:48] or "branch"
    return f"merge-queue-{readable}-{digest}"


def _canonical_queue_path(project_id: str, target_branch: str) -> Path:
    namespace = StateNamespaceResolver().resolve(
        StateNamespaceRequest(
            ownership=StateOwnershipClass.PROJECT_SPECIFIC,
            state_key=_queue_state_key(target_branch),
            identities={"project_id": project_id},
        )
    )
    return Path(namespace.path) / "queue.json"


class QueueStateStore:
    """Atomic generated-state store. Repository and GitHub remain authoritative."""

    def __init__(
        self,
        root: Path,
        *,
        canonical: bool = False,
        canonical_path_resolver: Callable[[str, str], Path] | None = None,
    ) -> None:
        self.root = Path(root)
        self.canonical = canonical
        self._canonical_path_resolver = canonical_path_resolver or _canonical_queue_path

    def _legacy_path(self, project_id: str, target_branch: str) -> Path:
        if _PROJECT_ID.fullmatch(project_id) is None:
            raise ToolError("MERGE_QUEUE_PROJECT_ID_INVALID")
        if not target_branch or any(
            part in {"", ".", ".."}
            for part in target_branch.replace("\\", "/").split("/")
        ):
            raise ToolError("MERGE_QUEUE_TARGET_BRANCH_INVALID")
        safe_branch = target_branch.replace("/", "__")
        return self.root / project_id / f"{safe_branch}.json"

    def _path(self, project_id: str, target_branch: str) -> Path:
        legacy = self._legacy_path(project_id, target_branch)
        if not self.canonical:
            return legacy
        return self._canonical_path_resolver(project_id, target_branch)

    @contextmanager
    def mutation_lock(self, project_id: str, target_branch: str) -> Iterable[None]:
        path = self._path(project_id, target_branch)
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as stream:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
                os.fsync(stream.fileno())
            stream.seek(0)
            _lock_queue_file(stream)
            try:
                yield
            finally:
                _unlock_queue_file(stream)

    def load(self, project_id: str, target_branch: str) -> dict[str, Any] | None:
        path = self._path(project_id, target_branch)
        if not path.is_file() and self.canonical:
            legacy = self._legacy_path(project_id, target_branch)
            if legacy.is_file():
                path = legacy
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ToolError("MERGE_QUEUE_STATE_INVALID: state file is unreadable") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ToolError("MERGE_QUEUE_STATE_INVALID: unsupported state schema")
        if payload.get("project_id") != project_id or payload.get("target_branch") != target_branch:
            raise ToolError("MERGE_QUEUE_STATE_INVALID: state identity mismatch")
        entries = payload.get("entries")
        events = payload.get("events")
        if not isinstance(entries, list) or not isinstance(events, list):
            raise ToolError("MERGE_QUEUE_STATE_INVALID: entries/events must be arrays")
        return payload

    def save(self, state: Mapping[str, Any]) -> Path:
        project_id = str(state.get("project_id", ""))
        target_branch = str(state.get("target_branch", ""))
        path = self._path(project_id, target_branch)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        serialized = json.dumps(dict(state), indent=2, sort_keys=True) + "\n"
        temporary.write_text(serialized, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
        return path


def _lock_queue_file(stream: Any) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_EX)


def _unlock_queue_file(stream: Any) -> None:
    if os.name == "nt":
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class MergeQueueCoordinator:
    """Provider-neutral FIFO/generation coordinator over an exact GitHub backend."""

    def __init__(
        self,
        settings: MergeQueueSettings,
        store: QueueStateStore,
        backend: MergeQueueBackend,
        *,
        now: Any | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.backend = backend
        self._now = now or (lambda: datetime.now(UTC))
        if not settings.enabled:
            raise ToolError("MERGE_QUEUE_DISABLED")

    def _timestamp(self) -> str:
        return self._now().astimezone(UTC).isoformat().replace("+00:00", "Z")

    def _new_state(self, target: QueueTarget, base_sha: str) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "project_id": target.project_id,
            "repository": target.repository,
            "target_branch": self.settings.target_branch,
            "generation": 1,
            "base_sha": _full_sha(base_sha, "base_sha"),
            "entries": [],
            "events": [],
            "updated_at": self._timestamp(),
        }

    def _load_or_create(self, target: QueueTarget, base_sha: str) -> dict[str, Any]:
        state = self.store.load(target.project_id, self.settings.target_branch)
        if state is None:
            state = self._new_state(target, base_sha)
        if state.get("repository") != target.repository:
            raise ToolError("MERGE_QUEUE_STATE_INVALID: repository mismatch")
        _full_sha(state.get("base_sha"), "queue base")
        generation = state.get("generation")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
            raise ToolError("MERGE_QUEUE_STATE_INVALID: generation must be positive")
        self._validate_entries(state)
        return state

    def _validate_entries(self, state: Mapping[str, Any]) -> None:
        generation = int(state["generation"])
        seen: set[int] = set()
        for index, entry in enumerate(state["entries"], start=1):
            if not isinstance(entry, dict):
                raise ToolError("MERGE_QUEUE_STATE_INVALID: entry must be an object")
            pull = entry.get("pull_number")
            if isinstance(pull, bool) or not isinstance(pull, int) or pull <= 0 or pull in seen:
                raise ToolError("MERGE_QUEUE_STATE_INVALID: invalid or duplicate pull number")
            seen.add(pull)
            _full_sha(entry.get("head_sha"), "queued head")
            if entry.get("position") != index:
                raise ToolError("MERGE_QUEUE_STATE_INVALID: position mismatch")
            if entry.get("generation") != generation:
                raise ToolError("MERGE_QUEUE_STATE_INVALID: entry generation mismatch")
            if entry.get("state") not in _QUEUE_STATES:
                raise ToolError("MERGE_QUEUE_STATE_INVALID: unsupported entry state")
            candidate = entry.get("candidate_sha")
            if candidate is not None:
                _full_sha(candidate, "candidate")

    def _record_event(self, state: dict[str, Any], *, reason: str, pull_number: int | None = None) -> None:
        event: dict[str, Any] = {
            "generation": state["generation"],
            "reason": reason,
            "at": self._timestamp(),
        }
        if pull_number is not None:
            event["pull_number"] = pull_number
        state["events"].append(event)
        state["events"] = state["events"][-100:]

    def _reset_generation(self, state: dict[str, Any], *, base_sha: str, reason: str) -> None:
        state["generation"] = int(state["generation"]) + 1
        state["base_sha"] = _full_sha(base_sha, "base_sha")
        self._record_event(state, reason=reason)
        for position, entry in enumerate(state["entries"], start=1):
            entry.update(
                {
                    "position": position,
                    "generation": state["generation"],
                    "state": "QUEUED",
                    "candidate_sha": None,
                    "candidate_ref": None,
                    "candidate_created_at": None,
                    "member_heads": [],
                    "check_run_id": None,
                    "check_url": None,
                }
            )
        state["updated_at"] = self._timestamp()

    def _drop_entry(self, state: dict[str, Any], index: int, *, reason: str, base_sha: str) -> int:
        removed = state["entries"].pop(index)
        old_generation = state["generation"]
        state["generation"] = int(old_generation) + 1
        state["base_sha"] = _full_sha(base_sha, "base_sha")
        self._record_event(state, reason=reason, pull_number=int(removed["pull_number"]))
        for position, entry in enumerate(state["entries"], start=1):
            entry.update(
                {
                    "position": position,
                    "generation": state["generation"],
                    "state": "QUEUED",
                    "candidate_sha": None,
                    "candidate_ref": None,
                    "candidate_created_at": None,
                    "member_heads": [],
                    "check_run_id": None,
                    "check_url": None,
                }
            )
        state["updated_at"] = self._timestamp()
        return int(removed["pull_number"])

    def _candidate_ref(self, generation: int, pull_number: int) -> str:
        return f"{self.settings.candidate_ref_prefix}/{self.settings.target_branch}/g{generation}/pr-{pull_number}"

    @staticmethod
    def _pr_is_exact(pr: PullRequestSnapshot, expected_head: str, target_branch: str) -> bool:
        return (
            pr.state == "OPEN"
            and not pr.is_draft
            and pr.base_ref == target_branch
            and pr.head_sha == expected_head
            and pr.review_decision not in {"CHANGES_REQUESTED", "REVIEW_REQUIRED"}
            and pr.merge_state_status != "BLOCKED"
        )

    def status(self, *, project_id: str) -> dict[str, Any]:
        target = self.backend.target(project_id)
        live_base = _full_sha(self.backend.prepare(target, self.settings.target_branch), "live base")
        state = self._load_or_create(target, live_base)
        return {
            "schema_version": 1,
            "state": "current" if state["base_sha"] == live_base else "stale",
            "live_base_sha": live_base,
            "base_current": state["base_sha"] == live_base,
            "queue": state,
        }

    def enqueue(
        self,
        *,
        project_id: str,
        pull_number: int,
        expected_head: str,
        governance: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if isinstance(pull_number, bool) or not isinstance(pull_number, int) or pull_number <= 0:
            raise ToolError("MERGE_QUEUE_PULL_REQUEST_INVALID")
        authorized_head = _full_sha(expected_head, "expected_head")
        target = self.backend.target(project_id)
        live_base = _full_sha(self.backend.prepare(target, self.settings.target_branch), "live base")
        pr = self.backend.pull_request(target, pull_number)
        if pr.head_sha != authorized_head:
            raise ToolError(
                f"QUEUE_PULL_REQUEST_HEAD_MISMATCH: expected {authorized_head}, observed {pr.head_sha}"
            )
        if not self._pr_is_exact(pr, authorized_head, self.settings.target_branch):
            raise ToolError("QUEUE_PULL_REQUEST_NOT_ELIGIBLE: pull request must be open, non-draft, and target the queue base")
        with self.store.mutation_lock(target.project_id, self.settings.target_branch):
            state = self._load_or_create(target, live_base)
            if state["base_sha"] != live_base:
                self._reset_generation(state, base_sha=live_base, reason="base_moved")
            for entry in state["entries"]:
                if entry["pull_number"] != pull_number:
                    continue
                if entry["head_sha"] != authorized_head:
                    raise ToolError("QUEUE_PULL_REQUEST_ALREADY_QUEUED_STALE")
                return {"schema_version": 1, "state": "already_queued", "queue": state}
            if state["entries"]:
                self._reset_generation(state, base_sha=live_base, reason="enqueue_topology_changed")
            position = len(state["entries"]) + 1
            state["entries"].append(
                {
                    "position": position,
                    "pull_number": pull_number,
                    "head_sha": authorized_head,
                    "head_ref": pr.head_ref,
                    "base_ref": pr.base_ref,
                    "enqueued_at": self._timestamp(),
                    "generation": state["generation"],
                    "state": "QUEUED",
                    "candidate_sha": None,
                    "candidate_ref": None,
                    "candidate_created_at": None,
                    "member_heads": [],
                    "check_run_id": None,
                    "check_url": None,
                    "governance": dict(governance) if governance is not None else None,
                }
            )
            self._record_event(state, reason="enqueued", pull_number=pull_number)
            state["updated_at"] = self._timestamp()
            self.store.save(state)
            return {"schema_version": 1, "state": "queued", "queue": state}

    def dequeue(self, *, project_id: str, pull_number: int, expected_head: str) -> dict[str, Any]:
        authorized_head = _full_sha(expected_head, "expected_head")
        target = self.backend.target(project_id)
        live_base = _full_sha(self.backend.prepare(target, self.settings.target_branch), "live base")
        with self.store.mutation_lock(target.project_id, self.settings.target_branch):
            state = self._load_or_create(target, live_base)
            if state["base_sha"] != live_base:
                self._reset_generation(state, base_sha=live_base, reason="base_moved")
            index = next((i for i, item in enumerate(state["entries"]) if item["pull_number"] == pull_number), None)
            if index is None:
                raise ToolError("QUEUE_PULL_REQUEST_NOT_FOUND")
            if state["entries"][index]["head_sha"] != authorized_head:
                raise ToolError("QUEUE_PULL_REQUEST_HEAD_MISMATCH")
            self._drop_entry(state, index, reason="dequeued", base_sha=live_base)
            self.store.save(state)
            return {"schema_version": 1, "state": "dequeued", "queue": state}

    def _check_timed_out(self, entry: Mapping[str, Any]) -> bool:
        created = entry.get("candidate_created_at")
        if not isinstance(created, str) or not created:
            return False
        try:
            started = datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            raise ToolError("MERGE_QUEUE_STATE_INVALID: candidate_created_at is invalid") from None
        return self._now().astimezone(UTC) - started >= timedelta(
            minutes=self.settings.status_check_timeout_minutes
        )

    def _validate_live_entries(
        self, target: QueueTarget, state: dict[str, Any], live_base: str
    ) -> bool:
        for index, entry in enumerate(tuple(state["entries"])):
            pr = self.backend.pull_request(target, int(entry["pull_number"]))
            if not self._pr_is_exact(
                pr, str(entry["head_sha"]), self.settings.target_branch
            ):
                self._drop_entry(
                    state, index, reason="pull_request_changed", base_sha=live_base
                )
                return True
        return False

    def _refresh_existing_checks(
        self, target: QueueTarget, state: dict[str, Any], live_base: str
    ) -> bool:
        for index, entry in enumerate(tuple(state["entries"])):
            candidate = entry.get("candidate_sha")
            branch = entry.get("candidate_ref")
            if candidate is None or branch is None:
                continue
            check = self.backend.candidate_check(target, str(branch), str(candidate))
            if check.state == "success":
                entry["state"] = "MERGEABLE"
                entry["check_run_id"] = check.run_id
                entry["check_url"] = check.url
                continue
            if check.state == "failure" or (
                check.state == "pending" and self._check_timed_out(entry)
            ):
                reason = (
                    "candidate_check_failure"
                    if check.state == "failure"
                    else "candidate_check_timeout"
                )
                self._drop_entry(state, index, reason=reason, base_sha=live_base)
                return True
            entry["state"] = "AWAITING_CHECKS"
            entry["check_run_id"] = check.run_id
            entry["check_url"] = check.url
        return False

    def _build_available_candidates(
        self, target: QueueTarget, state: dict[str, Any], live_base: str
    ) -> bool:
        in_flight = sum(
            1 for item in state["entries"] if item["state"] == "AWAITING_CHECKS"
        )
        slots = max(0, self.settings.build_concurrency - in_flight)
        if slots == 0:
            return False
        parent = str(state["base_sha"])
        member_heads: list[str] = []
        for index, entry in enumerate(tuple(state["entries"])):
            member_heads.append(str(entry["head_sha"]))
            existing = entry.get("candidate_sha")
            if existing is not None:
                parent = str(existing)
                continue
            if slots <= 0:
                break
            if index > 0 and state["entries"][index - 1].get("candidate_sha") is None:
                break
            message = (
                f"KIS merge queue g{state['generation']} PR #{entry['pull_number']} "
                f"onto {parent}"
            )
            candidate = self.backend.build_candidate(
                target,
                int(entry["pull_number"]),
                parent,
                str(entry["head_sha"]),
                message,
            )
            if candidate is None:
                self._drop_entry(
                    state, index, reason="candidate_conflict", base_sha=live_base
                )
                return True
            candidate_sha = _full_sha(candidate, "candidate")
            branch = self._candidate_ref(
                int(state["generation"]), int(entry["pull_number"])
            )
            self.backend.publish_candidate(target, branch, candidate_sha)
            entry.update(
                {
                    "candidate_sha": candidate_sha,
                    "candidate_ref": branch,
                    "candidate_created_at": self._timestamp(),
                    "member_heads": list(member_heads),
                    "state": "AWAITING_CHECKS",
                    "check_run_id": None,
                    "check_url": None,
                }
            )
            parent = candidate_sha
            slots -= 1
        return False

    def reconcile(self, *, project_id: str) -> dict[str, Any]:
        target = self.backend.target(project_id)
        live_base = _full_sha(
            self.backend.prepare(target, self.settings.target_branch), "live base"
        )
        with self.store.mutation_lock(target.project_id, self.settings.target_branch):
            state = self._load_or_create(target, live_base)
            if state["base_sha"] != live_base:
                self._reset_generation(state, base_sha=live_base, reason="base_moved")
            max_rounds = max(2, len(state["entries"]) + 2)
            for _ in range(max_rounds):
                if self._validate_live_entries(target, state, live_base):
                    continue
                if self._refresh_existing_checks(target, state, live_base):
                    continue
                if self._build_available_candidates(target, state, live_base):
                    continue
                break
            else:
                raise ToolError("MERGE_QUEUE_RECONCILIATION_UNSTABLE")
            state["updated_at"] = self._timestamp()
            self.store.save(state)
            return {"schema_version": 1, "state": "reconciled", "queue": state}

    def _green_prefix(self, state: Mapping[str, Any]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        for entry in state["entries"]:
            if entry["state"] != "MERGEABLE":
                break
            selected.append(entry)
            if len(selected) >= self.settings.max_entries_to_merge:
                break
        if len(selected) < self.settings.min_entries_to_merge:
            raise ToolError("MERGE_QUEUE_NOT_READY: insufficient contiguous ALLGREEN entries")
        return selected

    def _revalidate_landing_entry(
        self,
        target: QueueTarget,
        entry: Mapping[str, Any],
        expected_members: list[str],
    ) -> None:
        pr = self.backend.pull_request(target, int(entry["pull_number"]))
        if not self._pr_is_exact(
            pr, str(entry["head_sha"]), self.settings.target_branch
        ):
            raise ToolError("MERGE_QUEUE_LANDING_PR_CHANGED")
        if entry.get("member_heads") != expected_members:
            raise ToolError("MERGE_QUEUE_LANDING_MEMBERSHIP_MISMATCH")
        candidate = _full_sha(entry.get("candidate_sha"), "candidate")
        branch = str(entry.get("candidate_ref") or "")
        if not branch:
            raise ToolError("MERGE_QUEUE_LANDING_CANDIDATE_MISSING")
        check = self.backend.candidate_check(target, branch, candidate)
        if check.state != "success":
            raise ToolError("MERGE_QUEUE_LANDING_CHECK_NOT_GREEN")

    def preview_land(
        self,
        *,
        project_id: str,
        expected_generation: int,
        expected_base: str,
    ) -> dict[str, Any]:
        authorized_base = _full_sha(expected_base, "expected_base")
        target = self.backend.target(project_id)
        live_base = _full_sha(
            self.backend.prepare(target, self.settings.target_branch), "live base"
        )
        state = self._load_or_create(target, live_base)
        if state["generation"] != expected_generation:
            raise ToolError("QUEUE_GENERATION_MISMATCH")
        if state["base_sha"] != authorized_base or live_base != authorized_base:
            raise ToolError("QUEUE_BASE_MISMATCH")
        selected = self._green_prefix(state)
        return {
            "schema_version": 1,
            "generation": expected_generation,
            "base_sha": authorized_base,
            "entries": [
                {
                    "pull_number": int(entry["pull_number"]),
                    "head_sha": str(entry["head_sha"]),
                }
                for entry in selected
            ],
        }

    def _land_outcome(
        self,
        *,
        project_id: str,
        expected_generation: int,
        expected_base: str,
    ) -> _LandingOutcome:
        target = self.backend.target(project_id)
        with self.store.mutation_lock(target.project_id, self.settings.target_branch):
            return self._land_outcome_locked(
                project_id=project_id,
                expected_generation=expected_generation,
                expected_base=expected_base,
            )

    def _land_outcome_locked(
        self,
        *,
        project_id: str,
        expected_generation: int,
        expected_base: str,
    ) -> _LandingOutcome:
        authorized_base = _full_sha(expected_base, "expected_base")
        target = self.backend.target(project_id)
        live_base = _full_sha(
            self.backend.prepare(target, self.settings.target_branch), "live base"
        )
        state = self._load_or_create(target, live_base)
        if state["generation"] != expected_generation:
            raise ToolError("QUEUE_GENERATION_MISMATCH")
        if state["base_sha"] != authorized_base:
            raise ToolError("QUEUE_BASE_MISMATCH")
        if live_base != authorized_base:
            raise ToolError("QUEUE_BASE_MOVED")
        selected = self._green_prefix(state)
        expected_members: list[str] = []
        for entry in selected:
            expected_members.append(str(entry["head_sha"]))
            self._revalidate_landing_entry(target, entry, list(expected_members))
        final_candidate = _full_sha(
            selected[-1]["candidate_sha"], "final candidate"
        )
        if not self.backend.is_ancestor(target, authorized_base, final_candidate):
            raise ToolError("MERGE_QUEUE_ANCESTRY_MISMATCH")
        for head in expected_members:
            if not self.backend.is_ancestor(target, head, final_candidate):
                raise ToolError("MERGE_QUEUE_MEMBER_ANCESTRY_MISMATCH")
        self.backend.advance_base(
            target,
            self.settings.target_branch,
            authorized_base,
            final_candidate,
        )
        landed_pull_numbers = [int(item["pull_number"]) for item in selected]
        state["entries"] = state["entries"][len(selected):]
        state["base_sha"] = final_candidate
        state["generation"] = int(state["generation"]) + 1
        for position, entry in enumerate(state["entries"], start=1):
            entry["position"] = position
            entry["generation"] = state["generation"]
            entry["state"] = "QUEUED"
            entry["candidate_sha"] = None
            entry["candidate_ref"] = None
            entry["candidate_created_at"] = None
            entry["member_heads"] = []
            entry["check_run_id"] = None
            entry["check_url"] = None
        state["updated_at"] = self._timestamp()
        self.store.save(state)
        return _LandingOutcome(
            result={
                "schema_version": 1,
                "state": "landed",
                "landed_pull_numbers": landed_pull_numbers,
                "candidate_sha": final_candidate,
                "queue": state,
            },
            landed_sha=final_candidate,
        )

    def land(
        self,
        *,
        project_id: str,
        expected_generation: int,
        expected_base: str,
    ) -> dict[str, Any]:
        return self._land_outcome(
            project_id=project_id,
            expected_generation=expected_generation,
            expected_base=expected_base,
        ).result

    def land_with_identity(
        self,
        *,
        project_id: str,
        expected_generation: int,
        expected_base: str,
    ) -> tuple[dict[str, Any], str]:
        outcome = self._land_outcome(
            project_id=project_id,
            expected_generation=expected_generation,
            expected_base=expected_base,
        )
        return outcome.result, outcome.landed_sha


class RegisteredGitHubMergeQueueBackend(RegisteredGitHubOperations):
    """Exact Git/GitHub adapter used by the provider-neutral queue coordinator."""

    def __init__(
        self,
        projects: ProjectRegistry,
        *,
        verification_workflow: str,
        runner: CommandRunner | None = None,
        gh_config_dir: Path | None = None,
    ) -> None:
        super().__init__(projects, runner=runner, gh_config_dir=gh_config_dir)
        self.verification_workflow = verification_workflow

    def target(self, project_id: str) -> QueueTarget:
        project, repository, remote_url = self._target(project_id)
        return QueueTarget(
            project_id=project.project_id,
            repository=repository,
            local_root=Path(project.local_root),
            remote_url=remote_url,
        )

    def prepare(self, target: QueueTarget, target_branch: str) -> str:
        self._authenticate(target.local_root)
        observed_default = self._default_branch(target.remote_url, target.local_root)
        if observed_default != target_branch:
            raise ToolError(
                f"MERGE_QUEUE_TARGET_MISMATCH: configured {target_branch}, observed {observed_default}"
            )
        default_ref = f"refs/heads/{target_branch}"
        base_sha = self._remote_branch_sha(target.remote_url, default_ref, target.local_root)
        if base_sha is None:
            raise ToolError("MERGE_QUEUE_BASE_UNVERIFIABLE")
        probe = self._run(
            ("git", "cat-file", "-e", f"{base_sha}^{{commit}}"),
            target.local_root,
            allowed_returncodes=frozenset({0, 1, 128}),
        )
        if int(getattr(probe, "returncode", -1)) != 0:
            self._run(
                (
                    *self._git_network_prefix(),
                    "fetch",
                    "--no-tags",
                    "--no-recurse-submodules",
                    "--no-write-fetch-head",
                    target.remote_url,
                    default_ref,
                ),
                target.local_root,
            )
            after = self._remote_branch_sha(
                target.remote_url, default_ref, target.local_root
            )
            if after != base_sha:
                raise ToolError("MERGE_QUEUE_BASE_CHANGED_DURING_MATERIALIZATION")
        return base_sha

    def pull_request(self, target: QueueTarget, pull_number: int) -> PullRequestSnapshot:
        result = self._run(
            (
                "gh", "pr", "view", str(pull_number),
                "--repo", target.repository,
                "--json", "number,url,headRefOid,headRefName,baseRefName,state,isDraft,reviewDecision,mergeStateStatus",
            ),
            target.local_root,
        )
        try:
            payload = json.loads(str(getattr(result, "stdout", "")))
        except json.JSONDecodeError as exc:
            raise ToolError("MERGE_QUEUE_PULL_REQUEST_UNVERIFIABLE") from exc
        if not isinstance(payload, dict):
            raise ToolError("MERGE_QUEUE_PULL_REQUEST_UNVERIFIABLE")
        return PullRequestSnapshot(
            pull_number=int(payload.get("number", pull_number)),
            head_sha=_full_sha(payload.get("headRefOid"), "pull request head"),
            head_ref=str(payload.get("headRefName") or ""),
            base_ref=str(payload.get("baseRefName") or ""),
            state=str(payload.get("state") or ""),
            is_draft=payload.get("isDraft") is True,
            url=str(payload.get("url") or ""),
            review_decision=(str(payload["reviewDecision"]) if payload.get("reviewDecision") else None),
            merge_state_status=(str(payload["mergeStateStatus"]) if payload.get("mergeStateStatus") else None),
        )

    def _materialize_pull_head(
        self, target: QueueTarget, pull_number: int, expected_head: str
    ) -> None:
        probe = self._run(
            ("git", "cat-file", "-e", f"{expected_head}^{{commit}}"),
            target.local_root,
            allowed_returncodes=frozenset({0, 1, 128}),
        )
        if int(getattr(probe, "returncode", -1)) == 0:
            return
        self._run(
            (
                *self._git_network_prefix(),
                "fetch",
                "--no-tags",
                "--no-recurse-submodules",
                "--no-write-fetch-head",
                target.remote_url,
                f"refs/pull/{pull_number}/head",
            ),
            target.local_root,
        )
        verified = self.pull_request(target, pull_number)
        if verified.head_sha != expected_head:
            raise ToolError("MERGE_QUEUE_PULL_HEAD_CHANGED_DURING_MATERIALIZATION")
        self._run(
            ("git", "cat-file", "-e", f"{expected_head}^{{commit}}"),
            target.local_root,
        )

    def build_candidate(
        self,
        target: QueueTarget,
        pull_number: int,
        parent: str,
        head: str,
        message: str,
    ) -> str | None:
        self._materialize_pull_head(target, pull_number, head)
        merge = self._run(
            ("git", "merge-tree", "--write-tree", parent, head),
            target.local_root,
            allowed_returncodes=frozenset({0, 1}),
        )
        if int(getattr(merge, "returncode", -1)) != 0:
            return None
        lines = str(getattr(merge, "stdout", "")).splitlines()
        if not lines:
            raise ToolError("MERGE_QUEUE_CANDIDATE_TREE_UNVERIFIABLE")
        tree_sha = self._require_sha(lines[0].strip(), "candidate tree")
        commit = self._run(
            (
                "git", "commit-tree", tree_sha,
                "-p", parent,
                "-p", head,
                "-m", message,
            ),
            target.local_root,
        )
        return self._require_sha(
            str(getattr(commit, "stdout", "")).strip(), "candidate commit"
        )

    def publish_candidate(
        self, target: QueueTarget, branch: str, candidate_sha: str
    ) -> None:
        branch_name = self._validate_branch(branch, target.local_root)
        ref = f"refs/heads/{branch_name}"
        observed = self._remote_branch_sha(target.remote_url, ref, target.local_root)
        if observed == candidate_sha:
            return
        if observed is not None:
            raise ToolError("MERGE_QUEUE_CANDIDATE_REF_OCCUPIED")
        self.publish_commit(
            project_id=target.project_id,
            commit=candidate_sha,
            branch=branch_name,
            expected_remote_base=None,
            approved=True,
        )

    def candidate_check(
        self, target: QueueTarget, branch: str, candidate_sha: str
    ) -> CandidateCheck:
        result = self._run(
            (
                "gh", "run", "list",
                "--repo", target.repository,
                "--workflow", self.verification_workflow,
                "--branch", branch,
                "--event", "push",
                "--limit", "20",
                "--json", "databaseId,status,conclusion,headSha,url,createdAt,updatedAt",
            ),
            target.local_root,
        )
        try:
            payload = json.loads(str(getattr(result, "stdout", "")))
        except json.JSONDecodeError as exc:
            raise ToolError("MERGE_QUEUE_CHECKS_UNVERIFIABLE") from exc
        if not isinstance(payload, list):
            raise ToolError("MERGE_QUEUE_CHECKS_UNVERIFIABLE")
        exact = [
            item for item in payload
            if isinstance(item, dict)
            and str(item.get("headSha", "")).lower() == candidate_sha.lower()
        ]
        if not exact:
            return CandidateCheck("pending", None, None, None)
        exact.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
        latest = exact[0]
        status = str(latest.get("status") or "").lower()
        conclusion = str(latest.get("conclusion") or "").lower()
        state = "pending"
        if status == "completed":
            state = "success" if conclusion == "success" else "failure"
        return CandidateCheck(
            state=state,
            run_id=str(latest.get("databaseId")) if latest.get("databaseId") is not None else None,
            url=str(latest.get("url")) if latest.get("url") else None,
            observed_at=str(latest.get("updatedAt")) if latest.get("updatedAt") else None,
        )

    def is_ancestor(
        self, target: QueueTarget, ancestor: str, descendant: str
    ) -> bool:
        result = self._run(
            ("git", "merge-base", "--is-ancestor", ancestor, descendant),
            target.local_root,
            allowed_returncodes=frozenset({0, 1}),
        )
        return int(getattr(result, "returncode", -1)) == 0

    def advance_base(
        self,
        target: QueueTarget,
        target_branch: str,
        expected_base: str,
        candidate_sha: str,
    ) -> None:
        self.publish_commit(
            project_id=target.project_id,
            commit=candidate_sha,
            branch=target_branch,
            expected_remote_base=expected_base,
            approved=True,
        )


class RegisteredGitHubMergeQueueOperations:
    """Public registered-repository queue operation boundary."""

    def __init__(
        self,
        projects: ProjectRegistry,
        *,
        settings: MergeQueueSettings | None = None,
        runner: CommandRunner | None = None,
        gh_config_dir: Path | None = None,
        governance_validator: GovernanceValidator | None = None,
        post_land_hooks: PostLandHooks | None = None,
    ) -> None:
        self.settings = settings or load_merge_queue_settings()
        self.backend = RegisteredGitHubMergeQueueBackend(
            projects,
            verification_workflow=self.settings.verification_workflow,
            runner=runner,
            gh_config_dir=gh_config_dir,
        )
        self.coordinator = MergeQueueCoordinator(
            self.settings,
            QueueStateStore(self.settings.state_root, canonical=True),
            self.backend,
        )
        self.governance_validator = governance_validator
        self.post_land_hooks = post_land_hooks

    def _approval(self, approved: bool) -> None:
        self.backend._require_approval(approved)

    def status(self, *, project_id: str) -> dict[str, Any]:
        return self.coordinator.status(project_id=project_id)

    def enqueue(
        self,
        *,
        project_id: str,
        pull_number: int,
        expected_head: str,
        record: Mapping[str, Any],
        trace: Mapping[str, Any],
        approved: bool,
    ) -> dict[str, Any]:
        self._approval(approved)
        if self.governance_validator is None:
            raise ToolError("MERGE_QUEUE_GOVERNANCE_VALIDATOR_REQUIRED")
        governance = self.governance_validator(
            project_id,
            pull_number,
            expected_head,
            record,
            trace,
        )
        result = self.coordinator.enqueue(
            project_id=project_id,
            pull_number=pull_number,
            expected_head=expected_head,
            governance=governance,
        )
        result["governance"] = dict(governance)
        return result

    def reconcile(self, *, project_id: str, approved: bool) -> dict[str, Any]:
        self._approval(approved)
        return self.coordinator.reconcile(project_id=project_id)

    def dequeue(
        self, *, project_id: str, pull_number: int, expected_head: str, approved: bool
    ) -> dict[str, Any]:
        self._approval(approved)
        return self.coordinator.dequeue(
            project_id=project_id,
            pull_number=pull_number,
            expected_head=expected_head,
        )

    def land(
        self,
        *,
        project_id: str,
        expected_generation: int,
        expected_base: str,
        governance: list[Mapping[str, Any]],
        approved: bool,
    ) -> dict[str, Any]:
        self._approval(approved)
        if self.governance_validator is None:
            raise ToolError("MERGE_QUEUE_GOVERNANCE_VALIDATOR_REQUIRED")
        preview = self.coordinator.preview_land(
            project_id=project_id,
            expected_generation=expected_generation,
            expected_base=expected_base,
        )
        evidence_by_pull: dict[int, Mapping[str, Any]] = {}
        for item in governance:
            if not isinstance(item, Mapping):
                raise ToolError("MERGE_QUEUE_GOVERNANCE_EVIDENCE_INVALID")
            pull_number = item.get("pull_number")
            if isinstance(pull_number, bool) or not isinstance(pull_number, int):
                raise ToolError("MERGE_QUEUE_GOVERNANCE_EVIDENCE_INVALID")
            if pull_number in evidence_by_pull:
                raise ToolError("MERGE_QUEUE_GOVERNANCE_EVIDENCE_DUPLICATE")
            evidence_by_pull[pull_number] = item
        selected = {int(entry["pull_number"]): entry for entry in preview["entries"]}
        if set(evidence_by_pull) != set(selected):
            raise ToolError("MERGE_QUEUE_GOVERNANCE_EVIDENCE_MISMATCH")
        receipts = []
        for pull_number, entry in selected.items():
            evidence = evidence_by_pull[pull_number]
            receipt = self.governance_validator(
                project_id,
                pull_number,
                str(entry["head_sha"]),
                evidence.get("record", {}),
                evidence.get("trace", {}),
            )
            receipts.append(dict(receipt))
        target = self.backend.target(project_id)
        result, landed_sha = self.coordinator.land_with_identity(
            project_id=project_id,
            expected_generation=expected_generation,
            expected_base=expected_base,
        )
        dispatch_post_land_non_interfering(
            self.post_land_hooks,
            project_id,
            target.local_root,
            self.settings.target_branch,
            landed_sha,
        )
        result["governance"] = receipts
        return result


REGISTERED_GITHUB_MERGE_QUEUE_OPERATION_SCHEMAS: dict[str, dict[str, object]] = {
    "kis_github_merge_queue_status": {
        "type": "object",
        "properties": {"project_id": {"type": "string"}},
        "required": ["project_id"],
        "additionalProperties": False,
    },
    "kis_github_merge_queue_enqueue": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "pull_number": {"type": "integer", "minimum": 1},
            "expected_head": {"type": "string"},
            "record": {"type": "object"},
            "trace": {"type": "object"},
            "approved": {"type": "boolean"},
        },
        "required": [
            "project_id",
            "pull_number",
            "expected_head",
            "record",
            "trace",
            "approved",
        ],
        "additionalProperties": False,
    },
    "kis_github_merge_queue_reconcile": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "approved": {"type": "boolean"},
        },
        "required": ["project_id", "approved"],
        "additionalProperties": False,
    },
    "kis_github_merge_queue_dequeue": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "pull_number": {"type": "integer", "minimum": 1},
            "expected_head": {"type": "string"},
            "approved": {"type": "boolean"},
        },
        "required": ["project_id", "pull_number", "expected_head", "approved"],
        "additionalProperties": False,
    },
    "kis_github_merge_queue_land": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "expected_generation": {"type": "integer", "minimum": 1},
            "expected_base": {"type": "string"},
            "governance": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "pull_number": {"type": "integer", "minimum": 1},
                        "record": {"type": "object"},
                        "trace": {"type": "object"},
                    },
                    "required": ["pull_number", "record", "trace"],
                    "additionalProperties": False,
                },
            },
            "approved": {"type": "boolean"},
        },
        "required": [
            "project_id",
            "expected_generation",
            "expected_base",
            "governance",
            "approved",
        ],
        "additionalProperties": False,
    },
}


def _validated_arguments(operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    schema = REGISTERED_GITHUB_MERGE_QUEUE_OPERATION_SCHEMAS.get(operation)
    if schema is None:
        raise ToolError(f"UNKNOWN_REGISTERED_GITHUB_MERGE_QUEUE_OPERATION: {operation}")
    if not isinstance(arguments, Mapping):
        raise ToolError("INVALID_ACTION_ARGUMENTS: arguments must be an object")
    values = dict(arguments)
    properties = schema["properties"]
    required = set(schema["required"])
    unknown = sorted(set(values) - set(properties))
    missing = sorted(required - set(values))
    if unknown or missing:
        raise ToolError("INVALID_REGISTERED_GITHUB_MERGE_QUEUE_ARGUMENTS")
    if not isinstance(values.get("project_id"), str) or not values["project_id"].strip():
        raise ToolError("INVALID_REGISTERED_GITHUB_MERGE_QUEUE_ARGUMENTS: project_id")
    if "approved" in required and values.get("approved") is not True:
        raise ToolError("APPROVAL_REQUIRED: approved must be true")
    if "pull_number" in values and (
        isinstance(values["pull_number"], bool)
        or not isinstance(values["pull_number"], int)
        or values["pull_number"] <= 0
    ):
        raise ToolError("INVALID_REGISTERED_GITHUB_MERGE_QUEUE_ARGUMENTS: pull_number")
    if "expected_generation" in values and (
        isinstance(values["expected_generation"], bool)
        or not isinstance(values["expected_generation"], int)
        or values["expected_generation"] <= 0
    ):
        raise ToolError("INVALID_REGISTERED_GITHUB_MERGE_QUEUE_ARGUMENTS: expected_generation")
    for name in ("expected_head", "expected_base"):
        if name in values:
            values[name] = _full_sha(values[name], name)
    for name in ("record", "trace"):
        if name in values and not isinstance(values[name], Mapping):
            raise ToolError(f"INVALID_REGISTERED_GITHUB_MERGE_QUEUE_ARGUMENTS: {name}")
    if "governance" in values:
        if not isinstance(values["governance"], list) or not values["governance"]:
            raise ToolError("INVALID_REGISTERED_GITHUB_MERGE_QUEUE_ARGUMENTS: governance")
    return values


def _runtime_operations() -> RegisteredGitHubMergeQueueOperations:
    runtime = load_runtime_config()
    projects = load_project_registry_settings(boundary=runtime.project_boundary)
    return RegisteredGitHubMergeQueueOperations(
        projects,
        gh_config_dir=Path(runtime.github_cli_config_dir),
    )


def execute_registered_github_merge_queue_operation(
    operation: str,
    arguments: Mapping[str, Any],
    *,
    operations: RegisteredGitHubMergeQueueOperations | None = None,
) -> dict[str, Any]:
    values = _validated_arguments(operation, arguments)
    service = operations or _runtime_operations()
    project_id = values["project_id"]
    if operation == "kis_github_merge_queue_status":
        return service.status(project_id=project_id)
    if operation == "kis_github_merge_queue_enqueue":
        return service.enqueue(
            project_id=project_id,
            pull_number=values["pull_number"],
            expected_head=values["expected_head"],
            record=values["record"],
            trace=values["trace"],
            approved=values["approved"],
        )
    if operation == "kis_github_merge_queue_reconcile":
        return service.reconcile(project_id=project_id, approved=values["approved"])
    if operation == "kis_github_merge_queue_dequeue":
        return service.dequeue(
            project_id=project_id,
            pull_number=values["pull_number"],
            expected_head=values["expected_head"],
            approved=values["approved"],
        )
    return service.land(
        project_id=project_id,
        expected_generation=values["expected_generation"],
        expected_base=values["expected_base"],
        governance=values["governance"],
        approved=values["approved"],
    )


__all__ = [
    "CandidateCheck",
    "MergeQueueCoordinator",
    "MergeQueueSettings",
    "PullRequestSnapshot",
    "QueueStateStore",
    "QueueTarget",
    "REGISTERED_GITHUB_MERGE_QUEUE_OPERATION_SCHEMAS",
    "RegisteredGitHubMergeQueueOperations",
    "execute_registered_github_merge_queue_operation",
    "load_merge_queue_settings",
]
