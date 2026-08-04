from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from .paths import PathValidationError, normalize_windows_path


_VALUE_GLOBAL_OPTIONS = {
    "--config-env",
    "--exec-path",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--super-prefix",
}
_FLAG_GLOBAL_OPTIONS = {
    "--bare",
    "--paginate",
    "--no-pager",
    "--literal-pathspecs",
    "--glob-pathspecs",
    "--noglob-pathspecs",
    "--icase-pathspecs",
    "--no-optional-locks",
}
_REMOTE_OPERATIONS = {"clone", "fetch", "pull", "push", "ls-remote"}
_MAX_INCLUDE_DEPTH = 8
_MAX_CONFIG_BYTES = 256_000


@dataclass(frozen=True, slots=True)
class GitInvocation:
    operation: str
    tail: tuple[str, ...]
    cwd: str
    git_dir: str | None
    work_tree: str | None
    namespace: str | None
    config_overrides: tuple[str, ...]

    @property
    def remote_operation(self) -> bool:
        return self.operation in _REMOTE_OPERATIONS

    @property
    def mutation_paths(self) -> tuple[str, ...]:
        values: list[str | None] = [self.work_tree, self.git_dir]
        if self.git_dir:
            common = resolve_common_dir(self.git_dir)
            values.extend((common, str(Path(self.git_dir) / "index")))
            if common:
                values.append(str(Path(common) / "objects"))
        return tuple(dict.fromkeys(value for value in values if value))


def parse_git_invocation(tokens: list[str], *, cwd: str) -> GitInvocation:
    arguments = [_clean(value) for value in tokens[1:]]
    effective_cwd = cwd
    git_dir: str | None = None
    work_tree: str | None = None
    namespace: str | None = None
    overrides: list[str] = []
    index = 0

    while index < len(arguments):
        value = arguments[index]
        lowered = value.casefold()

        # Git's -C is case-sensitive and must be handled before -c.
        if value == "-C":
            if index + 1 < len(arguments):
                effective_cwd = _resolve(arguments[index + 1], effective_cwd) or effective_cwd
            index += 2
            continue
        if value.startswith("-C") and value != "-C" and not value.startswith("--"):
            effective_cwd = _resolve(value[2:], effective_cwd) or effective_cwd
            index += 1
            continue

        if value == "-c":
            if index + 1 < len(arguments):
                overrides.append(arguments[index + 1])
            index += 2
            continue
        if value.startswith("-c") and value != "-c" and not value.startswith("--"):
            overrides.append(value[2:])
            index += 1
            continue

        key, separator, inline = value.partition("=")
        lower_key = key.casefold()
        if lower_key in _VALUE_GLOBAL_OPTIONS:
            selected = inline if separator else (
                arguments[index + 1] if index + 1 < len(arguments) else ""
            )
            if lower_key == "--git-dir":
                git_dir = _resolve(selected, effective_cwd)
            elif lower_key == "--work-tree":
                work_tree = _resolve(selected, effective_cwd)
            elif lower_key == "--namespace":
                namespace = selected or None
            index += 1 if separator else 2
            continue
        if lowered in _FLAG_GLOBAL_OPTIONS:
            index += 1
            continue
        if value.startswith("-"):
            # Unsupported global flags are not themselves proof of a prohibited effect.
            index += 1
            continue

        operation = lowered
        tail = tuple(arguments[index + 1 :])
        if git_dir is None:
            git_dir = discover_git_dir(effective_cwd)
        if work_tree is None:
            work_tree = effective_cwd
        return GitInvocation(
            operation=operation,
            tail=tail,
            cwd=effective_cwd,
            git_dir=git_dir,
            work_tree=work_tree,
            namespace=namespace,
            config_overrides=tuple(overrides),
        )

    return GitInvocation(
        operation="",
        tail=(),
        cwd=effective_cwd,
        git_dir=git_dir,
        work_tree=work_tree,
        namespace=namespace,
        config_overrides=tuple(overrides),
    )


def discover_git_dir(cwd: str) -> str | None:
    marker = Path(cwd) / ".git"
    if marker.is_dir():
        return str(marker)
    if marker.is_file():
        try:
            declaration = marker.read_text(encoding="utf-8-sig").strip()
        except (OSError, UnicodeError):
            return None
        if declaration.casefold().startswith("gitdir:"):
            raw = declaration.split(":", 1)[1].strip()
            candidate = Path(raw)
            target = candidate if candidate.is_absolute() else marker.parent / candidate
            return str(target.resolve(strict=False))
    return None


