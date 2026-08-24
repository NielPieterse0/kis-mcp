from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .models import LandedChangeEvidence
from .settings import PostMergeCommissioningSettings, PostMergeTargetSettings

_CHANGE_ID = r"([0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*)"
_SCOPE_PATH = re.compile(rf"^\.work/changes/{_CHANGE_ID}/scope\.json$")
_CHANGE_BRANCH = re.compile(rf"^change/{_CHANGE_ID}$")
_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
_MAX_CHANGED_FILES = 3_000
_MAX_MERGE_COMMIT_PAGES = 30
_MAX_SCOPE_BYTES = 1_048_576
_MAX_SCOPE_WRAPPER_DEPTH = 4
_MAX_SCOPE_TREE_ENTRIES = 16
# Live acceptance proved second-level provider/Git drift; one minute is the fail-closed sanity bound.
_MAX_MERGE_TIME_DRIFT = timedelta(minutes=1)


class ExternalOperationInvoker(Protocol):
    async def external(self, operation: str, arguments: dict[str, Any]) -> Any: ...
    async def read(self, operation: str, arguments: dict[str, Any]) -> Any: ...


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


def _merge_message_matches(
    message: Any,
    pull_number: int,
    *,
    head_owner: str,
    head_ref: str,
) -> bool:
    if not isinstance(message, str):
        return False
    first_line = message.splitlines()[0] if message.splitlines() else ""
    return first_line == f"Merge pull request #{pull_number} from {head_owner}/{head_ref}"


