#!/usr/bin/env python3
"""Collect bounded, read-only seam evidence from a trusted Git repository."""

from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import combinations
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import Any


CODE_EXT = {
    ".c", ".cpp", ".cs", ".go", ".h", ".hpp", ".java", ".js", ".jsx",
    ".kt", ".php", ".py", ".rb", ".rs", ".scala", ".sh", ".sql",
    ".swift", ".ts", ".tsx",
}
DOC_EXT = {".adoc", ".md", ".rst", ".txt"}
DEPENDENCY_EXT = {".js", ".jsx", ".py", ".ts", ".tsx"}
SKIP_DIRS = {
    ".git", ".idea", ".mypy_cache", ".pytest_cache", ".tox", ".venv",
    "__pycache__", "build", "dist", "node_modules", "target", "vendor", "venv",
}
IMPORT_RE = re.compile(
    r"(?:^\s*(?:from|import)\s+([\w./]+))"
    r"|(?:from\s+['\"]([^'\"]+)['\"])"
    r"|(?:require\(\s*['\"]([^'\"]+)['\"]\s*\))",
    re.MULTILINE,
)
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_FILES = 20_000
DEFAULT_MAX_COMMITS = 5_000
MAX_GIT_OUTPUT_BYTES = 16 * 1024 * 1024


class CollectorError(RuntimeError):
    """A safe, user-actionable collection failure."""


def git_environment() -> dict[str, str]:
    """Return the minimum ambient environment needed for local Git commands."""
    allowed = (
        "COMSPEC", "HOME", "HOMEDRIVE", "HOMEPATH", "LANG", "LC_ALL", "PATH",
        "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE", "WINDIR",
    )
    env = {name: os.environ[name] for name in allowed if name in os.environ}
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"})
    safe_directories = []
    try:
        config_count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    except ValueError:
        config_count = 0
    for index in range(config_count):
        if os.environ.get(f"GIT_CONFIG_KEY_{index}") == "safe.directory":
            value = os.environ.get(f"GIT_CONFIG_VALUE_{index}")
            if value:
                safe_directories.append(value)
    if safe_directories:
        env["GIT_CONFIG_COUNT"] = str(len(safe_directories))
        for index, value in enumerate(safe_directories):
            env[f"GIT_CONFIG_KEY_{index}"] = "safe.directory"
            env[f"GIT_CONFIG_VALUE_{index}"] = value
    return env


def run_git(repo: Path, args: list[str], timeout_seconds: int) -> str:
    command = ["git", "-C", str(repo), *args]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            env=git_environment(),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise CollectorError(f"git command timed out after {timeout_seconds}s: {' '.join(args)}") from exc
    except OSError as exc:
        raise CollectorError(f"could not start git: {exc}") from exc

    if len(result.stdout) > MAX_GIT_OUTPUT_BYTES or len(result.stderr) > MAX_GIT_OUTPUT_BYTES:
        raise CollectorError("git output exceeded the 16 MiB safety limit")
    stdout = result.stdout.decode("utf-8", errors="strict")
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    if result.returncode != 0:
        raise CollectorError(f"git {' '.join(args)} failed: {stderr or 'no diagnostic'}")
    return stdout


def resolve_repo(raw_repo: str, timeout_seconds: int) -> Path:
    try:
        candidate = Path(raw_repo).resolve(strict=True)
    except OSError as exc:
        raise CollectorError(f"cannot resolve repository path {raw_repo!r}: {exc}") from exc
    if not candidate.is_dir():
        raise CollectorError(f"repository path is not a directory: {raw_repo}")
    root_text = run_git(candidate, ["rev-parse", "--show-toplevel"], timeout_seconds).strip()
    root = Path(root_text).resolve(strict=True)
    if os.path.normcase(str(candidate)) != os.path.normcase(str(root)):
        raise CollectorError("--repo must identify the trusted Git worktree root")
    return root


def is_link_or_reparse(path: Path) -> bool:
    details = path.lstat()
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(details, "st_file_attributes", 0)
    return stat.S_ISLNK(details.st_mode) or bool(attributes & reparse_flag)


def validate_tracked_path(repo: Path, relative: str) -> Path:
    logical = PurePosixPath(relative)
    if logical.is_absolute() or not logical.parts or any(part in ("", ".", "..") for part in logical.parts):
        raise CollectorError(f"git returned an unsafe tracked path: {relative!r}")
    path = repo.joinpath(*logical.parts)
    try:
        if is_link_or_reparse(path):
            raise CollectorError(f"refusing linked or reparse-point path: {relative}")
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CollectorError(f"cannot inspect tracked path {relative!r}: {exc}") from exc
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise CollectorError(f"tracked path escapes repository root: {relative}") from exc
    if not resolved.is_file():
        raise CollectorError(f"tracked path is not a regular file: {relative}")
    return resolved


