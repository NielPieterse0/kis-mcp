from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CHANGE_ID_PATTERN = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
ACTIVE_STATUSES = frozenset({"active", "ready"})
ALL_STATUSES = ACTIVE_STATUSES | {"closed"}
REQUIRED_CHANGE_FILES = ("scope.json", "spec.md", "plan.md", "tasks.md", "closeout.md")
REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "change_id",
        "status",
        "branch",
        "worktree",
        "base",
        "outcome",
        "owned_paths",
        "shared_paths",
        "excluded_paths",
        "dependencies",
        "integration_owner",
    }
)


class ClaimError(ValueError):
    """Raised when change governance cannot safely proceed."""


@dataclass(frozen=True, slots=True)
class PathClaim:
    raw: str
    prefix: str
    recursive: bool

    def matches(self, path: str) -> bool:
        normalized = _normalize_repository_path(path)
        if self.recursive:
            return normalized == self.prefix or normalized.startswith(f"{self.prefix}/")
        return normalized == self.prefix

    def overlaps(self, other: "PathClaim") -> bool:
        if not self.recursive and not other.recursive:
            return self.prefix == other.prefix
        if self.recursive and other.recursive:
            return _is_same_or_descendant(self.prefix, other.prefix) or _is_same_or_descendant(
                other.prefix, self.prefix
            )
        recursive = self if self.recursive else other
        exact = other if self.recursive else self
        return _is_same_or_descendant(exact.prefix, recursive.prefix)


@dataclass(frozen=True, slots=True)
class ChangeClaim:
    schema_version: int
    change_id: str
    status: str
    branch: str
    worktree: str
    base: str
    outcome: str
    owned_paths: tuple[PathClaim, ...]
    shared_paths: tuple[PathClaim, ...]
    excluded_paths: tuple[PathClaim, ...]
    dependencies: tuple[str, ...]
    integration_owner: str | None
    source: Path

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], *, source: Path) -> "ChangeClaim":
        missing = sorted(REQUIRED_FIELDS.difference(data))
        unknown = sorted(set(data).difference(REQUIRED_FIELDS))
        if missing:
            raise ClaimError(f"CHANGE_FIELDS_MISSING: {', '.join(missing)}")
        if unknown:
            raise ClaimError(f"CHANGE_FIELDS_UNKNOWN: {', '.join(unknown)}")
        if data["schema_version"] != 1:
            raise ClaimError("CHANGE_SCHEMA_VERSION_INVALID: expected 1")

        change_id = _require_change_id(data["change_id"], "change_id")
        status = _require_string(data["status"], "status")
        if status not in ALL_STATUSES:
            raise ClaimError(f"CHANGE_STATUS_INVALID: {status}")

        branch = _require_string(data["branch"], "branch")
        expected_branch = f"change/{change_id}"
        if branch != expected_branch:
            raise ClaimError(
                f"CHANGE_BRANCH_NONSTANDARD: expected {expected_branch}, received {branch}"
            )

        worktree = _require_string(data["worktree"], "worktree")
        expected_worktree = f".work/worktrees/{change_id}"
        if worktree != expected_worktree:
            raise ClaimError(
                "CHANGE_WORKTREE_NONSTANDARD: "
                f"expected {expected_worktree}, received {worktree}"
            )

        base = _require_string(data["base"], "base")
        if base.startswith("-") or ".." in base or any(character.isspace() for character in base):
            raise ClaimError(f"CHANGE_BASE_INVALID: {base}")

        outcome = _require_string(data["outcome"], "outcome")
        owned_paths = _require_path_claims(data["owned_paths"], "owned_paths")
        shared_paths = _require_path_claims(data["shared_paths"], "shared_paths")
        excluded_paths = _require_path_claims(data["excluded_paths"], "excluded_paths")
        if not owned_paths:
            raise ClaimError("CHANGE_OWNED_PATHS_EMPTY: at least one path is required")

        dependencies = _require_change_ids(data["dependencies"], "dependencies")
        if change_id in dependencies:
            raise ClaimError("CHANGE_DEPENDENCY_SELF: a change cannot depend on itself")

        owner_value = data["integration_owner"]
        integration_owner = (
            None
            if owner_value is None
            else _require_change_id(owner_value, "integration_owner")
        )

        for owned in owned_paths:
            if any(owned.overlaps(shared) for shared in shared_paths):
                raise ClaimError(
                    f"CHANGE_PATH_CLAIM_CONTRADICTION: {owned.raw} is both owned and shared"
                )
            if any(owned.overlaps(excluded) for excluded in excluded_paths):
                raise ClaimError(
                    f"CHANGE_PATH_CLAIM_CONTRADICTION: {owned.raw} is owned and excluded"
                )
        for shared in shared_paths:
            if any(shared.overlaps(excluded) for excluded in excluded_paths):
                raise ClaimError(
                    f"CHANGE_PATH_CLAIM_CONTRADICTION: {shared.raw} is shared and excluded"
                )

        return cls(
            schema_version=1,
            change_id=change_id,
            status=status,
            branch=branch,
            worktree=worktree,
            base=base,
            outcome=outcome,
            owned_paths=owned_paths,
            shared_paths=shared_paths,
            excluded_paths=excluded_paths,
            dependencies=dependencies,
            integration_owner=integration_owner,
            source=source,
        )

    @property
    def normalized_outcome(self) -> str:
        return " ".join(self.outcome.casefold().split())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "change_id": self.change_id,
            "status": self.status,
            "branch": self.branch,
            "worktree": self.worktree,
            "base": self.base,
            "outcome": self.outcome,
            "owned_paths": [claim.raw for claim in self.owned_paths],
            "shared_paths": [claim.raw for claim in self.shared_paths],
            "excluded_paths": [claim.raw for claim in self.excluded_paths],
            "dependencies": list(self.dependencies),
            "integration_owner": self.integration_owner,
        }


