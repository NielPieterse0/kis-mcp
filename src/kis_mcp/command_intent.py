from __future__ import annotations

import configparser
import re
import shlex
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

from .models import InvocationEffects
from .paths import PathValidationError, normalize_windows_path

_REDIRECT_RE = re.compile(
    r"(?<![<])(?:>>|>)\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s;&|]+))"
)

_NETWORK_PROGRAMS = {
    "curl",
    "wget",
    "invoke-webrequest",
    "iwr",
    "invoke-restmethod",
    "irm",
    "ssh",
    "scp",
    "sftp",
    "ftp",
    "telnet",
    "nc",
    "ncat",
}

_NETWORK_TARGET_OPTIONS = {
    "--url",
    "-uri",
}
_NETWORK_VALUE_OPTIONS = {
    "-a",
    "--user-agent",
    "-b",
    "--cookie",
    "-c",
    "--cookie-jar",
    "-d",
    "--data",
    "--data-ascii",
    "--data-binary",
    "--data-raw",
    "-e",
    "--referer",
    "-h",
    "--header",
    "-o",
    "--output",
    "-u",
    "--user",
    "-x",
    "--proxy",
    "-x",
    "--request",
    "--connect-to",
    "--resolve",
    "-i",
    "--identity-file",
    "-p",
    "--port",
    "-l",
    "--login-name",
    "-f",
    "--config",
    "-headers",
    "-outfile",
    "-method",
    "-body",
    "-contenttype",
    "-credential",
    "-timeoutsec",
}
_NETWORK_FLAG_OPTIONS = {
    "-4",
    "-6",
    "-i",
    "--include",
    "-k",
    "--insecure",
    "-l",
    "--location",
    "-s",
    "--silent",
    "-v",
    "--verbose",
    "--fail",
    "--head",
    "--compressed",
    "-usebasicparsing",
    "-batchmode",
    "-n",
    "-q",
    "-t",
    "-v",
    "-z",
}

_PACKAGE_COMMANDS = {
    "npm": {"install", "i", "ci", "update", "add"},
    "pnpm": {"install", "i", "update", "add"},
    "yarn": {"install", "add", "upgrade", "up"},
    "pip": {"install", "download"},
    "pip3": {"install", "download"},
    "uv": {"add", "sync", "lock"},
    "winget": {"install", "upgrade", "search"},
    "choco": {"install", "upgrade", "search"},
    "scoop": {"install", "update", "search"},
}
_PACKAGE_ENDPOINT_OPTIONS = {
    "--registry",
    "--source",
    "--index-url",
    "--extra-index-url",
    "--find-links",
    "-i",
    "-f",
}
_PACKAGE_VALUE_OPTIONS = {
    "--cache-dir",
    "--target",
    "--prefix",
    "--root",
    "--python",
    "--config-settings",
    "--constraint",
    "-c",
    "--requirement",
    "-r",
}
_PACKAGE_REMOTE_PREFIXES = (
    "git+http://",
    "git+https://",
    "git+ssh://",
    "git://",
    "github:",
    "gitlab:",
    "bitbucket:",
)

_REMOTE_GIT_COMMANDS = {"clone", "fetch", "pull", "push", "ls-remote"}
_LOCAL_GIT_WRITE_COMMANDS = {
    "add",
    "checkout",
    "cherry-pick",
    "commit",
    "merge",
    "reset",
    "restore",
    "revert",
    "switch",
}
_GIT_BRANCH_MUTATION_OPTIONS = {
    "-c",
    "-C",
    "-d",
    "-D",
    "-f",
    "-m",
    "-M",
    "--copy",
    "--delete",
    "--edit-description",
    "--force",
    "--move",
    "--set-upstream-to",
    "--track",
    "--unset-upstream",
}
_GIT_BRANCH_READ_VALUE_OPTIONS = {
    "--abbrev",
    "--color",
    "--column",
    "--contains",
    "--format",
    "--merged",
    "--no-contains",
    "--no-merged",
    "--points-at",
    "--sort",
}
_GIT_TAG_MUTATION_OPTIONS = {
    "-a",
    "-d",
    "-f",
    "-s",
    "-u",
    "--annotate",
    "--delete",
    "--force",
    "--local-user",
    "--sign",
}
_GIT_TAG_READ_VALUE_OPTIONS = {
    "--color",
    "--column",
    "--contains",
    "--format",
    "--merged",
    "--no-contains",
    "--no-merged",
    "--points-at",
    "--sort",
}

