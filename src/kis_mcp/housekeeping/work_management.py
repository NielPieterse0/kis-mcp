from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import (
    Finding,
    FindingKind,
    FindingSeverity,
    HousekeepingMetrics,
    HousekeepingReceipt,
    HousekeepingTrigger,
    PlannedAction,
    RunMode,
    RunnerKind,
)
from .local_evidence import GovernedWorkLink, governed_work_links
from .operations import OperationInvoker

_TERMINAL = {"done", "superseded", "rejected"}
_ACTIVE = {"ready", "active", "blocked", "approved", "review"}
_REQUIRED_READY = ("Record Type", "Priority", "Effort", "Documentation Impact")
_REF = re.compile(r"(?:(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+))?#(?P<number>[1-9][0-9]*)")


@dataclass(frozen=True, slots=True)
class HousekeepingRunConfig:
    project_id: str
    repository: str
    repository_root: Path
    item_limit: int = 1000
    max_findings: int = 200
    max_mutations: int = 20
    max_external_reads: int = 100

    def __post_init__(self) -> None:
        if not self.project_id.strip() or not self.repository.strip():
            raise ValueError("project_id and repository are required")
        if not 1 <= self.item_limit <= 1000:
            raise ValueError("item_limit must be between 1 and 1000")
        for name in ("max_findings", "max_mutations", "max_external_reads"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


def _field_values(item: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for raw in item.get("field_values", ()):  # normalized KIS inventory
        if isinstance(raw, Mapping) and isinstance(raw.get("field_name"), str):
            result[str(raw["field_name"])] = raw.get("value")
    return result


def _normalized(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().casefold().replace(" ", "_").replace("-", "_")


def _has_blocker(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _source_key(item: Mapping[str, Any]) -> tuple[str, int, str] | None:
    repository = item.get("repository")
    number = item.get("number")
    kind = item.get("kind")
    if not isinstance(repository, str) or not isinstance(number, int):
        return None
    if kind not in {"issue", "pull_request"}:
        return None
    return (repository.casefold(), number, str(kind))


def _source_state(document: Mapping[str, Any]) -> str | None:
    direct = document.get("state")
    if isinstance(direct, str):
        return direct.casefold()
    for key in ("issue", "content", "data"):
        nested = document.get(key)
        if isinstance(nested, Mapping):
            state = nested.get("state")
            if isinstance(state, str):
                return state.casefold()
    return None


def _finding(
    kind: FindingKind,
    severity: FindingSeverity,
    record_id: str,
    summary: str,
    evidence: Mapping[str, Any],
    recommendation: str | None = None,
) -> Finding:
    return Finding(
        kind=kind,
        severity=severity,
        record_id=record_id,
        summary=summary,
        evidence=evidence,
        recommendation=recommendation,
    )


def _record_id(repository: str, number: int) -> str:
    return f"{repository}#{number}"


def _bounded_append(target: list[Finding], finding: Finding, limit: int) -> None:
    if len(target) < limit:
        target.append(finding)


async def _read_source_issue(
    invoker: OperationInvoker,
    repository: str,
    number: int,
) -> dict[str, Any]:
    owner, repo = repository.split("/", 1)
    payload = _provider_json(
        await invoker.external(
            "github_issue_read",
            {"method": "get", "owner": owner, "repo": repo, "issue_number": number},
        )
    )
    if not isinstance(payload, Mapping):
        raise RuntimeError("github_issue_read returned malformed source evidence")
    source = dict(payload)
    state = _source_state(source)
    if state not in {"open", "closed"}:
        raise RuntimeError("github_issue_read returned unusable source lifecycle state")
    return source


def _provider_json(payload: Mapping[str, Any]) -> Any:
    text = payload.get("text")
    if isinstance(text, str):
        return json.loads(text)
    return payload


async def _read_complete_open_issue_numbers(
    invoker: OperationInvoker,
    repository: str,
    *,
    max_reads: int,
) -> tuple[set[int] | None, int]:
    owner, repo = repository.split("/", 1)
    numbers: set[int] = set()
    after: str | None = None
    reads = 0
    while reads < max_reads:
        arguments: dict[str, Any] = {
            "owner": owner,
            "repo": repo,
            "state": "OPEN",
            "perPage": 100,
        }
        if after is not None:
            arguments["after"] = after
        reads += 1
        try:
            payload = _provider_json(
                await invoker.external("github_list_issues", arguments)
            )
        except Exception:
            return None, reads
        if not isinstance(payload, Mapping):
            return None, reads
        issues = payload.get("issues")
        page_info = payload.get("pageInfo")
        if not isinstance(issues, list) or not isinstance(page_info, Mapping):
            return None, reads
        for issue in issues:
            if isinstance(issue, Mapping) and isinstance(issue.get("number"), int):
                numbers.add(int(issue["number"]))
        if page_info.get("hasNextPage") is not True:
            return numbers, reads
        end_cursor = page_info.get("endCursor")
        if not isinstance(end_cursor, str) or not end_cursor:
            return None, reads
        after = end_cursor
    return None, reads


async def _plan_missing_project_record(
    invoker: OperationInvoker,
    config: HousekeepingRunConfig,
    link: GovernedWorkLink,
) -> PlannedAction | None:
    arguments = {
        "project_id": config.project_id,
        "desired": [
            {
                "record_id": f"WORK-{link.source_number}",
                "fields": {},
                "source_repository": link.source_repository,
                "source_number": link.source_number,
                "source_kind": link.source_kind,
            }
        ],
        "observed": [],
        "supported_fields": [],
        "apply": False,
    }
    preview = await invoker.change("project_management_reconcile", arguments)
    outcomes = preview.get("outcomes")
    if not isinstance(outcomes, list) or len(outcomes) != 1:
        return None
    outcome = outcomes[0]
    if not isinstance(outcome, Mapping) or outcome.get("action") not in {"create", "noop"}:
        return None
    return PlannedAction(
        action_id=f"capture:{link.source_repository.casefold()}#{link.source_number}",
        operation="project_management_reconcile",
        arguments=arguments,
        rationale="A unique governed change binds an open source record that is absent from the Project.",
    )


async def _apply_actions(
    invoker: OperationInvoker,
    trigger: HousekeepingTrigger,
    actions: list[PlannedAction],
    max_mutations: int,
) -> tuple[list[Mapping[str, Any]], list[Finding]]:
    if trigger.mode is not RunMode.APPLY:
        return [], []
    receipts: list[Mapping[str, Any]] = []
    failures: list[Finding] = []
    base_key = trigger.idempotency_key or ""
    for index, action in enumerate(actions[:max_mutations]):
        arguments = dict(action.arguments)
        arguments["apply"] = True
        arguments["idempotency_key"] = f"{base_key}:{action.action_id}"
        try:
            result = await invoker.change(action.operation, arguments)
        except Exception as exc:
            failures.append(
                _finding(
                    FindingKind.APPLY_FAILED,
                    FindingSeverity.CONFLICT,
                    action.action_id,
                    "A planned housekeeping mutation failed; the run is incomplete.",
                    {
                        "operation": action.operation,
                        "error_type": type(exc).__name__,
                        "sequence": index + 1,
                    },
                    "Re-run with the same idempotency key after the underlying operation succeeds.",
                )
            )
            break
        receipts.append(
            {
                "action_id": action.action_id,
                "operation": action.operation,
                "result": result,
                "sequence": index + 1,
            }
        )
    return receipts, failures


def _metrics(
    scanned: int,
    findings: list[Finding],
    actions: list[PlannedAction],
    receipts: list[Mapping[str, Any]],
    *,
    source_failures: int = 0,
) -> HousekeepingMetrics:
    return HousekeepingMetrics(
        scanned_records=scanned,
        findings=len(findings),
        safe_actions=len(actions),
        applied_actions=len(receipts),
        conflicts=sum(item.severity is FindingSeverity.CONFLICT for item in findings),
        ambiguities=sum(item.kind in {FindingKind.AMBIGUOUS_DEPENDENCY, FindingKind.DUPLICATE_SOURCE_BINDING} for item in findings),
        source_failures=source_failures,
    )


def _authority_failure_receipt(
    trigger: HousekeepingTrigger,
    config: HousekeepingRunConfig,
    operation: str,
    exc: Exception,
) -> HousekeepingReceipt:
    finding = _finding(
        FindingKind.AUTHORITY_UNAVAILABLE,
        FindingSeverity.CONFLICT,
        config.project_id,
        "An authoritative housekeeping data source is unavailable; the run is fail-closed.",
        {"operation": operation, "error_type": type(exc).__name__},
    )
    return HousekeepingReceipt(
        trigger=trigger,
        project_id=config.project_id,
        repository=config.repository,
        findings=(finding,),
        metrics=_metrics(0, [finding], [], [], source_failures=1),
        complete=False,
        conflicts=("authority_unavailable",),
    )


async def run_work_management_reconciliation(
    invoker: OperationInvoker,
    config: HousekeepingRunConfig,
    trigger: HousekeepingTrigger,
) -> HousekeepingReceipt:
    if trigger.runner is not RunnerKind.WORK_MANAGEMENT_RECONCILIATION:
        raise ValueError("trigger runner does not match reconciliation runner")
    try:
        inventory = await invoker.read(
            "project_management_inventory",
            {
                "project_id": config.project_id,
                "field_names": [
                    "Status", "Record Type", "Priority", "Effort",
                    "Documentation Impact", "Execution Owner", "Change ID", "Blocked By",
                ],
                "item_limit": config.item_limit,
            },
        )
    except Exception as exc:
        return _authority_failure_receipt(
            trigger, config, "project_management_inventory", exc
        )
    raw_items = inventory.get("items", [])
    items = [item for item in raw_items if isinstance(item, Mapping)]
    findings: list[Finding] = []
    actions: list[PlannedAction] = []
    source_failures = 0
    if inventory.get("truncated"):
        findings.append(_finding(
            FindingKind.INVENTORY_INCOMPLETE,
            FindingSeverity.CONFLICT,
            config.project_id,
            "Project inventory is truncated; reconciliation is fail-closed.",
            {"item_limit": config.item_limit},
        ))
        return HousekeepingReceipt(
            trigger=trigger, project_id=config.project_id, repository=config.repository,
            findings=tuple(findings), metrics=_metrics(len(items), findings, actions, []),
            complete=False, conflicts=("inventory_truncated",),
        )
    project_keys = {key for item in items for key in (_source_key(item),) if key is not None}
    links = [
        link for link in governed_work_links(config.repository_root)
        if link.source_repository.casefold() == config.repository.casefold()
    ]
    by_source: dict[tuple[str, int, str], list[GovernedWorkLink]] = {}
    for link in links:
        by_source.setdefault(link.source_key, []).append(link)
    external_reads = 0
    absent_issue_sources = [
        bound_links[0]
        for source_key, bound_links in sorted(by_source.items())
        if source_key not in project_keys
        and len(bound_links) == 1
        and bound_links[0].source_kind == "issue"
    ]
    open_issue_numbers: set[int] | None = None
    if absent_issue_sources and external_reads < config.max_external_reads:
        open_issue_numbers, reads_used = await _read_complete_open_issue_numbers(
            invoker,
            config.repository,
            max_reads=config.max_external_reads - external_reads,
        )
        external_reads += reads_used
    for source_key, bound_links in sorted(by_source.items()):
        if source_key in project_keys:
            continue
        record = _record_id(bound_links[0].source_repository, bound_links[0].source_number)
        if len(bound_links) != 1:
            _bounded_append(findings, _finding(
                FindingKind.DUPLICATE_SOURCE_BINDING, FindingSeverity.CONFLICT, record,
                "Multiple governed changes bind the same source record; capture is ambiguous.",
                {"changes": [item.change_id for item in bound_links]},
            ), config.max_findings)
            continue
        link = bound_links[0]
        if link.source_kind == "issue" and open_issue_numbers is not None:
            if link.source_number not in open_issue_numbers:
                continue
        else:
            if external_reads >= config.max_external_reads:
                source_failures += 1
                continue
            external_reads += 1
            try:
                source = await _read_source_issue(
                    invoker, link.source_repository, link.source_number
                )
            except Exception:
                source_failures += 1
                continue
            if _source_state(source) != "open":
                continue
        _bounded_append(findings, _finding(
            FindingKind.MISSING_PROJECT_RECORD, FindingSeverity.WARNING, record,
            "Open governed work is absent from the Work Management Project.",
            {"change_id": link.change_id, "scope_path": link.scope_path},
            "Capture the exact source record through existing Project reconciliation.",
        ), config.max_findings)
        action = await _plan_missing_project_record(invoker, config, link)
        if action is not None:
            actions.append(action)
    for item in items:
        key = _source_key(item)
        if key is None or key[0] != config.repository.casefold():
            continue
        repository = str(item["repository"])
        number = int(item["number"])
        record = _record_id(repository, number)
        fields = _field_values(item)
        status = _normalized(fields.get("Status"))
        source_state = _normalized(item.get("state"))
        owner = fields.get("Execution Owner")
        change_id = fields.get("Change ID")
        blocker = fields.get("Blocked By")
        local_links = by_source.get(key, [])
        if len(local_links) > 1:
            _bounded_append(findings, _finding(
                FindingKind.DUPLICATE_SOURCE_BINDING,
                FindingSeverity.CONFLICT,
                record,
                "Multiple governed changes bind the same Project source record.",
                {"changes": [link.change_id for link in local_links]},
            ), config.max_findings)
        elif len(local_links) == 1:
            expected_change_id = local_links[0].change_id
            observed_change_id = change_id.strip() if isinstance(change_id, str) and change_id.strip() else None
            if observed_change_id != expected_change_id:
                _bounded_append(findings, _finding(
                    FindingKind.CHANGE_PROJECTION_MISSING,
                    FindingSeverity.CONFLICT,
                    record,
                    "Project Change ID does not match the unique governed source binding.",
                    {
                        "expected_change_id": expected_change_id,
                        "observed_change_id": observed_change_id,
                    },
                    "Use the existing change-classification projection operation after authoritative scope is visible.",
                ), config.max_findings)
        if source_state == "closed" and status in _ACTIVE:
            _bounded_append(findings, _finding(
                FindingKind.SOURCE_CLOSED_PROJECT_ACTIVE,
                FindingSeverity.CONFLICT,
                record,
                "Closed source work is still represented as active in Work Management.",
                {"status": fields.get("Status"), "source_state": item.get("state")},
                "Require exact closeout evidence before terminal reconciliation.",
            ), config.max_findings)
        if source_state == "open" and status in _TERMINAL:
            _bounded_append(findings, _finding(
                FindingKind.PROJECT_DONE_SOURCE_OPEN,
                FindingSeverity.CONFLICT,
                record,
                "Terminal Work Management state conflicts with an open source record.",
                {"status": fields.get("Status"), "source_state": item.get("state")},
            ), config.max_findings)
        if source_state == "closed" and isinstance(owner, str) and owner.strip():
            _bounded_append(findings, _finding(
                FindingKind.STALE_EXECUTION_CLAIM,
                FindingSeverity.CONFLICT,
                record,
                "Closed source work retains an execution owner claim.",
                {"execution_owner": owner.strip()},
                "Release only after lifecycle authority confirms the correct destination state.",
            ), config.max_findings)
        if isinstance(change_id, str) and change_id.strip():
            scope = config.repository_root / ".work" / "changes" / change_id.strip() / "scope.json"
            if not scope.is_file():
                _bounded_append(findings, _finding(
                    FindingKind.CHANGE_PROJECTION_MISSING,
                    FindingSeverity.CONFLICT,
                    record,
                    "Work Management references a governed change that is absent locally.",
                    {"change_id": change_id.strip()},
                ), config.max_findings)
        if status in {"ready", "active"}:
            missing = [name for name in _REQUIRED_READY if fields.get(name) in (None, "")]
            if missing:
                _bounded_append(findings, _finding(
                    FindingKind.MISSING_READY_METADATA,
                    FindingSeverity.CONFLICT,
                    record,
                    "Ready/Active work is missing command-plane readiness metadata.",
                    {"missing_fields": missing},
                ), config.max_findings)
        if status == "blocked" and not _has_blocker(blocker):
            _bounded_append(findings, _finding(
                FindingKind.BLOCKED_WITHOUT_DEPENDENCY, FindingSeverity.WARNING, record,
                "Blocked work has no observed native dependency evidence.",
                {"status": fields.get("Status")},
            ), config.max_findings)
        if _has_blocker(blocker) and status not in {"blocked", "on_hold"}:
            _bounded_append(findings, _finding(
                FindingKind.DEPENDENCY_WITHOUT_BLOCKED_STATE,
                FindingSeverity.WARNING,
                record,
                "Native dependency evidence exists while the lifecycle state is executable.",
                {"status": fields.get("Status"), "blocked_by": blocker},
            ), config.max_findings)

    complete = source_failures == 0
    conflicts: tuple[str, ...] = ()
    if not complete:
        _bounded_append(findings, _finding(
            FindingKind.SOURCE_EVIDENCE_INCOMPLETE,
            FindingSeverity.CONFLICT,
            config.project_id,
            "The bounded source-evidence scan did not complete; apply is suppressed.",
            {"source_failures": source_failures, "max_external_reads": config.max_external_reads},
        ), config.max_findings)
        conflicts = ("source_evidence_incomplete",)
    receipts: list[Mapping[str, Any]] = []
    apply_failures: list[Finding] = []
    if complete:
        receipts, apply_failures = await _apply_actions(
            invoker, trigger, actions, config.max_mutations
        )
    if apply_failures:
        for failure in apply_failures:
            _bounded_append(findings, failure, config.max_findings)
        complete = False
        conflicts = (*conflicts, "apply_failed")
    return HousekeepingReceipt(
        trigger=trigger,
        project_id=config.project_id,
        repository=config.repository,
        findings=tuple(findings),
        actions=tuple(actions),
        applied_receipts=tuple(receipts),
        metrics=_metrics(
            len(items), findings, actions, receipts, source_failures=source_failures
        ),
        complete=complete,
        conflicts=conflicts,
    )


def _dependency_refs(
    value: Any, default_repository: str
) -> tuple[tuple[str, int], ...] | None:
    if not isinstance(value, str) or not value.strip():
        return ()
    tokens = [item.strip() for item in re.split(r"[,;]", value) if item.strip()]
    if not tokens:
        return ()
    refs: list[tuple[str, int]] = []
    for token in tokens:
        match = _REF.fullmatch(token)
        if match is None:
            return None
        owner = match.group("owner")
        repo = match.group("repo")
        repository = f"{owner}/{repo}" if owner and repo else default_repository
        refs.append((repository, int(match.group("number"))))
    return tuple(sorted(set(refs), key=lambda item: (item[0].casefold(), item[1])))


async def _preview_ready_transition(
    invoker: OperationInvoker,
    config: HousekeepingRunConfig,
    repository: str,
    number: int,
) -> PlannedAction | None:
    arguments = {
        "project_id": config.project_id,
        "repository": repository,
        "issue_number": number,
        "target": "ready",
        "metadata": {},
        "apply": False,
    }
    try:
        preview = await invoker.change("project_management_transition_work", arguments)
    except Exception:
        return None
    outcomes = preview.get("outcomes")
    if not isinstance(outcomes, list) or not outcomes:
        return None
    if any(not isinstance(item, Mapping) or item.get("success") is False for item in outcomes):
        return None
    return PlannedAction(
        action_id=f"ready:{repository.casefold()}#{number}",
        operation="project_management_transition_work",
        arguments=arguments,
        rationale=(
            "The item is Blocked without observed dependency evidence and the existing "
            "Work Management transition gate accepts returning it to Ready."
        ),
    )


async def run_backlog_readiness(
    invoker: OperationInvoker,
    config: HousekeepingRunConfig,
    trigger: HousekeepingTrigger,
) -> HousekeepingReceipt:
    if trigger.runner is not RunnerKind.BACKLOG_READINESS:
        raise ValueError("trigger runner does not match backlog readiness runner")
    try:
        inventory = await invoker.read(
            "project_management_inventory",
            {
                "project_id": config.project_id,
                "field_names": [
                    "Status", "Record Type", "Priority", "Effort",
                    "Documentation Impact", "Execution Owner", "Blocked By",
                ],
                "item_limit": config.item_limit,
            },
        )
    except Exception as exc:
        return _authority_failure_receipt(
            trigger, config, "project_management_inventory", exc
        )
    raw_items = inventory.get("items", [])
    items = [item for item in raw_items if isinstance(item, Mapping)]
    findings: list[Finding] = []
    actions: list[PlannedAction] = []
    source_failures = 0
    if inventory.get("truncated"):
        findings.append(_finding(
            FindingKind.INVENTORY_INCOMPLETE,
            FindingSeverity.CONFLICT,
            config.project_id,
            "Project inventory is truncated; readiness recomputation is fail-closed.",
            {"item_limit": config.item_limit},
        ))
        return HousekeepingReceipt(
            trigger=trigger,
            project_id=config.project_id,
            repository=config.repository,
            findings=tuple(findings),
            metrics=_metrics(len(items), findings, actions, []),
            complete=False,
            conflicts=("inventory_truncated",),
        )
    try:
        selection = await invoker.read(
            "project_management_next_work",
            {"project_id": config.project_id, "item_limit": config.item_limit},
        )
    except Exception as exc:
        return _authority_failure_receipt(
            trigger, config, "project_management_next_work", exc
        )
    external_reads = 0
    dependency_state_cache: dict[tuple[str, int], str] = {}
    for item in items:
        key = _source_key(item)
        if key is None or key[0] != config.repository.casefold():
            continue
        repository = str(item["repository"])
        number = int(item["number"])
        record = _record_id(repository, number)
        fields = _field_values(item)
        status = _normalized(fields.get("Status"))
        blocker = fields.get("Blocked By")
        owner = fields.get("Execution Owner")
        source_state = _normalized(item.get("state"))
        if status == "blocked" and not _has_blocker(blocker):
            _bounded_append(findings, _finding(
                FindingKind.BLOCKED_WITHOUT_DEPENDENCY,
                FindingSeverity.WARNING,
                record,
                "Blocked work has no observed native dependency evidence.",
                {"status": fields.get("Status")},
                "Return to Ready only if the existing Work Management transition gate permits it.",
            ), config.max_findings)
            if source_state == "open" and not (isinstance(owner, str) and owner.strip()):
                action = await _preview_ready_transition(invoker, config, repository, number)
                if action is not None:
                    actions.append(action)
            continue
        if not _has_blocker(blocker):
            continue
        refs = _dependency_refs(blocker, repository)
        if refs is None:
            _bounded_append(findings, _finding(
                FindingKind.AMBIGUOUS_DEPENDENCY,
                FindingSeverity.CONFLICT,
                record,
                "Blocked By contains semantic text that cannot be reconciled mechanically.",
                {"blocked_by": blocker},
                "Resolve the dependency relationship explicitly; do not infer it.",
            ), config.max_findings)
            continue
        if status not in {"blocked", "on_hold"}:
            _bounded_append(findings, _finding(
                FindingKind.DEPENDENCY_WITHOUT_BLOCKED_STATE,
                FindingSeverity.WARNING,
                record,
                "Dependency evidence exists while lifecycle state is not Blocked/On Hold.",
                {"blocked_by": blocker, "status": fields.get("Status")},
            ), config.max_findings)
        if not refs:
            _bounded_append(findings, _finding(
                FindingKind.AMBIGUOUS_DEPENDENCY,
                FindingSeverity.CONFLICT,
                record,
                "Blocked By is non-empty but contains no exact issue references.",
                {"blocked_by": blocker},
            ), config.max_findings)
            continue
        states: list[str] = []
        failed = False
        for dependency_repository, dependency_number in refs:
            dependency_key = (dependency_repository.casefold(), dependency_number)
            cached_state = dependency_state_cache.get(dependency_key)
            if cached_state is not None:
                states.append(cached_state)
                continue
            if external_reads >= config.max_external_reads:
                source_failures += 1
                failed = True
                break
            external_reads += 1
            try:
                source = await _read_source_issue(
                    invoker, dependency_repository, dependency_number
                )
            except Exception:
                source_failures += 1
                failed = True
                break
            state = _source_state(source)
            if state is None:
                source_failures += 1
                failed = True
                break
            dependency_state_cache[dependency_key] = state
            states.append(state)
        if not failed and states and all(state == "closed" for state in states):
            _bounded_append(findings, _finding(
                FindingKind.RESOLVED_DEPENDENCY_STILL_BLOCKING,
                FindingSeverity.WARNING,
                record,
                "Every exact dependency reference is closed but Blocked By remains populated.",
                {"blocked_by": blocker, "dependency_states": states},
                "Reconcile native dependency evidence before changing lifecycle state.",
            ), config.max_findings)

    selection_complete = selection.get("complete", True) is not False
    source_complete = source_failures == 0
    conflicts: list[str] = []
    if not selection_complete:
        conflicts.append("next_work_incomplete")
    if not source_complete:
        _bounded_append(findings, _finding(
            FindingKind.SOURCE_EVIDENCE_INCOMPLETE,
            FindingSeverity.CONFLICT,
            config.project_id,
            "The bounded dependency-evidence scan did not complete; apply is suppressed.",
            {"source_failures": source_failures, "max_external_reads": config.max_external_reads},
        ), config.max_findings)
        conflicts.append("source_evidence_incomplete")
    complete = selection_complete and source_complete
    receipts: list[Mapping[str, Any]] = []
    apply_failures: list[Finding] = []
    if complete:
        receipts, apply_failures = await _apply_actions(
            invoker, trigger, actions, config.max_mutations
        )
    if apply_failures:
        for failure in apply_failures:
            _bounded_append(findings, failure, config.max_findings)
        complete = False
        conflicts.append("apply_failed")
    return HousekeepingReceipt(
        trigger=trigger,
        project_id=config.project_id,
        repository=config.repository,
        findings=tuple(findings),
        actions=tuple(actions),
        applied_receipts=tuple(receipts),
        metrics=_metrics(
            len(items), findings, actions, receipts, source_failures=source_failures
        ),
        selection=selection,
        complete=complete,
        conflicts=tuple(conflicts),
    )


__all__ = [
    "HousekeepingRunConfig",
    "run_backlog_readiness",
    "run_work_management_reconciliation",
]
