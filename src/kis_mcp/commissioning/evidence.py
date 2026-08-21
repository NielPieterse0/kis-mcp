from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .models import LandedChangeEvidence
from .settings import PostMergeCommissioningSettings, PostMergeTargetSettings

_ISSUE_MARKER = re.compile(r"^Issue:\s+#([1-9][0-9]*)\s*$", re.MULTILINE)
_CHANGE_MARKER = re.compile(
    r"^Change:\s+([0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*)\s*$",
    re.MULTILINE,
)
_SHA = re.compile(r"^[0-9a-fA-F]{40}$")


class ExternalOperationInvoker(Protocol):
    async def external(self, operation: str, arguments: dict[str, Any]) -> Any: ...


class MergeEvidenceError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _repository_parts(repository: str) -> tuple[str, str]:
    parts = repository.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise MergeEvidenceError("repository_invalid", "repository must be owner/name")
    return parts[0], parts[1]


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise MergeEvidenceError("provider_evidence_invalid", f"{label} is missing")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise MergeEvidenceError(
            "provider_evidence_invalid", f"{label} is not an ISO timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise MergeEvidenceError(
            "provider_evidence_invalid", f"{label} must include timezone evidence"
        )
    return parsed.astimezone(UTC)


def _mapping(value: Any, code: str, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MergeEvidenceError(code, f"{label} must be an object")
    return value


def _sequence(value: Any, code: str, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise MergeEvidenceError(code, f"{label} must be an array")
    return value


def _parse_markers(body: Any) -> tuple[int, str]:
    if not isinstance(body, str):
        raise MergeEvidenceError("pr_markers_invalid", "pull request body is missing")
    issues = _ISSUE_MARKER.findall(body)
    changes = _CHANGE_MARKER.findall(body)
    if len(issues) != 1 or len(changes) != 1:
        raise MergeEvidenceError(
            "pr_markers_invalid",
            "pull request body requires exactly one Issue and one Change marker",
        )
    return int(issues[0]), changes[0]


def _merge_message_matches(message: Any, pull_number: int) -> bool:
    if not isinstance(message, str):
        return False
    first_line = message.splitlines()[0] if message.splitlines() else ""
    return re.fullmatch(
        rf"Merge pull request #{pull_number} from .+",
        first_line,
    ) is not None


def _scope_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, Mapping):
        for key in ("content", "text"):
            content = value.get(key)
            if isinstance(content, str):
                if value.get("encoding") == "base64":
                    try:
                        return base64.b64decode(content, validate=True).decode("utf-8")
                    except (ValueError, UnicodeDecodeError) as exc:
                        raise MergeEvidenceError(
                            "scope_invalid", "scope content has invalid base64 encoding"
                        ) from exc
                return content
        for key in ("data", "file", "result"):
            nested = value.get(key)
            if nested is not None:
                try:
                    return _scope_text(nested)
                except MergeEvidenceError:
                    pass
    raise MergeEvidenceError(
        "scope_invalid", "provider result did not expose readable scope content"
    )


def _scope_document(text: str) -> Mapping[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MergeEvidenceError("scope_invalid", "landed scope is not valid JSON") from exc
    if not isinstance(value, Mapping) or value.get("schema_version") != 4:
        raise MergeEvidenceError("scope_invalid", "landed scope must be schema_version 4")
    return value


def _validate_scope_identity(
    scope: Mapping[str, Any],
    *,
    change_id: str,
    repository: str,
    source_issue: int,
) -> tuple[str, ...]:
    if scope.get("change_id") != change_id:
        raise MergeEvidenceError(
            "scope_identity_mismatch", "landed scope change_id does not match PR marker"
        )
    work = scope.get("work_management")
    if not isinstance(work, Mapping):
        raise MergeEvidenceError(
            "scope_identity_mismatch", "landed scope has no Work Management identity"
        )
    if str(work.get("source_repository", "")).casefold() != repository.casefold():
        raise MergeEvidenceError(
            "scope_identity_mismatch", "landed scope repository does not match observed repository"
        )
    if work.get("source_number") != source_issue or work.get("source_kind") != "issue":
        raise MergeEvidenceError(
            "scope_identity_mismatch", "landed scope source issue identity does not match PR marker"
        )
    risks = scope.get("risk_triggers")
    if not isinstance(risks, Sequence) or isinstance(risks, (str, bytes, bytearray)):
        raise MergeEvidenceError("scope_invalid", "landed scope risk_triggers must be an array")
    if any(not isinstance(item, str) or not item for item in risks):
        raise MergeEvidenceError("scope_invalid", "landed scope risk_triggers are invalid")
    return tuple(sorted(set(risks)))


class MergedChangeResolver:
    def __init__(
        self,
        invoker: ExternalOperationInvoker,
        settings: PostMergeCommissioningSettings,
    ) -> None:
        self._invoker = invoker
        self._settings = settings

    def _target(self, repository: str) -> PostMergeTargetSettings:
        for target in self._settings.targets:
            if target.repository.casefold() == repository.casefold():
                return target
        raise MergeEvidenceError(
            "repository_not_configured", f"repository is not a commissioning target: {repository}"
        )

    async def _merge_sha(
        self,
        *,
        owner: str,
        repo: str,
        branch: str,
        merged_at: datetime,
        pull_number: int,
    ) -> str:
        window = timedelta(seconds=self._settings.overlap_seconds)
        matches: list[Mapping[str, Any]] = []
        page = 1
        while True:
            commits_value = await self._invoker.external(
                "github_list_commits",
                {
                    "owner": owner,
                    "repo": repo,
                    "sha": branch,
                    "since": (merged_at - window).isoformat().replace("+00:00", "Z"),
                    "until": (merged_at + window).isoformat().replace("+00:00", "Z"),
                    "perPage": 100,
                    "page": page,
                    "fields": ["sha", "commit"],
                },
            )
            commits = _sequence(commits_value, "provider_evidence_invalid", "commit list")
            if len(commits) > 100:
                raise MergeEvidenceError(
                    "provider_evidence_invalid", "commit page exceeds provider bound"
                )
            for value in commits:
                commit = _mapping(value, "provider_evidence_invalid", "commit list item")
                details = commit.get("commit")
                if isinstance(details, Mapping) and _merge_message_matches(
                    details.get("message"), pull_number
                ):
                    matches.append(commit)
            if len(commits) < 100:
                break
            page += 1
        if not matches:
            raise MergeEvidenceError(
                "merge_commit_missing", "default-branch commit stream has no merge commit for PR"
            )
        if len(matches) != 1:
            raise MergeEvidenceError(
                "merge_commit_ambiguous", "default-branch commit stream has multiple PR merge commits"
            )
        merge_sha = matches[0].get("sha")
        if not isinstance(merge_sha, str) or _SHA.fullmatch(merge_sha) is None:
            raise MergeEvidenceError(
                "provider_evidence_invalid", "resolved merge commit has invalid SHA"
            )
        return merge_sha.casefold()

    async def _changed_paths(self, *, owner: str, repo: str, merge_sha: str) -> tuple[str, ...]:
        paths: set[str] = set()
        page = 1
        while True:
            commit_value = await self._invoker.external(
                "github_get_commit",
                {
                    "owner": owner,
                    "repo": repo,
                    "sha": merge_sha,
                    "detail": "stats",
                    "perPage": 100,
                    "page": page,
                },
            )
            commit = _mapping(commit_value, "provider_evidence_invalid", "merge commit")
            if commit.get("sha") != merge_sha:
                raise MergeEvidenceError(
                    "provider_evidence_invalid",
                    "merge commit read did not preserve exact SHA identity",
                )
            files = _sequence(commit.get("files"), "provider_evidence_invalid", "merge files")
            if len(files) > 100:
                raise MergeEvidenceError(
                    "provider_evidence_invalid", "merge file page exceeds provider bound"
                )
            for value in files:
                item = _mapping(value, "provider_evidence_invalid", "merge file")
                filename = item.get("filename")
                if not isinstance(filename, str) or not filename:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid", "merge file has invalid filename"
                    )
                paths.add(filename)
            if len(files) < 100:
                break
            page += 1
        if not paths:
            raise MergeEvidenceError(
                "provider_evidence_invalid", "merge commit has no changed-file evidence"
            )
        return tuple(sorted(paths))

    async def resolve(self, repository: str, pull_number: int) -> LandedChangeEvidence:
        target = self._target(repository)
        owner, repo = _repository_parts(target.repository)
        pr_value = await self._invoker.external(
            "github_pull_request_read",
            {
                "method": "get",
                "owner": owner,
                "repo": repo,
                "pullNumber": pull_number,
            },
        )
        pr = _mapping(pr_value, "provider_evidence_invalid", "pull request")
        if pr.get("merged") is not True:
            raise MergeEvidenceError("pr_not_merged", "pull request is closed or open but not merged")
        source_issue, change_id = _parse_markers(pr.get("body"))
        merged_at = _parse_time(pr.get("merged_at"), "merged_at")
        merge_sha = await self._merge_sha(
            owner=owner,
            repo=repo,
            branch=target.default_branch,
            merged_at=merged_at,
            pull_number=pull_number,
        )
        changed_paths = await self._changed_paths(
            owner=owner,
            repo=repo,
            merge_sha=merge_sha,
        )
        scope_path = f".work/changes/{change_id}/scope.json"
        if scope_path not in changed_paths:
            raise MergeEvidenceError(
                "scope_identity_mismatch",
                "landed scope path was not changed by the observed merge commit",
            )
        scope_value = await self._invoker.external(
            "github_get_file_contents",
            {
                "owner": owner,
                "repo": repo,
                "path": scope_path,
                "sha": merge_sha,
            },
        )
        scope = _scope_document(_scope_text(scope_value))
        risks = _validate_scope_identity(
            scope,
            change_id=change_id,
            repository=target.repository,
            source_issue=source_issue,
        )
        return LandedChangeEvidence(
            repository=target.repository,
            source_issue=source_issue,
            source_pr=pull_number,
            merge_sha=merge_sha.casefold(),
            change_id=change_id,
            changed_paths=changed_paths,
            risk_triggers=risks,
        )


__all__ = ["MergeEvidenceError", "MergedChangeResolver"]