_DELETE_PROGRAMS = {
    "del",
    "erase",
    "rd",
    "rmdir",
    "rm",
    "remove-item",
    "unlink",
    "shred",
}

_COPY_PROGRAMS = {"copy", "copy-item", "cp", "xcopy"}
_MOVE_PROGRAMS = {"move", "move-item", "mv"}
_CREATE_PROGRAMS = {"mkdir", "md", "new-item", "touch"}
_WRITE_CMDLETS = {
    "add-content",
    "out-file",
    "set-content",
    "tee-object",
}
_SHELL_WRAPPERS = {"cmd", "powershell", "pwsh"}
_MAX_NESTED_COMMAND_DEPTH = 4


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=False)
    except ValueError:
        return command.split()


def _split_shell_segments(command: str) -> list[str]:
    segments: list[str] = []
    current: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(command):
        character = command[index]
        if quote is not None:
            current.append(character)
            if character == quote:
                quote = None
            elif character in {"`", "^", "\\"} and index + 1 < len(command):
                index += 1
                current.append(command[index])
            index += 1
            continue

        if character in {"\"", "'"}:
            quote = character
            current.append(character)
            index += 1
            continue
        if character in {"`", "^"} and index + 1 < len(command):
            current.append(character)
            index += 1
            current.append(command[index])
            index += 1
            continue

        separator_length = 0
        if command.startswith("&&", index) or command.startswith("||", index):
            separator_length = 2
        elif character in {";", "|", "\n", "\r"}:
            separator_length = 1
        if separator_length:
            segment = "".join(current).strip()
            if segment:
                segments.append(segment)
            current = []
            index += separator_length
            continue

        current.append(character)
        index += 1

    segment = "".join(current).strip()
    if segment:
        segments.append(segment)
    return segments or ([command.strip()] if command.strip() else [])


def _clean_token(token: str) -> str:
    return token.strip().strip("\"'").rstrip(",;)")


def _wrapped_command_payload(tokens: list[str]) -> str | None:
    if not tokens:
        return None
    program = _program_name(tokens[0])
    if program not in _SHELL_WRAPPERS:
        return None

    arguments = [_clean_token(token) for token in tokens[1:]]
    markers = {"/c", "/k"} if program == "cmd" else {"-command", "-c"}
    for index, argument in enumerate(arguments):
        if argument.casefold() in markers and index + 1 < len(arguments):
            payload = " ".join(arguments[index + 1 :]).strip()
            return payload or None
    return None


def _program_name(token: str) -> str:
    clean = _clean_token(token).replace("/", "\\")
    clean = clean.rsplit("\\", 1)[-1].casefold()
    if clean.endswith((".exe", ".cmd", ".bat")):
        clean = clean.rsplit(".", 1)[0]
    return clean