@dataclass(frozen=True, slots=True)
class WorktreeEntry:
    path: Path
    branch: str | None
    head: str


@dataclass(frozen=True, slots=True)
class CleanupResult:
    change_id: str
    branch: str
    recovered: bool
    backup_path: Path | None

    def to_mapping(self) -> dict[str, Any]:
        return {
            "cleaned": self.change_id,
            "branch": self.branch,
            "recovered": self.recovered,
            "backup_path": str(self.backup_path) if self.backup_path is not None else None,
        }


def find_claim_conflicts(claims: Sequence[ChangeClaim]) -> list[str]:
    active = [claim for claim in claims if claim.status in ACTIVE_STATUSES]
    conflicts: list[str] = []

    for index, left in enumerate(active):
        for right in active[index + 1 :]:
            if left.change_id == right.change_id:
                conflicts.append(
                    f"DUPLICATE_CHANGE_ID: {left.change_id} in {left.source} and {right.source}"
                )
            if left.branch == right.branch:
                conflicts.append(
                    f"DUPLICATE_ACTIVE_BRANCH: {left.branch} in {left.source} and {right.source}"
                )
            if left.worktree == right.worktree:
                conflicts.append(
                    "DUPLICATE_ACTIVE_WORKTREE: "
                    f"{left.worktree} in {left.source} and {right.source}"
                )
            if left.normalized_outcome == right.normalized_outcome:
                conflicts.append(
                    "DUPLICATE_ACTIVE_OUTCOME: "
                    f"{left.outcome!r} in {left.source} and {right.source}"
                )
            conflicts.extend(_path_conflicts(left, right))

    return conflicts