def tracked_files(
    repo: Path,
    include_docs: bool,
    timeout_seconds: int,
    max_files: int,
) -> list[str]:
    raw = run_git(repo, ["-c", "core.quotepath=false", "ls-files", "-z"], timeout_seconds)
    extensions = CODE_EXT | (DOC_EXT if include_docs else set())
    selected: list[str] = []
    for relative in raw.split("\0"):
        if not relative:
            continue
        logical = PurePosixPath(relative)
        if any(part in SKIP_DIRS for part in logical.parts):
            continue
        if logical.suffix.lower() not in extensions:
            continue
        validate_tracked_path(repo, relative)
        selected.append(relative)
        if len(selected) > max_files:
            raise CollectorError(f"tracked input exceeds --max-files={max_files}")
    return sorted(selected)


def unit_of(path: str, granularity: str, depth: int) -> str:
    if granularity == "file":
        return path
    parts = path.split("/")
    if len(parts) <= 1:
        return "<root>"
    return "/".join(parts[: min(depth, len(parts) - 1)])


def collect_history(
    repo: Path,
    tracked: set[str],
    since: str,
    granularity: str,
    depth: int,
    timeout_seconds: int,
    max_commits: int,
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[tuple[str, str], int], int]:
    raw = run_git(
        repo,
        [
            "-c", "core.quotepath=false", "log", f"--since={since}",
            f"--max-count={max_commits + 1}", "--name-only", "--pretty=format:%x01%H%x02%s",
            "--no-merges", "--",
        ],
        timeout_seconds,
    )
    unit_commits: dict[str, set[str]] = defaultdict(set)
    unit_subjects: dict[str, set[str]] = defaultdict(set)
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    relevant_commits = 0
    blocks = [block for block in raw.split("\x01") if block.strip()]
    if len(blocks) > max_commits:
        raise CollectorError(f"history exceeds --max-commits={max_commits}")
    for block in blocks:
        if not block.strip():
            continue
        header, _, names = block.partition("\n")
        sha, _, subject = header.partition("\x02")
        touched = {
            unit_of(name.strip(), granularity, depth)
            for name in names.splitlines()
            if name.strip() in tracked
        }
        if not sha.strip() or not touched:
            continue
        relevant_commits += 1
        for unit in touched:
            unit_commits[unit].add(sha.strip())
            unit_subjects[unit].add(subject.strip().lower())
        for left, right in combinations(sorted(touched), 2):
            pair_counts[(left, right)] += 1
    return unit_commits, unit_subjects, pair_counts, relevant_commits