def _is_local_host(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip("[]").casefold()
    return normalized in {"localhost", "127.0.0.1", "::1"} or normalized.endswith(
        ".localhost"
    )


def _parsed_remote_url(value: str):
    clean = _clean_token(value)
    lowered = clean.casefold()
    if lowered.startswith("git+"):
        clean = clean[4:]
    return urlparse(clean)


def _looks_like_local_target(token: str, *, cwd: str) -> bool:
    clean = _clean_token(token)
    if not clean:
        return False

    parsed = _parsed_remote_url(clean)
    if parsed.scheme.casefold() in {"http", "https", "ftp", "ssh", "git"}:
        return _is_local_host(parsed.hostname)
    if parsed.scheme.casefold() == "file":
        return True

    lowered = clean.casefold()
    if lowered in {"localhost", "127.0.0.1", "::1", ".", ".."}:
        return True
    if clean.isdigit():
        return True
    if clean.startswith((".\\", "..\\", "./", "../")):
        return True
    if re.match(r"(?i)^[a-z]:[\\/]", clean):
        return True
    if clean.startswith("\\\\"):
        host = clean.lstrip("\\").split("\\", 1)[0]
        return _is_local_host(host)
    scp_match = re.match(r"^[^@\s]+@([^:\s]+):", clean)
    if scp_match:
        return _is_local_host(scp_match.group(1))
    if Path(cwd, clean).exists():
        return True
    if lowered.endswith((".whl", ".zip", ".tar.gz", ".tgz")):
        return True
    return False


def _external_target(token: str, *, cwd: str) -> bool:
    clean = _clean_token(token)
    if not clean or clean.startswith("-"):
        return False
    if _looks_like_local_target(clean, cwd=cwd):
        return False

    parsed = _parsed_remote_url(clean)
    if parsed.scheme.casefold() in {"http", "https", "ftp", "ssh", "git"}:
        return not _is_local_host(parsed.hostname)
    if clean.startswith("\\\\"):
        host = clean.lstrip("\\").split("\\", 1)[0]
        return not _is_local_host(host)
    match = re.match(r"^[^@\s]+@([^:\s]+):", clean)
    if match:
        return not _is_local_host(match.group(1))
    return True


def _explicit_remote_reference(token: str, *, cwd: str) -> bool:
    clean = _clean_token(token)
    if not clean:
        return False
    lowered = clean.casefold()
    if lowered.startswith(_PACKAGE_REMOTE_PREFIXES):
        return _external_target(clean, cwd=cwd)
    parsed = _parsed_remote_url(clean)
    if parsed.scheme.casefold() in {"http", "https", "ftp", "ssh", "git"}:
        return not _is_local_host(parsed.hostname)
    if clean.startswith("\\\\"):
        return _external_target(clean, cwd=cwd)
    return bool(re.match(r"^[^@\s]+@([^:\s]+):", clean)) and _external_target(
        clean, cwd=cwd
    )


def _operation_and_tail(tokens: list[str]) -> tuple[str, list[str]]:
    arguments = [_clean_token(token) for token in tokens[1:]]
    for index, value in enumerate(arguments):
        if value and not value.startswith(("-", "/")):
            return value.casefold(), arguments[index + 1 :]
    return "", []


def _network_targets(tokens: list[str]) -> list[str]:
    targets: list[str] = []
    arguments = [_clean_token(token) for token in tokens[1:]]
    index = 0
    while index < len(arguments):
        value = arguments[index]
        lowered = value.casefold()
        key, separator, inline_value = lowered.partition("=")
        if separator and key in _NETWORK_TARGET_OPTIONS:
            targets.append(value.partition("=")[2])
            index += 1
            continue
        if separator and key in _NETWORK_VALUE_OPTIONS:
            index += 1
            continue
        if lowered in _NETWORK_TARGET_OPTIONS:
            if index + 1 < len(arguments):
                targets.append(arguments[index + 1])
            index += 2
            continue
        if lowered in _NETWORK_VALUE_OPTIONS:
            index += 2
            continue
        if lowered in _NETWORK_FLAG_OPTIONS:
            index += 1
            continue
        if value.startswith(("-", "/")):
            # Unknown option semantics are not proof. Conservatively skip one
            # following value rather than treating it as a network target.
            index += 2 if index + 1 < len(arguments) else 1
            continue
        targets.append(value)
        index += 1
    return targets


def _package_sources(tokens: list[str]) -> tuple[list[str], list[str]]:
    endpoint_values: list[str] = []
    package_values: list[str] = []
    index = 0
    while index < len(tokens):
        value = _clean_token(tokens[index])
        lowered = value.casefold()
        key, separator, _inline_value = lowered.partition("=")
        if separator and key in _PACKAGE_ENDPOINT_OPTIONS:
            endpoint_values.append(value.partition("=")[2])
            index += 1
            continue
        if separator and key in _PACKAGE_VALUE_OPTIONS:
            index += 1
            continue
        if lowered in _PACKAGE_ENDPOINT_OPTIONS:
            if index + 1 < len(tokens):
                endpoint_values.append(_clean_token(tokens[index + 1]))
            index += 2
            continue
        if lowered in _PACKAGE_VALUE_OPTIONS:
            index += 2
            continue
        if value.startswith(("-", "/")):
            index += 1
            continue
        package_values.append(value)
        index += 1
    return endpoint_values, package_values


def _git_directory(cwd: str) -> Path | None:
    marker = Path(cwd) / ".git"
    if marker.is_dir():
        return marker
    if marker.is_file():
        try:
            declaration = marker.read_text(encoding="utf-8-sig").strip()
        except (OSError, UnicodeError):
            return None
        if declaration.casefold().startswith("gitdir:"):
            target = declaration.split(":", 1)[1].strip()
            candidate = Path(target)
            return candidate if candidate.is_absolute() else (marker.parent / candidate).resolve()
    return None


def _git_config(cwd: str) -> configparser.ConfigParser | None:
    git_dir = _git_directory(cwd)
    if git_dir is None:
        return None
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    try:
        with (git_dir / "config").open(encoding="utf-8-sig") as stream:
            parser.read_file(stream)
    except (OSError, configparser.Error, UnicodeError):
        return None
    return parser


def _git_current_branch(cwd: str) -> str | None:
    git_dir = _git_directory(cwd)
    if git_dir is None:
        return None
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8-sig").strip()
    except (OSError, UnicodeError):
        return None
    prefix = "ref: refs/heads/"
    return head[len(prefix) :] if head.startswith(prefix) else None


def _git_remote_names(config: configparser.ConfigParser) -> list[str]:
    names: list[str] = []
    for section in config.sections():
        match = re.fullmatch(r'remote\s+"(.+)"', section, re.IGNORECASE)
        if match:
            names.append(match.group(1))
    return names


def _git_remote_url(cwd: str, remote: str | None, operation: str) -> str | None:
    config = _git_config(cwd)
    if config is None:
        return None

    selected = remote
    branch = _git_current_branch(cwd)
    if selected is None and branch:
        branch_section = f'branch "{branch}"'
        if operation == "push":
            selected = config.get(branch_section, "pushRemote", fallback=None)
            selected = selected or config.get("remote", "pushDefault", fallback=None)
        selected = selected or config.get(branch_section, "remote", fallback=None)

    names = _git_remote_names(config)
    if selected is None and len(names) == 1:
        selected = names[0]
    if not selected or selected == ".":
        return None

    section = f'remote "{selected}"'
    return config.get(section, "url", fallback=None)


def _git_all_remote_urls(cwd: str) -> tuple[str, ...]:
    config = _git_config(cwd)
    if config is None:
        return ()
    urls: list[str] = []
    for name in _git_remote_names(config):
        value = config.get(f'remote "{name}"', "url", fallback=None)
        if value:
            urls.append(value)
    return tuple(urls)


def _network_intent(tokens: list[str], *, cwd: str) -> bool:
    if not tokens:
        return False

    program = _program_name(tokens[0])
    lowered_arguments = [_clean_token(token).casefold() for token in tokens[1:]]

    if program in _NETWORK_PROGRAMS:
        targets = _network_targets(tokens)
        if program == "scp":
            return any(_explicit_remote_reference(value, cwd=cwd) for value in targets)
        return any(_external_target(value, cwd=cwd) for value in targets)

    if program == "uv" and lowered_arguments[:2] == ["pip", "install"]:
        if "--offline" in lowered_arguments:
            return False
        endpoints, packages = _package_sources(tokens[3:])
        return any(
            _explicit_remote_reference(value, cwd=cwd) for value in endpoints
        ) or any(_explicit_remote_reference(value, cwd=cwd) for value in packages)

    if program in _PACKAGE_COMMANDS:
        operation, tail = _operation_and_tail(tokens)
        if operation not in _PACKAGE_COMMANDS[program] or "--offline" in lowered_arguments:
            return False
        endpoints, packages = _package_sources(tail)
        return any(
            _explicit_remote_reference(value, cwd=cwd) for value in endpoints
        ) or any(_explicit_remote_reference(value, cwd=cwd) for value in packages)

    if program == "git":
        operation, tail = _operation_and_tail(tokens)
        if operation not in _REMOTE_GIT_COMMANDS:
            return False
        values = [value for value in tail if value and not value.startswith("-")]
        if operation in {"clone", "ls-remote"}:
            if not values:
                return False
            candidate = values[0]
            resolved = _git_remote_url(cwd, candidate, operation)
            target = resolved or candidate
            return _explicit_remote_reference(target, cwd=cwd)
        if "--all" in lowered_arguments:
            return any(
                _explicit_remote_reference(url, cwd=cwd)
                for url in _git_all_remote_urls(cwd)
            )
        candidate = values[0] if values else None
        resolved = _git_remote_url(cwd, candidate, operation)
        if resolved:
            return _explicit_remote_reference(resolved, cwd=cwd)
        return bool(candidate) and _explicit_remote_reference(candidate, cwd=cwd)

    return False


def _resolve_path(value: str, *, cwd: str) -> str | None:
    clean = _clean_token(value)
    if not clean or clean in {"-", "nul", "NUL"} or clean.startswith("&"):
        return None
    if any(marker in clean for marker in ("$env:", "%", "${", "$(")):
        return None
    try:
        return normalize_windows_path(clean, base=cwd)
    except PathValidationError:
        return None


def _non_option_values(tokens: Iterable[str]) -> list[str]:
    values: list[str] = []
    skip_next = False
    for token in tokens:
        clean = _clean_token(token)
        lower = clean.casefold()
        if skip_next:
            values.append(clean)
            skip_next = False
            continue
        if lower in {"-path", "-literalpath", "-destination", "-filepath"}:
            skip_next = True
            continue
        if clean.startswith(("-", "/")):
            continue
        values.append(clean)
    return values


def _redirection_paths(command: str, *, cwd: str) -> list[str]:
    paths: list[str] = []
    for match in _REDIRECT_RE.finditer(command):
        candidate = next(value for value in match.groups() if value is not None)
        resolved = _resolve_path(candidate, cwd=cwd)
        if resolved:
            paths.append(resolved)
    return paths


def _git_operation(tokens: list[str]) -> str:
    operation, _tail = _operation_and_tail(tokens)
    return operation


def _git_option_key(value: str) -> str:
    return value.split("=", 1)[0]


def _git_has_option(arguments: list[str], options: set[str]) -> bool:
    lowered_long = {value.casefold() for value in options if value.startswith("--")}
    for argument in arguments:
        key = _git_option_key(argument)
        if key in options:
            return True
        if key.startswith("--") and key.casefold() in lowered_long:
            return True
    return False


def _git_has_positional(arguments: list[str]) -> bool:
    return any(argument and not argument.startswith("-") for argument in arguments)


def _git_local_write_intent(tokens: list[str]) -> bool:
    operation, tail = _operation_and_tail(tokens)
    arguments = [_clean_token(value) for value in tail]
    lowered = [value.casefold() for value in arguments]

    if operation in _LOCAL_GIT_WRITE_COMMANDS:
        return True

    if operation in {"am", "rebase"}:
        return "--show-current-patch" not in lowered

    if operation == "branch":
        if _git_has_option(arguments, _GIT_BRANCH_MUTATION_OPTIONS):
            return True
        read_only = (
            _git_has_option(arguments, _GIT_BRANCH_READ_VALUE_OPTIONS)
            or any(
                value in {"-a", "-r", "-l", "--all", "--remotes", "--list", "--show-current"}
                or value.startswith("-v")
                for value in arguments
            )
        )
        return False if read_only else _git_has_positional(arguments)

    if operation == "tag":
        if _git_has_option(arguments, _GIT_TAG_MUTATION_OPTIONS):
            return True
        read_only = (
            _git_has_option(arguments, _GIT_TAG_READ_VALUE_OPTIONS)
            or any(
                value in {"-l", "-v", "--list", "--verify"}
                or value.startswith("-n")
                for value in arguments
            )
        )
        return False if read_only else _git_has_positional(arguments)

    if operation == "stash":
        action = next((value for value in lowered if value and not value.startswith("-")), "")
        return action not in {"list", "show"}

    return False


def _combined_short_flag(tokens: list[str], flag: str) -> bool:
    for token in tokens[1:]:
        clean = _clean_token(token).casefold()
        if clean.startswith("-") and not clean.startswith("--") and flag in clean[1:]:
            return True
    return False


def _git_clean_is_unresolved_delete(tokens: list[str]) -> bool:
    if _git_operation(tokens) != "clean":
        return False
    lowered = {_clean_token(token).casefold() for token in tokens[1:]}
    dry_run = "--dry-run" in lowered or _combined_short_flag(tokens, "n")
    force = "--force" in lowered or _combined_short_flag(tokens, "f")
    return force and not dry_run


def _delete_paths(tokens: list[str], command: str, *, cwd: str) -> list[str]:
    lower_command = command.casefold()
    if any(flag in lower_command for flag in ("--help", " -h", " /?", "-whatif")):
        return []
    if not tokens:
        return []

    program = _program_name(tokens[0])
    if program == "git" or program not in _DELETE_PROGRAMS:
        return []

    values = _non_option_values(tokens[1:])
    resolved = [_resolve_path(value, cwd=cwd) for value in values]
    return [value for value in resolved if value]


def _explicit_write_paths(tokens: list[str], command: str, *, cwd: str) -> list[str]:
    paths = _redirection_paths(command, cwd=cwd)
    if not tokens:
        return paths

    program = _program_name(tokens[0])

    if program == "git":
        if _git_local_write_intent(tokens):
            paths.append(cwd)
        return list(dict.fromkeys(paths))

    values = _non_option_values(tokens[1:])

    if program in _COPY_PROGRAMS and values:
        resolved = _resolve_path(values[-1], cwd=cwd)
        if resolved:
            paths.append(resolved)
    elif program in _CREATE_PROGRAMS:
        for value in values:
            resolved = _resolve_path(value, cwd=cwd)
            if resolved:
                paths.append(resolved)
    elif program in _WRITE_CMDLETS:
        named_path_found = False
        for index, token in enumerate(tokens[1:], start=1):
            lower = _clean_token(token).casefold()
            if lower in {"-path", "-literalpath", "-filepath"} and index + 1 < len(tokens):
                resolved = _resolve_path(tokens[index + 1], cwd=cwd)
                if resolved:
                    paths.append(resolved)
                    named_path_found = True
        if not named_path_found and values:
            resolved = _resolve_path(values[0], cwd=cwd)
            if resolved:
                paths.append(resolved)

    return list(dict.fromkeys(paths))


def _entry_paths(tokens: list[str], *, cwd: str) -> list[str]:
    if not tokens or _program_name(tokens[0]) not in _MOVE_PROGRAMS:
        return []
    values = _non_option_values(tokens[1:])
    if not values:
        return []
    paths: list[str] = []
    for value in (values[0], values[-1]):
        resolved = _resolve_path(value, cwd=cwd)
        if resolved:
            paths.append(resolved)
    return list(dict.fromkeys(paths))


def _merge_effects(effects: Iterable[InvocationEffects]) -> InvocationEffects:
    write_paths: list[str] = []
    entry_paths: list[str] = []
    delete_paths: list[str] = []
    unresolved_delete = False
    external_network = False
    for effect in effects:
        write_paths.extend(effect.write_paths)
        entry_paths.extend(effect.entry_paths)
        delete_paths.extend(effect.delete_paths)
        unresolved_delete = unresolved_delete or effect.unresolved_delete
        external_network = external_network or effect.external_network
    return InvocationEffects(
        write_paths=tuple(dict.fromkeys(write_paths)),
        entry_paths=tuple(dict.fromkeys(entry_paths)),
        delete_paths=tuple(dict.fromkeys(delete_paths)),
        unresolved_delete=unresolved_delete,
        external_network=external_network,
    )


def _resolve_command_recursive(
    command: str,
    *,
    cwd: str,
    depth: int,
) -> InvocationEffects:
    if depth > _MAX_NESTED_COMMAND_DEPTH:
        return InvocationEffects()

    segments = _split_shell_segments(command)
    if len(segments) > 1:
        return _merge_effects(
            _resolve_command_recursive(segment, cwd=cwd, depth=depth + 1)
            for segment in segments
        )

    segment = segments[0] if segments else command.strip()
    tokens = _tokens(segment)
    direct = InvocationEffects(
        write_paths=tuple(_explicit_write_paths(tokens, segment, cwd=cwd)),
        entry_paths=tuple(_entry_paths(tokens, cwd=cwd)),
        delete_paths=tuple(_delete_paths(tokens, segment, cwd=cwd)),
        unresolved_delete=(
            bool(tokens)
            and _program_name(tokens[0]) == "git"
            and _git_clean_is_unresolved_delete(tokens)
        ),
        external_network=_network_intent(tokens, cwd=cwd),
    )
    payload = _wrapped_command_payload(tokens)
    if not payload or payload.strip() == segment.strip():
        return direct
    nested = _resolve_command_recursive(payload, cwd=cwd, depth=depth + 1)
    return _merge_effects((direct, nested))


def resolve_command_effects(
    command: str,
    *,
    cwd: str,
    project_boundary: str,
) -> InvocationEffects:
    """Resolve only explicit HR-001/HR-002/HR-003 evidence from a command."""

    effective_cwd = normalize_windows_path(cwd or project_boundary, base=project_boundary)
    return _resolve_command_recursive(command, cwd=effective_cwd, depth=0)
