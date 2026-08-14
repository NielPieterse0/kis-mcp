from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, BinaryIO, Sequence


SCHEMA_VERSION = 1
DEFAULT_MAX_FILES = 1_000
DEFAULT_MAX_OUTPUT_BYTES = 1_000_000
_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@{}+:-]*$")
_CHANGE_ID_PATTERN = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")


class GitWorkflowError(ValueError):
    def __init__(self, code: str, message: str, *, field: str | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.field = field

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "error": {
                "code": self.code,
                "message": self.message,
                "field": self.field,
                "retryable": False,
            },
        }


def _load_change_governance():
    path = Path(__file__).with_name("change-governance.py")
    spec = importlib.util.spec_from_file_location("kis_change_governance", path)
    if spec is None or spec.loader is None:
        raise GitWorkflowError("GOVERNANCE_MODULE_UNAVAILABLE", "Change governance could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _repository_root(value: Path | str) -> Path:
    candidate = Path(value).resolve()
    if not candidate.is_dir():
        raise GitWorkflowError(
            "GIT_REPOSITORY_INVALID",
            "The repository path does not identify an existing directory.",
            field="repository",
        )
    result = _run_git(candidate, "rev-parse", "--show-toplevel", check=False)
    if result.returncode != 0:
        raise GitWorkflowError(
            "GIT_REPOSITORY_INVALID",
            "The repository path is not a Git worktree.",
            field="repository",
        )
    return Path(_decode(result.stdout).strip()).resolve()


def _validate_ref(repository: Path, value: str, field: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("-"):
        raise GitWorkflowError("GIT_REF_INVALID", f"{field} must be a non-option Git ref.", field=field)
    if any(character.isspace() for character in value) or ".." in value or not _REF_PATTERN.fullmatch(value):
        raise GitWorkflowError("GIT_REF_INVALID", f"{field} contains unsupported characters.", field=field)
    result = _run_git(
        repository,
        "rev-parse",
        "--verify",
        "--quiet",
        "--end-of-options",
        f"{value}^{{commit}}",
        check=False,
    )
    if result.returncode != 0:
        raise GitWorkflowError("GIT_REF_NOT_FOUND", f"{field} does not resolve to a commit.", field=field)
    return value


def _validate_path(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace("\\", "/").strip()
    if (
        not normalized
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:/", normalized)
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
    ):
        raise GitWorkflowError(
            "GIT_PATH_INVALID",
            "Path filters must be unambiguous repository-relative paths.",
            field="path",
        )
    return normalized


def _validate_change_id(value: str | None) -> str | None:
    if value is None:
        return None
    if not _CHANGE_ID_PATTERN.fullmatch(value):
        raise GitWorkflowError(
            "CHANGE_ID_INVALID",
            "change_id must use NNN-kebab-case form.",
            field="change_id",
        )
    return value


def _run_git(
    repository: Path,
    *args: str,
    check: bool = True,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    timeout_seconds: float = 30.0,
) -> subprocess.CompletedProcess[bytes]:
    command = ["git", "--no-pager", *args]
    try:
        process = subprocess.Popen(
            command,
            cwd=repository,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise GitWorkflowError(
            "GIT_EXECUTION_FAILED",
            f"Git could not be started: {exc}",
        ) from exc
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise GitWorkflowError("GIT_EXECUTION_FAILED", "Git output streams were unavailable.")

    stdout = bytearray()
    stderr = bytearray()
    state = {"overflow": False, "captured": 0}
    lock = threading.Lock()

    def drain(stream: BinaryIO, target: bytearray) -> None:
        while True:
            chunk = stream.read(65_536)
            if not chunk:
                break
            with lock:
                remaining = max_output_bytes - int(state["captured"])
                accepted = min(len(chunk), max(0, remaining))
                if accepted:
                    target.extend(chunk[:accepted])
                    state["captured"] = int(state["captured"]) + accepted
                if accepted < len(chunk):
                    state["overflow"] = True

    stdout_thread = threading.Thread(target=drain, args=(process.stdout, stdout), daemon=True)
    stderr_thread = threading.Thread(target=drain, args=(process.stderr, stderr), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    try:
        returncode = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        stdout_thread.join()
        stderr_thread.join()
        raise GitWorkflowError(
            "GIT_TIMEOUT",
            f"Git command exceeded {timeout_seconds:g} seconds.",
        ) from exc
    stdout_thread.join()
    stderr_thread.join()
    if state["overflow"]:
        raise GitWorkflowError(
            "GIT_OUTPUT_LIMIT_EXCEEDED",
            f"Git output exceeded {max_output_bytes} bytes.",
        )
    completed = subprocess.CompletedProcess(
        command,
        returncode,
        bytes(stdout),
        bytes(stderr),
    )
    if check and completed.returncode != 0:
        detail = _decode(completed.stderr).strip()
        raise GitWorkflowError("GIT_COMMAND_FAILED", detail or "Git command failed.")
    return completed


def _decode(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _parse_name_status(output: bytes) -> list[dict[str, Any]]:
    fields = output.split(b"\x00")
    if fields and fields[-1] == b"":
        fields.pop()
    records: list[dict[str, Any]] = []
    index = 0
    statuses = {
        "A": "added",
        "C": "copied",
        "D": "deleted",
        "M": "modified",
        "R": "renamed",
        "T": "type_changed",
        "U": "unmerged",
    }
    while index < len(fields):
        raw_status = _decode(fields[index])
        index += 1
        marker = raw_status[:1].upper()
        if marker in {"R", "C"}:
            if index + 1 >= len(fields):
                break
            previous_path = _decode(fields[index])
            path = _decode(fields[index + 1])
            index += 2
        else:
            if index >= len(fields):
                break
            previous_path = None
            path = _decode(fields[index])
            index += 1
        records.append(
            {
                "path": path,
                "previous_path": previous_path,
                "status": statuses.get(marker, "unknown"),
                "similarity": int(raw_status[1:]) if raw_status[1:].isdigit() else None,
                "added": 0,
                "deleted": 0,
                "binary": False,
            }
        )
    return records


def _parse_numstat(output: bytes) -> dict[str, tuple[int, int, bool]]:
    fields = output.split(b"\x00")
    if fields and fields[-1] == b"":
        fields.pop()
    result: dict[str, tuple[int, int, bool]] = {}
    index = 0
    while index < len(fields):
        first = _decode(fields[index])
        index += 1
        parts = first.split("\t", 2)
        if len(parts) != 3:
            continue
        added_raw, deleted_raw, path = parts
        if path:
            target = path
        else:
            if index + 1 >= len(fields):
                break
            index += 1  # previous path
            target = _decode(fields[index])
            index += 1
        binary = added_raw == "-" or deleted_raw == "-"
        result[target] = (
            0 if binary else int(added_raw),
            0 if binary else int(deleted_raw),
            binary,
        )
    return result


def diff_summary(
    repository: Path | str,
    *,
    base: str,
    head: str,
    path: str | None = None,
    max_files: int = DEFAULT_MAX_FILES,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> dict[str, Any]:
    root = _repository_root(repository)
    base = _validate_ref(root, base, "base")
    head = _validate_ref(root, head, "head")
    path = _validate_path(path)
    if isinstance(max_files, bool) or not isinstance(max_files, int) or max_files < 1:
        raise GitWorkflowError("GIT_LIMIT_INVALID", "max_files must be a positive integer.", field="max_files")
    if (
        isinstance(max_output_bytes, bool)
        or not isinstance(max_output_bytes, int)
        or max_output_bytes < 1
    ):
        raise GitWorkflowError(
            "GIT_LIMIT_INVALID",
            "max_output_bytes must be a positive integer.",
            field="max_output_bytes",
        )
    merge_base = _decode(_run_git(root, "merge-base", base, head).stdout).strip()
    range_value = f"{merge_base}..{head}"
    diff_args = ["diff", "--name-status", "-z", "--find-renames", "--find-copies", merge_base, head]
    numstat_args = ["diff", "--numstat", "-z", "--find-renames", "--find-copies", merge_base, head]
    if path is not None:
        diff_args.extend(("--", path))
        numstat_args.extend(("--", path))
    all_records = _parse_name_status(
        _run_git(root, *diff_args, max_output_bytes=max_output_bytes).stdout
    )
    stats = _parse_numstat(
        _run_git(root, *numstat_args, max_output_bytes=max_output_bytes).stdout
    )
    for item in all_records:
        added, deleted, binary = stats.get(item["path"], (0, 0, False))
        item["added"] = added
        item["deleted"] = deleted
        item["binary"] = binary
    all_records.sort(key=lambda item: (item["path"].casefold(), item["path"]))
    total_records = len(all_records)
    records = all_records[:max_files]
    log_output = _decode(
        _run_git(
            root,
            "log",
            "--reverse",
            "--format=%H%x09%s",
            range_value,
            max_output_bytes=max_output_bytes,
        ).stdout
    )
    commits = []
    for line in log_output.splitlines():
        sha, separator, subject = line.partition("\t")
        if separator:
            commits.append({"sha": sha, "subject": subject})
    status_counts: dict[str, int] = {}
    for item in all_records:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "diff-summary",
        "repository": str(root),
        "base": base,
        "head": head,
        "merge_base": merge_base,
        "path": path,
        "files": records,
        "commits": commits,
        "summary": {
            "files": total_records,
            "returned_files": len(records),
            "omitted_files": max(0, total_records - len(records)),
            "added_lines": sum(item["added"] for item in all_records),
            "deleted_lines": sum(item["deleted"] for item in all_records),
            "binary_files": sum(item["binary"] for item in all_records),
            "statuses": dict(sorted(status_counts.items())),
        },
        "truncated": total_records > len(records),
    }


def pr_readiness(repository: Path | str, *, base: str = "main") -> dict[str, Any]:
    root = _repository_root(repository)
    base = _validate_ref(root, base, "base")
    branch = _decode(_run_git(root, "branch", "--show-current").stdout).strip()
    detached = not branch
    status = _decode(_run_git(root, "status", "--porcelain", "--untracked-files=all").stdout)
    clean = not status.strip()
    counts = _decode(_run_git(root, "rev-list", "--left-right", "--count", f"{base}...HEAD").stdout).split()
    behind, ahead = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (0, 0)
    blockers: list[str] = []
    if detached:
        blockers.append("DETACHED_HEAD")
    if not clean:
        blockers.append("WORKTREE_DIRTY")
    if ahead < 1:
        blockers.append("BRANCH_NOT_AHEAD")
    if behind:
        blockers.append("BASE_BEHIND")
    change_id = branch.removeprefix("change/") if branch.startswith("change/") else None
    scope_check: dict[str, Any] = {"passed": False, "changed_paths": [], "error": None}
    if change_id is None:
        blockers.append("CHANGE_CLAIM_MISSING")
        scope_check["error"] = "Current branch is not a governed change branch."
    else:
        governance = _load_change_governance()
        try:
            changed_paths = governance.check_current_change(root)
            scope_check = {"passed": True, "changed_paths": changed_paths, "error": None}
        except governance.ClaimError as exc:
            blockers.append("SCOPE_CHECK_FAILED")
            scope_check["error"] = str(exc)
    blockers = list(dict.fromkeys(blockers))
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "pr-readiness",
        "repository": str(root),
        "branch": branch or None,
        "change_id": change_id,
        "base": base,
        "head": _decode(_run_git(root, "rev-parse", "HEAD").stdout).strip(),
        "clean": clean,
        "detached": detached,
        "ahead": ahead,
        "behind": behind,
        "scope_check": scope_check,
        "ready": not blockers,
        "blockers": blockers,
        "recommended_actions": _readiness_actions(blockers, change_id),
    }


def _readiness_actions(blockers: list[str], change_id: str | None) -> list[str]:
    actions: list[str] = []
    if "WORKTREE_DIRTY" in blockers:
        actions.append("Commit or recover current changes before publishing.")
    if "BASE_BEHIND" in blockers:
        actions.append("Integrate the latest base branch and rerun verification.")
    if "BRANCH_NOT_AHEAD" in blockers:
        actions.append("Confirm the branch contains a reviewable commit beyond the base.")
    if "CHANGE_CLAIM_MISSING" in blockers:
        actions.append("Use a registered change/<id> branch with complete governance artifacts.")
    if "SCOPE_CHECK_FAILED" in blockers:
        actions.append("Reconcile changed paths with the registered change scope.")
    if not blockers and change_id:
        actions.extend(
            (
                "Run scripts/verify.ps1 on the exact head.",
                "Push the named branch and create the PR through the GitHub connector.",
            )
        )
    return actions


def _long_path_risk(path: Path, *, limit: int = 240, max_entries: int = 2_000) -> bool:
    if len(str(path)) >= limit:
        return True
    checked = 0
    try:
        for item in path.rglob("*"):
            if len(str(item)) >= limit:
                return True
            checked += 1
            if checked >= max_entries:
                break
    except OSError:
        return True
    return False


def _primary_worktree(repository: Path) -> Path:
    common_dir = _decode(
        _run_git(
            repository,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ).stdout
    ).strip()
    path = Path(common_dir).resolve()
    if path.name.casefold() != ".git" or not path.is_dir():
        raise GitWorkflowError(
            "GIT_COMMON_DIR_INVALID",
            "Git did not resolve a normal primary worktree common directory.",
        )
    return path.parent


def _branch_landing_evidence(repository: Path, branch: str, base: str) -> dict[str, Any]:
    branch_sha = _decode(_run_git(repository, "rev-parse", branch).stdout).strip()
    base_sha = _decode(_run_git(repository, "rev-parse", base).stdout).strip()
    ancestor = _run_git(
        repository,
        "merge-base",
        "--is-ancestor",
        branch_sha,
        base_sha,
        check=False,
    )
    if ancestor.returncode == 0:
        return {
            "landed": True,
            "mode": "ancestor",
            "branch_sha": branch_sha,
            "base_sha": base_sha,
            "landing_commit": branch_sha,
        }

    branch_tree = _decode(
        _run_git(repository, "show", "-s", "--format=%T", branch_sha).stdout
    ).strip()
    history = _decode(
        _run_git(
            repository,
            "log",
            "--format=%H%x09%T",
            base_sha,
            max_output_bytes=5_000_000,
        ).stdout
    )
    for line in history.splitlines():
        commit_sha, separator, tree_sha = line.partition("\t")
        if separator and tree_sha == branch_tree:
            return {
                "landed": True,
                "mode": "tree_equivalent_reachable",
                "branch_sha": branch_sha,
                "base_sha": base_sha,
                "landing_commit": commit_sha,
            }

    cherry = _run_git(repository, "cherry", base_sha, branch_sha, check=False)
    if cherry.returncode == 0:
        entries = [line.strip() for line in _decode(cherry.stdout).splitlines() if line.strip()]
        if entries and all(line.startswith("-") for line in entries):
            return {
                "landed": True,
                "mode": "patch_equivalent",
                "branch_sha": branch_sha,
                "base_sha": base_sha,
                "landing_commit": None,
            }

    return {
        "landed": False,
        "mode": "unlanded",
        "branch_sha": branch_sha,
        "base_sha": base_sha,
        "landing_commit": None,
    }


def prepare_cleanup(repository: Path | str, *, change_id: str) -> dict[str, Any]:
    root = _repository_root(repository)
    normalized_id = _validate_change_id(change_id)
    if normalized_id is None:
        raise GitWorkflowError("CHANGE_ID_INVALID", "change_id is required.", field="change_id")

    preview = cleanup_preview(root, change_id=normalized_id)
    records = preview["worktrees"]
    if len(records) != 1:
        raise GitWorkflowError(
            "CHANGE_WORKTREE_MISSING",
            f"Expected one registered worktree for {normalized_id}, found {len(records)}.",
        )
    record = records[0]
    if not record["eligible"]:
        blocker = record["blockers"][0] if record["blockers"] else "CLEANUP_NOT_ELIGIBLE"
        raise GitWorkflowError(
            blocker,
            f"Change {normalized_id} is not eligible for cleanup: {', '.join(record['blockers'])}",
        )

    if record["landing_mode"] == "ancestor":
        return {
            "schema_version": SCHEMA_VERSION,
            "operation": "prepare-cleanup",
            "change_id": normalized_id,
            "normalized": False,
            "landing_mode": record["landing_mode"],
            "original_head": record["head"],
            "normalized_head": record["head"],
            "recovery_ref": None,
        }

    target = Path(record["path"])
    original_head = str(record["head"])
    base_sha = str(record["base_sha"])
    recovery_ref = f"refs/kis-recovery/cleanup/{normalized_id}"
    existing = _run_git(
        root,
        "rev-parse",
        "--verify",
        "--quiet",
        recovery_ref,
        check=False,
    )
    if existing.returncode == 0:
        existing_sha = _decode(existing.stdout).strip()
        if existing_sha != original_head:
            raise GitWorkflowError(
                "CLEANUP_RECOVERY_REF_CONFLICT",
                f"Recovery ref {recovery_ref} points to {existing_sha}, expected {original_head}.",
            )
    else:
        _run_git(root, "update-ref", recovery_ref, original_head)

    reset = _run_git(target, "reset", "--keep", base_sha, check=False)
    if reset.returncode != 0:
        detail = _decode(reset.stderr).strip() or _decode(reset.stdout).strip() or "unknown reset failure"
        raise GitWorkflowError(
            "CLEANUP_NORMALIZATION_FAILED",
            f"Could not normalize {normalized_id} to verified base {base_sha}: {detail}",
        )
    normalized_head = _decode(_run_git(target, "rev-parse", "HEAD").stdout).strip()
    if normalized_head != base_sha:
        raise GitWorkflowError(
            "CLEANUP_NORMALIZATION_MISMATCH",
            f"Normalized head {normalized_head} does not match verified base {base_sha}.",
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "prepare-cleanup",
        "change_id": normalized_id,
        "normalized": True,
        "landing_mode": record["landing_mode"],
        "original_head": original_head,
        "normalized_head": normalized_head,
        "recovery_ref": recovery_ref,
    }


def cleanup_preview(repository: Path | str, *, change_id: str | None = None) -> dict[str, Any]:
    root = _repository_root(repository)
    change_id = _validate_change_id(change_id)
    governance = _load_change_governance()
    try:
        claims = {
            claim.branch: claim
            for claim in governance.load_worktree_claims(root)
        }
        entries = governance.discover_worktrees(root)
        primary = _primary_worktree(root)
    except governance.ClaimError as exc:
        raise GitWorkflowError(
            "CHANGE_GOVERNANCE_INVALID",
            str(exc),
        ) from exc

    records: list[dict[str, Any]] = []
    for entry in entries:
        if entry.path.resolve() == primary:
            continue
        if not entry.branch or not entry.branch.startswith("change/"):
            continue
        current_id = entry.branch.removeprefix("change/")
        if change_id is not None and current_id != change_id:
            continue
        claim = claims.get(entry.branch)
        blockers: list[str] = []
        landing_mode = None
        landing_commit = None
        base_sha = None
        if claim is None:
            blockers.append("CHANGE_CLAIM_MISSING")
            base = None
            merged = False
        else:
            if getattr(claim, "schema_version", 1) < 3 and claim.status != "closed":
                blockers.append("CHANGE_STATUS_NOT_CLOSED")
            base = claim.base
            evidence = _branch_landing_evidence(root, entry.branch, base)
            merged = bool(evidence["landed"])
            landing_mode = str(evidence["mode"])
            landing_commit = evidence["landing_commit"]
            base_sha = str(evidence["base_sha"])
            if not merged:
                blockers.append("CHANGE_BRANCH_UNMERGED")

        status_result = _run_git(
            entry.path,
            "status",
            "--porcelain",
            "--untracked-files=all",
            check=False,
        )
        if status_result.returncode != 0:
            clean = False
            blockers.append("WORKTREE_STATUS_UNAVAILABLE")
        else:
            clean = not _decode(status_result.stdout).strip()
            if not clean:
                blockers.append("WORKTREE_DIRTY")
        records.append(
            {
                "change_id": current_id,
                "branch": entry.branch,
                "path": str(entry.path),
                "head": entry.head,
                "base": base,
                "base_sha": base_sha,
                "registered": claim is not None,
                "clean": clean,
                "merged": merged,
                "landing_mode": landing_mode,
                "landing_commit": landing_commit,
                "long_path_risk": _long_path_risk(entry.path),
                "eligible": not blockers,
                "blockers": blockers,
            }
        )
    records.sort(key=lambda item: item["change_id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "cleanup-preview",
        "repository": str(root),
        "worktrees": records,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded local Git workflow evidence commands.")
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)
    diff = subparsers.add_parser("diff-summary")
    diff.add_argument("--base", default="main")
    diff.add_argument("--head", default="HEAD")
    diff.add_argument("--path")
    diff.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    diff.add_argument("--max-output-bytes", type=int, default=DEFAULT_MAX_OUTPUT_BYTES)
    readiness = subparsers.add_parser("pr-readiness")
    readiness.add_argument("--base", default="main")
    cleanup = subparsers.add_parser("cleanup-preview")
    cleanup.add_argument("--change-id")
    prepare = subparsers.add_parser("prepare-cleanup")
    prepare.add_argument("--change-id", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "diff-summary":
            result = diff_summary(
                args.repository,
                base=args.base,
                head=args.head,
                path=args.path,
                max_files=args.max_files,
                max_output_bytes=args.max_output_bytes,
            )
        elif args.command == "pr-readiness":
            result = pr_readiness(args.repository, base=args.base)
        elif args.command == "cleanup-preview":
            result = cleanup_preview(args.repository, change_id=args.change_id)
        elif args.command == "prepare-cleanup":
            result = prepare_cleanup(args.repository, change_id=args.change_id)
        else:
            raise GitWorkflowError("COMMAND_UNSUPPORTED", f"Unsupported command: {args.command}")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except GitWorkflowError as exc:
        print(json.dumps(exc.to_json_dict(), sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