def resolve_common_dir(git_dir: str) -> str:
    marker = Path(git_dir) / "commondir"
    if marker.is_file():
        try:
            raw = marker.read_text(encoding="utf-8-sig").strip()
        except (OSError, UnicodeError):
            return git_dir
        candidate = Path(raw)
        target = candidate if candidate.is_absolute() else Path(git_dir) / candidate
        return str(target.resolve(strict=False))
    return git_dir


def git_remote_targets(invocation: GitInvocation) -> tuple[str, ...]:
    if not invocation.remote_operation:
        return ()

    if invocation.operation in {"clone", "ls-remote"}:
        values = _positional_values(invocation.tail)
        return tuple(values[:1])

    explicit_repo = _option_value(invocation.tail, "--repo")
    if explicit_repo:
        return (explicit_repo,)

    config = _load_effective_config(invocation)
    if _has_option(invocation.tail, "--all"):
        urls: list[str] = []
        for remote in config.remote_names():
            urls.extend(config.remote_urls(remote, push=invocation.operation == "push"))
        return tuple(dict.fromkeys(urls))

    values = _positional_values(invocation.tail, skip_value_options={"--repo"})
    remote = values[0] if values else None
    if remote and _looks_like_explicit_repository(remote):
        return (remote,)

    selected = remote or config.default_remote(
        invocation.operation,
        current_branch(invocation.git_dir),
    )
    if not selected:
        names = config.remote_names()
        selected = names[0] if len(names) == 1 else None
    if not selected or selected == ".":
        return ()

    urls = config.remote_urls(selected, push=invocation.operation == "push")
    return tuple(urls or (selected,))


def current_branch(git_dir: str | None) -> str | None:
    if not git_dir:
        return None
    try:
        head = (Path(git_dir) / "HEAD").read_text(encoding="utf-8-sig").strip()
    except (OSError, UnicodeError):
        return None
    prefix = "ref: refs/heads/"
    return head[len(prefix) :] if head.startswith(prefix) else None


class GitConfig:
    def __init__(self) -> None:
        self._values: dict[tuple[str, str], list[str]] = {}

    def add(self, section: str, key: str, value: str) -> None:
        self._values.setdefault((section.casefold(), key.casefold()), []).append(value)

    def getall(self, section: str, key: str) -> tuple[str, ...]:
        return tuple(self._values.get((section.casefold(), key.casefold()), ()))

    def get(self, section: str, key: str) -> str | None:
        values = self.getall(section, key)
        return values[-1] if values else None

    def remote_names(self) -> list[str]:
        names: set[str] = set()
        for section, _key in self._values:
            match = re.fullmatch(r'remote\s+"(.+)"', section, re.IGNORECASE)
            if match:
                names.add(match.group(1))
        return sorted(names, key=str.casefold)

    def remote_urls(self, remote: str, *, push: bool) -> list[str]:
        section = f'remote "{remote}"'
        if push:
            pushurls = list(self.getall(section, "pushurl"))
            if pushurls:
                return pushurls
        return list(self.getall(section, "url"))

    def default_remote(self, operation: str, branch: str | None) -> str | None:
        if branch:
            section = f'branch "{branch}"'
            if operation == "push":
                value = self.get(section, "pushremote") or self.get(
                    "remote", "pushdefault"
                )
                if value:
                    return value
            value = self.get(section, "remote")
            if value:
                return value
        if operation == "push":
            return self.get("remote", "pushdefault")
        return None


def _load_effective_config(invocation: GitInvocation) -> GitConfig:
    config = GitConfig()
    if invocation.git_dir:
        common = resolve_common_dir(invocation.git_dir)
        _load_config_file(
            Path(common) / "config",
            config,
            invocation,
            depth=0,
            seen=set(),
        )
        _load_config_file(
            Path(invocation.git_dir) / "config.worktree",
            config,
            invocation,
            depth=0,
            seen=set(),
        )
    for override in invocation.config_overrides:
        key, separator, value = override.partition("=")
        if not separator:
            continue
        parsed = _split_config_key(key)
        if parsed is not None:
            section, name = parsed
            config.add(section, name, value)
    return config