def _scope_content(value: Any) -> tuple[str, bytes]:
    current = value
    seen: set[int] = set()
    max_base64_chars = ((_MAX_SCOPE_BYTES + 2) // 3) * 4
    for _ in range(_MAX_SCOPE_WRAPPER_DEPTH + 1):
        if isinstance(current, str):
            if len(current) > _MAX_SCOPE_BYTES:
                raise MergeEvidenceError(
                    "provider_evidence_invalid",
                    "scope provider content exceeds size limit",
                )
            raw = current.encode("utf-8")
            if len(raw) > _MAX_SCOPE_BYTES:
                raise MergeEvidenceError(
                    "provider_evidence_invalid",
                    "scope provider content exceeds size limit",
                )
            return current, raw
        if isinstance(current, bytes):
            if len(current) > _MAX_SCOPE_BYTES:
                raise MergeEvidenceError(
                    "provider_evidence_invalid",
                    "scope provider content exceeds size limit",
                )
            try:
                return current.decode("utf-8"), current
            except UnicodeDecodeError as exc:
                raise MergeEvidenceError(
                    "provider_evidence_invalid", "scope provider bytes are not UTF-8"
                ) from exc
        if not isinstance(current, Mapping):
            break
        marker = id(current)
        if marker in seen:
            raise MergeEvidenceError(
                "provider_evidence_invalid", "scope provider wrapper cycle detected"
            )
        seen.add(marker)
        for key in ("content", "text"):
            content = current.get(key)
            if isinstance(content, str):
                if current.get("encoding") == "base64":
                    if len(content) > max_base64_chars:
                        raise MergeEvidenceError(
                            "provider_evidence_invalid",
                            "scope provider content exceeds size limit",
                        )
                    try:
                        raw = base64.b64decode(content, validate=True)
                        if len(raw) > _MAX_SCOPE_BYTES:
                            raise MergeEvidenceError(
                                "provider_evidence_invalid",
                                "scope provider content exceeds size limit",
                            )
                        return raw.decode("utf-8"), raw
                    except (ValueError, UnicodeDecodeError) as exc:
                        raise MergeEvidenceError(
                            "provider_evidence_invalid",
                            "scope provider content has invalid base64 or UTF-8 encoding",
                        ) from exc
                if len(content) > _MAX_SCOPE_BYTES:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid",
                        "scope provider content exceeds size limit",
                    )
                raw = content.encode("utf-8")
                if len(raw) > _MAX_SCOPE_BYTES:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid",
                        "scope provider content exceeds size limit",
                    )
                return content, raw
        nested = next(
            (current.get(key) for key in ("data", "file", "result") if current.get(key) is not None),
            None,
        )
        if nested is None:
            break
        current = nested
    if isinstance(current, Mapping):
        raise MergeEvidenceError(
            "provider_evidence_invalid", "scope provider wrapper depth exceeds limit"
        )
    raise MergeEvidenceError(
        "provider_evidence_invalid",
        "provider result did not expose readable scope content",
    )


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def _scope_document(text: str) -> Mapping[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MergeEvidenceError("scope_invalid", "landed scope is not valid JSON") from exc
    except RecursionError as exc:
        raise MergeEvidenceError(
            "scope_invalid", "landed scope nesting exceeds parser limit"
        ) from exc
    if not isinstance(value, Mapping) or value.get("schema_version") != 4:
        raise MergeEvidenceError("scope_invalid", "landed scope must be schema_version 4")
    return value


def _validate_scope_identity(
    scope: Mapping[str, Any],
    *,
    change_id: str,
    repository: str,
) -> tuple[int, tuple[str, ...]]:
    if scope.get("change_id") != change_id:
        raise MergeEvidenceError(
            "scope_identity_mismatch", "landed scope change_id does not match changed scope path"
        )
    if scope.get("branch") != f"change/{change_id}":
        raise MergeEvidenceError(
            "scope_identity_mismatch",
            "landed scope branch does not match governed change branch",
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
    source_issue = work.get("source_number")
    if type(source_issue) is not int or source_issue <= 0 or work.get("source_kind") != "issue":
        raise MergeEvidenceError(
            "scope_identity_mismatch", "landed scope source issue identity is invalid"
        )
    risks = scope.get("risk_triggers")
    if not isinstance(risks, Sequence) or isinstance(risks, (str, bytes, bytearray)):
        raise MergeEvidenceError("scope_invalid", "landed scope risk_triggers must be an array")
    if any(not isinstance(item, str) or not item for item in risks):
        raise MergeEvidenceError("scope_invalid", "landed scope risk_triggers are invalid")
    return source_issue, tuple(sorted(set(risks)))


def _scope_candidate(changed_paths: Sequence[str]) -> tuple[str, str]:
    candidates = [
        (path, match.group(1))
        for path in changed_paths
        if (match := _SCOPE_PATH.fullmatch(path)) is not None
    ]
    if not candidates:
        raise MergeEvidenceError(
            "scope_path_missing", "merge commit changed no canonical governed scope path"
        )
    if len(candidates) != 1:
        raise MergeEvidenceError(
            "scope_path_ambiguous", "merge commit changed multiple canonical governed scope paths"
        )
    return candidates[0]


def _pr_change_binding(
    pr: Mapping[str, Any], repository: str
) -> tuple[str, str, str]:
    head = _mapping(pr.get("head"), "provider_evidence_invalid", "pull request head")
    head_ref = head.get("ref")
    if not isinstance(head_ref, str) or not head_ref:
        raise MergeEvidenceError(
            "provider_evidence_invalid", "pull request head ref is missing"
        )
    head_repo = _mapping(
        head.get("repo"), "provider_evidence_invalid", "pull request head repository"
    )
    full_name = head_repo.get("full_name")
    if not isinstance(full_name, str) or not full_name:
        raise MergeEvidenceError(
            "provider_evidence_invalid", "pull request head repository is missing"
        )
    if full_name.casefold() != repository.casefold():
        raise MergeEvidenceError(
            "provider_evidence_invalid",
            "pull request head repository does not match governed repository",
        )
    branch_match = _CHANGE_BRANCH.fullmatch(head_ref)
    if branch_match is None:
        raise MergeEvidenceError(
            "provider_evidence_invalid",
            "pull request head ref is not a governed change branch",
        )
    head_owner = full_name.split("/", 1)[0]
    return branch_match.group(1), head_owner, head_ref


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

    async def _source_commit_shas(
        self,
        *,
        owner: str,
        repo: str,
        pull_number: int,
    ) -> frozenset[str]:
        shas: set[str] = set()
        page = 1
        while True:
            value = await self._invoker.external(
                "github_pull_request_read",
                {
                    "method": "get_commits",
                    "owner": owner,
                    "repo": repo,
                    "pullNumber": pull_number,
                    "perPage": 100,
                    "page": page,
                },
            )
            commits = _sequence(value, "provider_evidence_invalid", "pull request commits")
            if len(commits) > 100 or (page == 1 and not commits):
                raise MergeEvidenceError(
                    "provider_evidence_invalid", "pull request commit page has invalid bounded size"
                )
            for value in commits:
                commit = _mapping(value, "provider_evidence_invalid", "pull request commit")
                sha = commit.get("sha")
                if not isinstance(sha, str) or _SHA.fullmatch(sha) is None:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid", "pull request commit has invalid SHA"
                    )
                normalized = sha.casefold()
                if normalized in shas:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid", "pull request commit pagination repeated a SHA"
                    )
                shas.add(normalized)
                if len(shas) > 250:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid", "pull request commit count exceeds provider bound"
                    )
            if len(commits) < 100:
                break
            page += 1
        return frozenset(shas)

    async def _merge_sha(
        self,
        *,
        owner: str,
        repo: str,
        branch: str,
        merged_at: datetime,
        pull_number: int,
        head_owner: str,
        head_ref: str,
        source_commit_shas: frozenset[str],
    ) -> str:
        window = timedelta(seconds=self._settings.overlap_seconds)
        matches: list[Mapping[str, Any]] = []
        seen_shas: set[str] = set()
        page = 1
        while True:
            if page > _MAX_MERGE_COMMIT_PAGES:
                raise MergeEvidenceError(
                    "provider_evidence_invalid",
                    "default-branch commit pagination exceeds local bound",
                )
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
                    "fields": ["sha", "commit", "committer"],
                },
            )
            commits = _sequence(commits_value, "provider_evidence_invalid", "commit list")
            if len(commits) > 100:
                raise MergeEvidenceError(
                    "provider_evidence_invalid", "commit page exceeds provider bound"
                )
            for value in commits:
                commit = _mapping(value, "provider_evidence_invalid", "commit list item")
                candidate_sha = commit.get("sha")
                if not isinstance(candidate_sha, str) or _SHA.fullmatch(candidate_sha) is None:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid", "default-branch commit has invalid SHA"
                    )
                normalized_sha = candidate_sha.casefold()
                if normalized_sha in seen_shas:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid",
                        "default-branch commit pagination repeated a SHA",
                    )
                seen_shas.add(normalized_sha)
                if normalized_sha in source_commit_shas:
                    continue
                details = commit.get("commit")
                if not isinstance(details, Mapping) or not _merge_message_matches(
                    details.get("message"),
                    pull_number,
                    head_owner=head_owner,
                    head_ref=head_ref,
                ):
                    continue
                provider_committer = commit.get("committer")
                git_committer = details.get("committer")
                if not isinstance(provider_committer, Mapping) or not isinstance(
                    git_committer, Mapping
                ):
                    continue
                try:
                    committed_at = _parse_time(
                        git_committer.get("date"), "merge commit committer date"
                    )
                except MergeEvidenceError:
                    continue
                if provider_committer.get("login") != "web-flow":
                    continue
                if abs(committed_at - merged_at) >= _MAX_MERGE_TIME_DRIFT:
                    continue
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

    async def _changed_paths(
        self,
        *,
        owner: str,
        repo: str,
        merge_sha: str,
        expected_count: int,
    ) -> tuple[str, ...]:
        paths: set[str] = set()
        page = 1
        while len(paths) < expected_count:
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
            if not files or len(files) > 100:
                raise MergeEvidenceError(
                    "provider_evidence_invalid", "merge file page has invalid bounded size"
                )
            for value in files:
                item = _mapping(value, "provider_evidence_invalid", "merge file")
                filename = item.get("filename")
                if not isinstance(filename, str) or not filename:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid", "merge file has invalid filename"
                    )
                if filename in paths:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid",
                        "merge file pagination repeated a changed filename",
                    )
                paths.add(filename)
                if len(paths) > expected_count:
                    raise MergeEvidenceError(
                        "provider_evidence_invalid",
                        "merge commit file enumeration exceeds pull request changed_files",
                    )
            if len(paths) == expected_count:
                break
            if len(files) < 100:
                raise MergeEvidenceError(
                    "provider_evidence_invalid",
                    "merge commit file enumeration ended before pull request changed_files",
                )
            page += 1
        return tuple(sorted(paths))

    async def _scope_blob_sha(
        self,
        *,
        owner: str,
        repo: str,
        merge_sha: str,
        scope_path: str,
    ) -> str:
        tree_value = await self._invoker.external(
            "github_get_repository_tree",
            {
                "owner": owner,
                "repo": repo,
                "tree_sha": merge_sha,
                "recursive": True,
                "path_filter": scope_path,
            },
        )
        tree = _mapping(tree_value, "provider_evidence_invalid", "merge tree")
        if (
            tree.get("sha") != merge_sha
            or tree.get("tree_sha") != merge_sha
            or tree.get("truncated") is not False
        ):
            raise MergeEvidenceError(
                "provider_evidence_invalid",
                "merge tree did not preserve exact complete commitish identity",
            )
        entries = _sequence(tree.get("tree"), "provider_evidence_invalid", "merge tree entries")
        if len(entries) > _MAX_SCOPE_TREE_ENTRIES:
            raise MergeEvidenceError(
                "provider_evidence_invalid", "merge tree entry count exceeds local bound"
            )
        matches = []
        for value in entries:
            entry = _mapping(value, "provider_evidence_invalid", "merge tree entry")
            if entry.get("path") == scope_path:
                matches.append(entry)
        if len(matches) != 1:
            raise MergeEvidenceError(
                "provider_evidence_invalid",
                "merge tree did not expose exactly one scope blob",
            )
        entry = matches[0]
        blob_sha = entry.get("sha")
        if entry.get("type") != "blob" or not isinstance(blob_sha, str) or _SHA.fullmatch(blob_sha) is None:
            raise MergeEvidenceError(
                "provider_evidence_invalid",
                "merge tree scope entry is not a valid blob",
            )
        return blob_sha.casefold()

    async def _validate_work_change_binding(
        self,
        *,
        target: PostMergeTargetSettings,
        source_issue: int,
        change_id: str,
    ) -> None:
        value = await self._invoker.read(
            "project_management_board_data",
            {
                "project_id": target.project_id,
                "include_history": True,
                "query": str(source_issue),
                "group_by": "state",
                "item_limit": 1000,
            },
        )
        root = _mapping(value, "provider_evidence_invalid", "source Work evidence")
        provenance = _mapping(
            root.get("provenance"), "provider_evidence_invalid", "source Work provenance"
        )
        result = _mapping(
            root.get("result"), "provider_evidence_invalid", "source Work result"
        )
        cards = _sequence(
            result.get("cards"), "provider_evidence_invalid", "source Work cards"
        )
        if (
            provenance.get("complete") is not True
            or result.get("complete") is not True
            or result.get("truncated") is not False
        ):
            raise MergeEvidenceError(
                "provider_evidence_invalid", "source Work evidence is incomplete"
            )
        matches = [
            value
            for value in cards
            if isinstance(value, Mapping)
            and value.get("number") == source_issue
            and str(value.get("repository", "")).casefold()
            == target.repository.casefold()
        ]
        if len(matches) != 1:
            raise MergeEvidenceError(
                "provider_evidence_invalid",
                "source Work card is not uniquely observable",
            )
        if matches[0].get("change_id") != change_id:
            raise MergeEvidenceError(
                "provider_evidence_invalid",
                "source Work Change ID does not match landed scope change_id",
            )

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
        changed_file_count = pr.get("changed_files")
        if type(changed_file_count) is not int or changed_file_count <= 0:
            raise MergeEvidenceError(
                "provider_evidence_invalid",
                "pull request changed_files must be a positive integer",
            )
        if changed_file_count > _MAX_CHANGED_FILES:
            raise MergeEvidenceError(
                "provider_evidence_invalid",
                "pull request changed_files exceeds provider maximum",
            )
        pr_change_id, head_owner, head_ref = _pr_change_binding(
            pr, target.repository
        )
        merged_at = _parse_time(pr.get("merged_at"), "merged_at")
        source_commit_shas = await self._source_commit_shas(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
        )
        merge_sha = await self._merge_sha(
            owner=owner,
            repo=repo,
            branch=target.default_branch,
            merged_at=merged_at,
            pull_number=pull_number,
            head_owner=head_owner,
            head_ref=head_ref,
            source_commit_shas=source_commit_shas,
        )
        changed_paths = await self._changed_paths(
            owner=owner,
            repo=repo,
            merge_sha=merge_sha,
            expected_count=changed_file_count,
        )
        scope_path, change_id = _scope_candidate(changed_paths)
        expected_scope_blob_sha = await self._scope_blob_sha(
            owner=owner,
            repo=repo,
            merge_sha=merge_sha,
            scope_path=scope_path,
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
        scope_text, scope_bytes = _scope_content(scope_value)
        if _git_blob_sha(scope_bytes) != expected_scope_blob_sha:
            raise MergeEvidenceError(
                "provider_evidence_invalid",
                "scope provider content does not match exact merge-tree blob",
            )
        scope = _scope_document(scope_text)
        source_issue, risks = _validate_scope_identity(
            scope,
            change_id=change_id,
            repository=target.repository,
        )
        if change_id != pr_change_id:
            raise MergeEvidenceError(
                "scope_identity_mismatch",
                "pull request head change ID does not match proven landed scope",
            )
        await self._validate_work_change_binding(
            target=target,
            source_issue=source_issue,
            change_id=change_id,
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