def paths_outside_claim(claim: ChangeClaim, paths: Iterable[str]) -> list[str]:
    violations: list[str] = []
    seen: set[str] = set()
    declared = (*claim.owned_paths, *claim.shared_paths)
    for raw_path in paths:
        normalized = _normalize_repository_path(raw_path)
        if normalized in seen:
            continue
        seen.add(normalized)
        if any(path_claim.matches(normalized) for path_claim in claim.excluded_paths):
            violations.append(f"PATH_EXCLUDED_BY_CLAIM: {normalized}")
        elif not any(path_claim.matches(normalized) for path_claim in declared):
            violations.append(f"PATH_OUTSIDE_CLAIM: {normalized}")
    return violations


def load_claim(path: Path) -> ChangeClaim:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClaimError(f"CHANGE_SCOPE_UNREADABLE: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ClaimError(f"CHANGE_SCOPE_INVALID: {path} must contain a JSON object")
    return ChangeClaim.from_mapping(data, source=path)


def discover_worktrees(repository: Path) -> list[WorktreeEntry]:
    root = repository_root(repository)
    output = _run_git(root, "worktree", "list", "--porcelain").stdout
    entries: list[WorktreeEntry] = []
    current: dict[str, str] = {}
    for line in [*output.splitlines(), ""]:
        if not line:
            if current:
                entries.append(
                    WorktreeEntry(
                        path=Path(current["worktree"]).resolve(),
                        branch=_normalize_branch_ref(current.get("branch")),
                        head=current.get("HEAD", ""),
                    )
                )
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return entries


def load_worktree_claims(repository: Path) -> list[ChangeClaim]:
    worktrees = discover_worktrees(repository)
    if not worktrees:
        return []

    current_root = repository_root(repository)
    claims = _claims_in_checkout(current_root)
    known_change_ids = {claim.change_id for claim in claims}

    for entry in worktrees:
        if not entry.branch or not entry.branch.startswith("change/"):
            continue
        change_id = entry.branch.removeprefix("change/")
        if change_id in known_change_ids:
            continue
        scope_path = entry.path / ".work" / "changes" / change_id / "scope.json"
        if not scope_path.is_file():
            continue
        claims.append(load_claim(scope_path))
        known_change_ids.add(change_id)
    return claims


def create_change_worktree(
    repository: Path,
    *,
    change_id: str,
    outcome: str,
    owned_paths: Sequence[str],
    shared_paths: Sequence[str] = (),
    excluded_paths: Sequence[str] = (),
    dependencies: Sequence[str] = (),
    integration_owner: str | None = None,
    base: str = "main",
) -> Path:
    root = repository_root(repository)
    _require_primary_clean_worktree(root, base)
    _require_worktree_directory_ignored(root)
    _require_template(root)
    existing_claims = validate_repository(root)

    workspace_claim = f".work/changes/{change_id}/**"
    normalized_owned = list(owned_paths)
    if workspace_claim not in normalized_owned:
        normalized_owned.append(workspace_claim)
    claim_data = {
        "schema_version": 1,
        "change_id": change_id,
        "status": "active",
        "branch": f"change/{change_id}",
        "worktree": f".work/worktrees/{change_id}",
        "base": base,
        "outcome": outcome,
        "owned_paths": normalized_owned,
        "shared_paths": list(shared_paths),
        "excluded_paths": list(excluded_paths),
        "dependencies": list(dependencies),
        "integration_owner": integration_owner,
    }
    claim = ChangeClaim.from_mapping(claim_data, source=Path("<new-change>"))
    conflicts = find_claim_conflicts([*existing_claims, claim])
    if conflicts:
        raise ClaimError("\n".join(conflicts))

    branch = claim.branch
    target = root / claim.worktree
    if target.exists():
        raise ClaimError(f"CHANGE_WORKTREE_EXISTS: {target}")
    if _git_ref_exists(root, f"refs/heads/{branch}"):
        raise ClaimError(f"CHANGE_BRANCH_EXISTS: {branch}")
    if not _git_ref_exists(root, f"refs/heads/{base}"):
        raise ClaimError(f"CHANGE_BASE_MISSING: {base}")

    target.parent.mkdir(parents=True, exist_ok=True)
    _run_git(root, "worktree", "add", str(target), "-b", branch, base)
    try:
        change_root = target / ".work" / "changes" / change_id
        change_root.mkdir(parents=True, exist_ok=False)
        (change_root / "scope.json").write_text(
            json.dumps(claim.to_mapping(), indent=2) + "\n", encoding="utf-8"
        )
        template_root = root / ".work" / "changes" / "_template"
        replacements = {
            "{{CHANGE_ID}}": change_id,
            "{{CHANGE_NAME}}": change_id.split("-", 1)[1].replace("-", " ").title(),
            "{{OUTCOME}}": outcome,
        }
        for name in REQUIRED_CHANGE_FILES[1:]:
            content = (template_root / name).read_text(encoding="utf-8")
            for marker, replacement in replacements.items():
                content = content.replace(marker, replacement)
            (change_root / name).write_text(content, encoding="utf-8")
    except Exception:
        _run_git(root, "worktree", "remove", str(target), check=False)
        _run_git(root, "branch", "-d", branch, check=False)
        raise
    return target


def validate_repository(
    repository: Path,
    *,
    require_active_worktrees: bool = True,
) -> list[ChangeClaim]:
    current_root = repository_root(repository)
    worktrees = discover_worktrees(current_root)
    if not worktrees:
        raise ClaimError("PRIMARY_WORKTREE_UNRESOLVED: no Git worktrees were found")
    primary_root = worktrees[0].path
    _require_worktree_directory_ignored(primary_root)
    template_root = (
        current_root
        if (current_root / ".work" / "changes" / "_template").is_dir()
        else primary_root
    )
    _require_template(template_root)
    claims = load_worktree_claims(current_root)
    conflicts = find_claim_conflicts(claims)
    if conflicts:
        raise ClaimError("\n".join(conflicts))
    entries = {entry.branch: entry for entry in worktrees if entry.branch}
    claims_by_branch: dict[str, list[ChangeClaim]] = {}
    for claim in claims:
        claims_by_branch.setdefault(claim.branch, []).append(claim)

    for entry in worktrees[1:]:
        if not entry.branch or not entry.branch.startswith("change/"):
            continue
        registered = claims_by_branch.get(entry.branch, [])
        if not registered:
            raise ClaimError(f"ACTIVE_CHANGE_CLAIM_MISSING: {entry.branch}")
        expected = (primary_root / registered[0].worktree).resolve()
        if entry.path != expected:
            raise ClaimError(
                f"ACTIVE_CHANGE_WORKTREE_MISMATCH: {registered[0].change_id}: "
                f"{entry.path} != {expected}"
            )

    if require_active_worktrees:
        for claim in claims:
            if claim.status not in ACTIVE_STATUSES:
                continue
            entry = entries.get(claim.branch)
            if entry is None:
                raise ClaimError(f"ACTIVE_CHANGE_WORKTREE_MISSING: {claim.change_id}")
    return claims


def check_current_change(repository: Path) -> list[str]:
    root = repository_root(repository)
    branch = _run_git(root, "branch", "--show-current").stdout.strip()
    if not branch:
        raise ClaimError("CHANGE_BRANCH_DETACHED: current worktree has no branch")
    matches = [claim for claim in _claims_in_checkout(root) if claim.branch == branch]
    if len(matches) != 1:
        raise ClaimError(
            f"CURRENT_CHANGE_CLAIM_MISSING: expected one claim for {branch}, found {len(matches)}"
        )
    claim = matches[0]
    _require_change_artifacts(root, claim.change_id)
    merge_base = _run_git(root, "merge-base", claim.base, "HEAD").stdout.strip()
    committed = _run_git(root, "diff", "--name-only", f"{merge_base}...HEAD").stdout.splitlines()
    working = _working_tree_paths(root)
    changed = [*committed, *working]
    violations = paths_outside_claim(claim, changed)
    if violations:
        raise ClaimError("\n".join(violations))
    return sorted(set(changed))


def cleanup_change_worktree(repository: Path, change_id: str) -> CleanupResult:
    root = repository_root(repository)
    normalized_id = _require_change_id(change_id, "change_id")
    target = (root / ".work" / "worktrees" / normalized_id).resolve()
    branch = f"change/{normalized_id}"
    entries = {entry.branch: entry for entry in discover_worktrees(root) if entry.branch}
    entry = entries.get(branch)
    if entry is None or entry.path != target:
        raise ClaimError(f"CHANGE_WORKTREE_MISSING: {normalized_id}")

    status = _run_git(target, "status", "--porcelain", "--untracked-files=all").stdout
    if status.strip():
        raise ClaimError(f"CHANGE_WORKTREE_DIRTY: {target}")

    claims = [claim for claim in _claims_in_checkout(target) if claim.change_id == normalized_id]
    if len(claims) != 1:
        raise ClaimError(f"CHANGE_SCOPE_MISSING: {normalized_id}")
    claim = claims[0]
    if claim.status != "closed":
        raise ClaimError(
            f"CHANGE_STATUS_NOT_CLOSED: {normalized_id}: status is {claim.status}"
        )
    base = claim.base
    ancestor = _run_git(root, "merge-base", "--is-ancestor", branch, base, check=False)
    if ancestor.returncode != 0:
        raise ClaimError(f"CHANGE_BRANCH_UNMERGED: {branch} is not merged into {base}")

    removal = _run_git(
        root,
        "-c",
        "core.longpaths=true",
        "worktree",
        "remove",
        str(target),
        check=False,
    )
    recovered = False
    backup_path: Path | None = None
    if removal.returncode != 0:
        remaining = {
            worktree.branch: worktree
            for worktree in discover_worktrees(root)
            if worktree.branch
        }
        if branch in remaining:
            detail = removal.stderr.strip() or removal.stdout.strip() or "unknown removal failure"
            raise ClaimError(
                f"CHANGE_WORKTREE_REMOVE_FAILED: {branch} remains registered: {detail}"
            )
        if target.exists():
            backup_root = root.parent / ".backup"
            backup_root.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            backup_path = backup_root / f"{normalized_id}-worktree-remnant-{timestamp}"
            if backup_path.exists():
                raise ClaimError(f"CHANGE_BACKUP_EXISTS: {backup_path}")
            try:
                target.replace(backup_path)
            except OSError as exc:
                raise ClaimError(
                    f"CHANGE_WORKTREE_RECOVERY_FAILED: {target} -> {backup_path}: {exc}"
                ) from exc
            recovered = True

    _run_git(root, "branch", "-d", branch)
    _run_git(root, "worktree", "prune")
    return CleanupResult(
        change_id=normalized_id,
        branch=branch,
        recovered=recovered,
        backup_path=backup_path,
    )


def repository_root(path: Path) -> Path:
    candidate = Path(path).resolve()
    result = _run_git(candidate, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve()


def _path_conflicts(left: ChangeClaim, right: ChangeClaim) -> list[str]:
    conflicts: list[str] = []
    for left_owned in left.owned_paths:
        for right_claim in (*right.owned_paths, *right.shared_paths):
            if left_owned.overlaps(right_claim):
                conflicts.append(
                    "EXCLUSIVE_PATH_OVERLAP: "
                    f"{left.change_id}:{left_owned.raw} overlaps "
                    f"{right.change_id}:{right_claim.raw}"
                )
    for right_owned in right.owned_paths:
        for left_shared in left.shared_paths:
            if right_owned.overlaps(left_shared):
                conflicts.append(
                    "EXCLUSIVE_PATH_OVERLAP: "
                    f"{right.change_id}:{right_owned.raw} overlaps "
                    f"{left.change_id}:{left_shared.raw}"
                )
    for left_shared in left.shared_paths:
        for right_shared in right.shared_paths:
            if left_shared.overlaps(right_shared) and not _claims_are_coordinated(left, right):
                conflicts.append(
                    "UNCOORDINATED_SHARED_PATH: "
                    f"{left.change_id}:{left_shared.raw} overlaps "
                    f"{right.change_id}:{right_shared.raw}"
                )
    return conflicts


def _claims_are_coordinated(left: ChangeClaim, right: ChangeClaim) -> bool:
    if left.change_id in right.dependencies or right.change_id in left.dependencies:
        return True
    if left.integration_owner and left.integration_owner == right.integration_owner:
        return True
    if left.integration_owner == right.change_id or right.integration_owner == left.change_id:
        return True
    return False


def _claims_in_checkout(root: Path) -> list[ChangeClaim]:
    changes_root = root / ".work" / "changes"
    if not changes_root.is_dir():
        return []
    claims: list[ChangeClaim] = []
    for scope_path in sorted(changes_root.glob("*/scope.json")):
        if scope_path.parent.name.startswith("_"):
            continue
        claims.append(load_claim(scope_path))
    return claims


def _require_primary_clean_worktree(root: Path, base: str) -> None:
    entries = discover_worktrees(root)
    if not entries or entries[0].path != root:
        raise ClaimError("PRIMARY_WORKTREE_UNRESOLVED: cannot determine the primary checkout")
    current = _run_git(root, "branch", "--show-current").stdout.strip()
    if current != base:
        raise ClaimError(f"PRIMARY_BRANCH_REQUIRED: expected {base}, received {current or '<detached>'}")
    status = _run_git(root, "status", "--porcelain", "--untracked-files=all").stdout
    if status.strip():
        raise ClaimError("PRIMARY_WORKTREE_DIRTY: commit or quarantine current changes first")


def _require_worktree_directory_ignored(root: Path) -> None:
    probe = ".work/worktrees/.governance-probe"
    result = _run_git(root, "check-ignore", "-q", probe, check=False)
    if result.returncode != 0:
        raise ClaimError("WORKTREE_DIRECTORY_NOT_IGNORED: add .work/worktrees/ to .gitignore")


def _require_template(root: Path) -> None:
    template = root / ".work" / "changes" / "_template"
    missing = [name for name in REQUIRED_CHANGE_FILES if not (template / name).is_file()]
    if missing:
        raise ClaimError(f"CHANGE_TEMPLATE_MISSING: {', '.join(missing)}")


def _require_change_artifacts(root: Path, change_id: str) -> None:
    change_root = root / ".work" / "changes" / change_id
    missing = [name for name in REQUIRED_CHANGE_FILES if not (change_root / name).is_file()]
    if missing:
        raise ClaimError(f"CHANGE_ARTIFACTS_MISSING: {change_id}: {', '.join(missing)}")


def _working_tree_paths(root: Path) -> list[str]:
    output = _run_git(root, "status", "--porcelain", "--untracked-files=all").stdout
    paths: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.append(value.strip('"'))
    return paths


def _git_ref_exists(root: Path, ref: str) -> bool:
    return _run_git(root, "show-ref", "--verify", "--quiet", ref, check=False).returncode == 0


def _run_git(
    repository: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown git failure"
        raise ClaimError(f"GIT_COMMAND_FAILED: git {' '.join(args)}: {detail}")
    return completed


def _normalize_branch_ref(value: str | None) -> str | None:
    prefix = "refs/heads/"
    if value and value.startswith(prefix):
        return value[len(prefix) :]
    return value


def _require_path_claims(value: Any, field: str) -> tuple[PathClaim, ...]:
    raw_values = _require_string_list(value, field)
    claims = tuple(_parse_path_claim(raw) for raw in raw_values)
    if len({claim.raw for claim in claims}) != len(claims):
        raise ClaimError(f"CHANGE_PATH_DUPLICATE: {field}")
    return claims


def _require_change_ids(value: Any, field: str) -> tuple[str, ...]:
    values = _require_string_list(value, field)
    normalized = tuple(_require_change_id(item, field) for item in values)
    if len(set(normalized)) != len(normalized):
        raise ClaimError(f"CHANGE_ID_DUPLICATE: {field}")
    return normalized


def _require_string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ClaimError(f"CHANGE_FIELD_TYPE_INVALID: {field} must be a string array")
    return tuple(value)


def _require_change_id(value: Any, field: str) -> str:
    text = _require_string(value, field)
    if not CHANGE_ID_PATTERN.fullmatch(text):
        raise ClaimError(f"CHANGE_ID_INVALID: {field}={text}")
    return text


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClaimError(f"CHANGE_FIELD_TYPE_INVALID: {field} must be a non-empty string")
    return value.strip()


def _parse_path_claim(value: str) -> PathClaim:
    normalized = _normalize_repository_path(value)
    recursive = normalized.endswith("/**")
    if "*" in normalized and not recursive:
        raise ClaimError(f"CHANGE_PATH_PATTERN_INVALID: {value}")
    prefix = normalized[:-3] if recursive else normalized
    if not prefix or "*" in prefix:
        raise ClaimError(f"CHANGE_PATH_PATTERN_INVALID: {value}")
    return PathClaim(raw=normalized, prefix=prefix, recursive=recursive)


def _normalize_repository_path(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClaimError("CHANGE_PATH_PATTERN_INVALID: path must be non-empty")
    normalized = value.strip().replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        raise ClaimError(f"CHANGE_PATH_PATTERN_INVALID: {value}")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ClaimError(f"CHANGE_PATH_PATTERN_INVALID: {value}")
    return normalized


def _is_same_or_descendant(path: str, parent: str) -> bool:
    return path == parent or path.startswith(f"{parent}/")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage bounded parallel change worktrees.")
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)

    new = subparsers.add_parser("new", help="Create one validated change worktree.")
    new.add_argument("change_id")
    new.add_argument("--outcome", required=True)
    new.add_argument("--owned", action="append", required=True)
    new.add_argument("--shared", action="append", default=[])
    new.add_argument("--exclude", action="append", default=[])
    new.add_argument("--depends-on", action="append", default=[])
    new.add_argument("--integration-owner")
    new.add_argument("--base", default="main")

    validate = subparsers.add_parser("validate", help="Validate active change claims and worktrees.")
    validate.add_argument(
        "--claims-only",
        action="store_true",
        help="Validate claim semantics without requiring unrelated active worktrees to exist locally.",
    )
    subparsers.add_parser("check", help="Check the current diff against its declared scope.")
    subparsers.add_parser("list", help="List active and ready change claims.")
    cleanup = subparsers.add_parser("cleanup", help="Remove one clean merged worktree.")
    cleanup.add_argument("change_id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "new":
            target = create_change_worktree(
                args.repository,
                change_id=args.change_id,
                outcome=args.outcome,
                owned_paths=args.owned,
                shared_paths=args.shared,
                excluded_paths=args.exclude,
                dependencies=args.depends_on,
                integration_owner=args.integration_owner,
                base=args.base,
            )
            print(json.dumps({"change_id": args.change_id, "worktree": str(target)}))
        elif args.command == "validate":
            claims = validate_repository(
                args.repository,
                require_active_worktrees=not args.claims_only,
            )
            print(json.dumps({"active_changes": sum(c.status in ACTIVE_STATUSES for c in claims)}))
        elif args.command == "check":
            changed = check_current_change(args.repository)
            print(json.dumps({"changed_paths": changed}))
        elif args.command == "list":
            claims = [
                claim.to_mapping()
                for claim in load_worktree_claims(repository_root(args.repository))
                if claim.status in ACTIVE_STATUSES
            ]
            print(json.dumps(claims, indent=2))
        elif args.command == "cleanup":
            result = cleanup_change_worktree(args.repository, args.change_id)
            print(json.dumps(result.to_mapping()))
        else:
            parser.error(f"unsupported command: {args.command}")
    except ClaimError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