def collect_sizes(
    repo: Path,
    tracked: list[str],
    granularity: str,
    depth: int,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    sizes: dict[str, int] = defaultdict(int)
    files: dict[str, list[str]] = defaultdict(list)
    for relative in tracked:
        path = repo.joinpath(*PurePosixPath(relative).parts)
        try:
            with path.open("r", encoding="utf-8", errors="strict") as handle:
                line_count = sum(1 for _ in handle)
        except (OSError, UnicodeError) as exc:
            raise CollectorError(f"cannot read tracked text file {relative!r}: {exc}") from exc
        unit = unit_of(relative, granularity, depth)
        sizes[unit] += line_count
        files[unit].append(relative)
    return sizes, files


def dependency_evidence_complete(tracked: list[str]) -> bool:
    return bool(tracked) and all(PurePosixPath(path).suffix.lower() in DEPENDENCY_EXT for path in tracked)


def dependency_tokens(files: dict[str, list[str]]) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for unit, paths in files.items():
        for path in paths:
            stem = str(PurePosixPath(path).with_suffix(""))
            tokens.setdefault(stem.replace("/", "."), unit)
            tokens.setdefault(stem, unit)
            base = PurePosixPath(stem).name
            if len(base) > 3:
                tokens.setdefault(base, unit)
        head = unit.split("/")[-1]
        if len(head) > 3:
            tokens.setdefault(head, unit)
    return tokens


def collect_edges(repo: Path, files: dict[str, list[str]]) -> tuple[dict[str, int], dict[str, int]]:
    token_to_unit = dependency_tokens(files)
    edges: set[tuple[str, str]] = set()
    for unit, paths in files.items():
        for relative in paths:
            path = repo.joinpath(*PurePosixPath(relative).parts)
            try:
                text = path.read_text(encoding="utf-8", errors="strict")
            except (OSError, UnicodeError) as exc:
                raise CollectorError(f"cannot read tracked text file {relative!r}: {exc}") from exc
            for match in IMPORT_RE.finditer(text):
                spec = next((group for group in match.groups() if group), "")
                normalized = spec.strip("./").replace("/", ".")
                target = token_to_unit.get(normalized) or token_to_unit.get(normalized.split(".")[-1])
                if target and target != unit:
                    edges.add((unit, target))
    fan_in: dict[str, int] = defaultdict(int)
    fan_out: dict[str, int] = defaultdict(int)
    for source, target in edges:
        fan_out[source] += 1
        fan_in[target] += 1
    return fan_in, fan_out


def cochange_peers(
    unit_commits: dict[str, set[str]],
    pair_counts: dict[tuple[str, str], int],
    total: int,
    top_peers: int,
) -> dict[str, list[dict[str, Any]]]:
    peers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (left, right), count in pair_counts.items():
        for source, target in ((left, right), (right, left)):
            denominator = len(unit_commits.get(source, ())) or 1
            peers[source].append({
                "peer": target,
                "pair_commits": count,
                "support": round(count / total, 3) if total else 0.0,
                "confidence": round(count / denominator, 3),
            })
    for unit in peers:
        peers[unit].sort(key=lambda item: (-item["confidence"], -item["pair_commits"], item["peer"]))
        peers[unit] = peers[unit][:top_peers]
    return peers


def build_rows(
    unit_commits: dict[str, set[str]],
    unit_subjects: dict[str, set[str]],
    pair_counts: dict[tuple[str, str], int],
    total: int,
    sizes: dict[str, int],
    fan_in: dict[str, int],
    fan_out: dict[str, int],
    dependency_measured: bool,
    top_peers: int,
) -> list[dict[str, Any]]:
    peers = cochange_peers(unit_commits, pair_counts, total, top_peers)
    rows: list[dict[str, Any]] = []
    for unit in sorted(set(sizes) | set(unit_commits)):
        rows.append({
            "unit": unit,
            "loc": sizes.get(unit, 0),
            "commits": len(unit_commits.get(unit, ())),
            "distinct_subjects": len(unit_subjects.get(unit, ())),
            "fan_in": fan_in.get(unit, 0) if dependency_measured else None,
            "fan_out": fan_out.get(unit, 0) if dependency_measured else None,
            "cochange_peers": peers.get(unit, []),
            "provenance": {
                "loc": "M",
                "commits": "M",
                "distinct_subjects": "M",
                "fan_in": "M" if dependency_measured else "U",
                "fan_out": "M" if dependency_measured else "U",
                "cochange_peers": "M",
            },
        })
    return rows


def select_rows(rows: list[dict[str, Any]], top: int, requested_units: list[str]) -> tuple[list[dict[str, Any]], str]:
    if requested_units:
        requested = set(requested_units)
        known = {row["unit"] for row in rows}
        missing = sorted(requested - known)
        if missing:
            raise CollectorError(f"requested units were not found: {', '.join(missing)}")
        rows = [row for row in rows if row["unit"] in requested]
    if len(rows) <= top:
        return sorted(rows, key=lambda row: row["unit"]), "all enumerated units"

    by_size = sorted(rows, key=lambda row: (-row["loc"], -row["commits"], row["unit"]))
    by_churn = sorted(rows, key=lambda row: (-row["commits"], -row["loc"], row["unit"]))
    selected: dict[str, dict[str, Any]] = {}
    for index in range(len(rows)):
        for ranking in (by_size, by_churn):
            selected.setdefault(ranking[index]["unit"], ranking[index])
            if len(selected) == top:
                ordered = sorted(selected.values(), key=lambda row: (-row["loc"], -row["commits"], row["unit"]))
                return ordered, "alternating highest LOC and highest commit count"
    raise CollectorError("could not construct the bounded sample")


def measured(value: Any, provenance: str) -> str:
    return "U" if provenance == "U" else f"{value} ({provenance})"


def render_markdown(rows: list[dict[str, Any]], relevant_commits: int, args: argparse.Namespace, sampling: str) -> str:
    lines = [
        "# Seam evidence (Gate 1)",
        "",
        "Repository: tracked Git root (absolute path omitted)",
        f"Window: `{args.since}` | Relevant commits: {relevant_commits} | Granularity: {args.granularity}/{args.depth}",
        f"Sampling: {sampling}",
        "",
        "| Unit | LOC | Commits | Distinct subjects | Fan-in | Fan-out | Top co-change peer |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        provenance = row["provenance"]
        peer = row["cochange_peers"][0] if row["cochange_peers"] else None
        peer_text = f"{peer['peer']} ({peer['confidence']}/{peer['support']}) (M)" if peer else "- (M)"
        lines.append(
            f"| `{row['unit']}` | {measured(row['loc'], provenance['loc'])} "
            f"| {measured(row['commits'], provenance['commits'])} "
            f"| {measured(row['distinct_subjects'], provenance['distinct_subjects'])} "
            f"| {measured(row['fan_in'], provenance['fan_in'])} "
            f"| {measured(row['fan_out'], provenance['fan_out'])} | {peer_text} |"
        )
    lines.extend([
        "",
        "## Limits",
        "",
        "- Distinct subjects are not RFC kinds; cluster them before scoring.",
        "- Fan-in and fan-out are M only for Python and JavaScript/TypeScript-only inputs.",
        "- Read-set/edit-set, hidden coupling, and test isolation remain U until measured separately.",
        "",
    ])
    return "\n".join(lines)


def render_json(rows: list[dict[str, Any]], relevant_commits: int, args: argparse.Namespace, sampling: str) -> str:
    return json.dumps({
        "repo": ".",
        "since": args.since,
        "relevant_commits": relevant_commits,
        "granularity": args.granularity,
        "depth": args.depth,
        "sampling": sampling,
        "units": rows,
        "caveats": [
            "distinct_subjects is not RFC kinds",
            "fan_in and fan_out are unmeasured for unsupported or mixed dependency languages",
        ],
    }, indent=2, sort_keys=True)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect bounded, read-only structural seam evidence.",
        epilog=(
            "Examples: seams.py --repo . --format md; "
            "seams.py --repo . --unit src --top 10 --format json"
        ),
    )
    parser.add_argument("--repo", default=".", help="trusted Git worktree root")
    parser.add_argument("--since", default="90 days ago", help="Git date expression")
    parser.add_argument("--granularity", choices=("file", "dir"), default="dir")
    parser.add_argument("--depth", type=int, default=1, help="directory grouping depth")
    parser.add_argument("--top", type=int, default=25, help="maximum units to report (1-25)")
    parser.add_argument("--top-peers", type=int, default=3, help="co-change peers per unit (0-10)")
    parser.add_argument("--unit", action="append", default=[], help="exact unit to include; repeatable")
    parser.add_argument("--include-docs", action="store_true", help="include tracked documentation files")
    parser.add_argument("--format", choices=("md", "json"), default="md")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-commits", type=int, default=DEFAULT_MAX_COMMITS)
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    if not 1 <= args.top <= 25:
        raise CollectorError("--top must be between 1 and 25")
    if not 0 <= args.top_peers <= 10:
        raise CollectorError("--top-peers must be between 0 and 10")
    if not 1 <= args.depth <= 10:
        raise CollectorError("--depth must be between 1 and 10")
    if not 1 <= args.timeout_seconds <= 120:
        raise CollectorError("--timeout-seconds must be between 1 and 120")
    if not 1 <= args.max_files <= 100_000:
        raise CollectorError("--max-files must be between 1 and 100000")
    if not 1 <= args.max_commits <= 100_000:
        raise CollectorError("--max-commits must be between 1 and 100000")


def collect(args: argparse.Namespace) -> tuple[list[dict[str, Any]], str, int]:
    validate_args(args)
    repo = resolve_repo(args.repo, args.timeout_seconds)
    tracked = tracked_files(repo, args.include_docs, args.timeout_seconds, args.max_files)
    unit_commits, unit_subjects, pair_counts, relevant_commits = collect_history(
        repo, set(tracked), args.since, args.granularity, args.depth,
        args.timeout_seconds, args.max_commits,
    )
    sizes, files = collect_sizes(repo, tracked, args.granularity, args.depth)
    dependency_measured = dependency_evidence_complete(tracked)
    fan_in, fan_out = collect_edges(repo, files) if dependency_measured else ({}, {})
    rows = build_rows(
        unit_commits, unit_subjects, pair_counts, relevant_commits, sizes,
        fan_in, fan_out, dependency_measured, args.top_peers,
    )
    return (*select_rows(rows, args.top, args.unit), relevant_commits)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        rows, sampling, relevant_commits = collect(args)
        if args.format == "json":
            output = render_json(rows, relevant_commits, args, sampling)
        else:
            output = render_markdown(rows, relevant_commits, args, sampling)
        print(output)
        return 0
    except (CollectorError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