def _split_config_key(key: str) -> tuple[str, str] | None:
    parts = key.split(".")
    if len(parts) < 2:
        return None
    if len(parts) >= 3 and parts[0].casefold() in {"remote", "branch"}:
        return f'{parts[0]} "{parts[1]}"', ".".join(parts[2:])
    return ".".join(parts[:-1]), parts[-1]


def _load_config_file(
    path: Path,
    config: GitConfig,
    invocation: GitInvocation,
    *,
    depth: int,
    seen: set[Path],
) -> None:
    if depth > _MAX_INCLUDE_DEPTH:
        return
    try:
        resolved = path.resolve(strict=True)
        if resolved in seen or resolved.stat().st_size > _MAX_CONFIG_BYTES:
            return
        text = resolved.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return

    seen.add(resolved)
    section = ""
    includes: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        match = re.fullmatch(r"\[(.+)]", line)
        if match:
            section = match.group(1).strip()
            continue
        key, separator, value = line.partition("=")
        if not separator:
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            key, value = parts
        key = key.strip()
        value = value.strip().strip('"')
        if section.casefold() == "include" and key.casefold() == "path":
            includes.append(value)
            continue
        if section.casefold().startswith("includeif ") and key.casefold() == "path":
            if _include_condition_matches(section, invocation):
                includes.append(value)
            continue
        config.add(section, key, value)

    for raw in includes:
        if not raw or "://" in raw:
            continue
        candidate = Path(raw).expanduser()
        include = candidate if candidate.is_absolute() else resolved.parent / candidate
        _load_config_file(
            include,
            config,
            invocation,
            depth=depth + 1,
            seen=seen,
        )


def _include_condition_matches(section: str, invocation: GitInvocation) -> bool:
    match = re.fullmatch(r'includeif\s+"(.+)"', section, re.IGNORECASE)
    if not match:
        return False
    condition = match.group(1)
    lowered = condition.casefold()
    if lowered.startswith(("gitdir:", "gitdir/i:")) and invocation.git_dir:
        prefix = "gitdir/i:" if lowered.startswith("gitdir/i:") else "gitdir:"
        pattern = condition[len(prefix) :].replace("\\", "/").rstrip("*").casefold()
        actual = invocation.git_dir.replace("\\", "/").casefold()
        return actual.startswith(pattern)
    if lowered.startswith("onbranch:"):
        branch = current_branch(invocation.git_dir) or ""
        pattern = condition.split(":", 1)[1].rstrip("*").casefold()
        return branch.casefold().startswith(pattern)
    return False


def _option_value(arguments: Iterable[str], option: str) -> str | None:
    values = list(arguments)
    for index, value in enumerate(values):
        key, separator, inline = value.partition("=")
        if key.casefold() != option.casefold():
            continue
        if separator:
            return inline
        if index + 1 < len(values):
            return values[index + 1]
    return None


def _has_option(arguments: Iterable[str], option: str) -> bool:
    expected = option.casefold()
    return any(
        value.casefold() == expected or value.casefold().startswith(expected + "=")
        for value in arguments
    )


def _positional_values(
    arguments: Iterable[str],
    *,
    skip_value_options: set[str] | None = None,
) -> list[str]:
    skip = {value.casefold() for value in (skip_value_options or set())}
    values = list(arguments)
    positional: list[str] = []
    index = 0
    while index < len(values):
        value = values[index]
        key = value.split("=", 1)[0].casefold()
        if key in skip:
            index += 1 if "=" in value else 2
            continue
        if value.startswith("-"):
            index += 1
            continue
        positional.append(value)
        index += 1
    return positional


def _looks_like_explicit_repository(value: str) -> bool:
    lowered = value.casefold()
    return (
        "://" in value
        or value.startswith(("\\\\", ".\\", "..\\", "./", "../"))
        or bool(re.match(r"(?i)^[a-z]:[\\/]", value))
        or lowered.startswith("file:")
        or bool(re.match(r"^[^@\s]+@[^:\s]+:", value))
    )


def _clean(value: str) -> str:
    return value.strip().strip("\"'").rstrip(",;")


def _resolve(value: str, cwd: str) -> str | None:
    if not value or any(marker in value for marker in ("$env:", "%", "${", "$(")):
        return None
    try:
        return normalize_windows_path(value, base=cwd)
    except PathValidationError:
        return None


__all__ = [
    "GitInvocation",
    "current_branch",
    "discover_git_dir",
    "git_remote_targets",
    "parse_git_invocation",
    "resolve_common_dir",
]
