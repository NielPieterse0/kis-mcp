from __future__ import annotations

import re
import shlex
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

from .git_context import git_remote_targets, parse_git_invocation
from .models import InvocationEffects
from .paths import PathValidationError, normalize_windows_path
from .shell_parser import (
    ShellState,
    output_redirection_targets,
    resolve_shell_segments,
    shell_from_command,
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
    "--dry-run",
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


def _clean_token(token: str) -> str:
    return token.strip().strip("\"'").rstrip(",;)")


def _strip_outer_quotes(token: str) -> str:
    value = token.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
        return value[1:-1]
    return value


def _wrapped_command_payload(tokens: list[str]) -> str | None:
    if not tokens:
        return None
    program = _program_name(tokens[0])
    if program not in _SHELL_WRAPPERS:
        return None

    arguments = [_strip_outer_quotes(token) for token in tokens[1:]]
    markers = {"/c", "/k"} if program == "cmd" else {"-command", "-c"}
    for index, argument in enumerate(arguments):
        if argument.casefold() in markers and index + 1 < len(arguments):
            payload = " ".join(arguments[index + 1 :]).strip()
            return payload or None
    return None


def _persistent_shell_payload(tokens: list[str]) -> tuple[str, str] | None:
    if not tokens:
        return None
    program = _program_name(tokens[0])
    arguments = [_strip_outer_quotes(token) for token in tokens[1:]]
    lowered = [argument.casefold() for argument in arguments]

    if program == "cmd":
        markers = {"/k"}
        nested_shell = "cmd"
    elif program in {"powershell", "pwsh"} and "-noexit" in lowered:
        markers = {"-command", "-c"}
        nested_shell = "powershell"
    else:
        return None

    for index, argument in enumerate(lowered):
        if argument in markers:
            payload = " ".join(arguments[index + 1 :]).strip()
            return nested_shell, payload
    return nested_shell, ""


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


def _network_option_role(program: str, option: str) -> str:
    """Classify one known option without folding case-sensitive short forms."""

    folded = option.casefold()
    if program == "curl":
        if option == "-x" or folded in {
            "--url",
            "--proxy",
            "--connect-to",
            "--resolve",
        }:
            return "target"
        if option == "-X" or folded in _NETWORK_VALUE_OPTIONS:
            return "value"
        if folded in _NETWORK_FLAG_OPTIONS:
            return "flag"
        return "unknown"
    if program in {"ssh", "scp", "sftp"}:
        if option == "-J" or folded in {"--jump-host", "--proxyjump"}:
            return "target"
        if folded in _NETWORK_VALUE_OPTIONS:
            return "value"
        if folded in _NETWORK_FLAG_OPTIONS:
            return "flag"
        return "unknown"
    if folded in _NETWORK_TARGET_OPTIONS:
        return "target"
    if folded in _NETWORK_VALUE_OPTIONS:
        return "value"
    if folded in _NETWORK_FLAG_OPTIONS:
        return "flag"
    return "unknown"


def _network_targets(tokens: list[str]) -> list[str]:
    targets: list[str] = []
    if not tokens:
        return targets
    program = _program_name(tokens[0])
    arguments = [_clean_token(token) for token in tokens[1:]]
    index = 0
    while index < len(arguments):
        value = arguments[index]
        option, separator, inline_value = value.partition("=")
        role = _network_option_role(program, option)
        if separator and role == "target":
            targets.append(inline_value)
            index += 1
            continue
        if separator and role in {"value", "flag"}:
            index += 1
            continue
        if role == "target":
            if index + 1 < len(arguments):
                targets.append(arguments[index + 1])
            index += 2
            continue
        if role == "value":
            index += 2
            continue
        if role == "flag":
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
        invocation = parse_git_invocation(tokens, cwd=cwd)
        return any(
            _explicit_remote_reference(target, cwd=invocation.cwd)
            for target in git_remote_targets(invocation)
        )

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


def _positional_operands(
    tokens: Iterable[str], *, value_options: frozenset[str] = frozenset()
) -> list[str]:
    values: list[str] = []
    items = list(tokens)
    index = 0
    while index < len(items):
        clean = _clean_token(items[index])
        key, separator, _inline = clean.partition("=")
        folded = key.casefold()
        if folded in value_options:
            index += 1 if separator else 2
            continue
        if clean.startswith(("-", "/")):
            index += 1
            continue
        values.append(clean)
        index += 1
    return values


def _redirection_paths(command: str, *, cwd: str, shell: str) -> list[str]:
    paths: list[str] = []
    for candidate in output_redirection_targets(command, shell=shell):
        resolved = _resolve_path(candidate, cwd=cwd)
        if resolved:
            paths.append(resolved)
    return paths


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


def _git_local_write_intent(tokens: list[str], *, cwd: str) -> bool:
    invocation = parse_git_invocation(tokens, cwd=cwd)
    operation = invocation.operation
    arguments = [_clean_token(value) for value in invocation.tail]
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
                value
                in {
                    "-a",
                    "-r",
                    "-l",
                    "--all",
                    "--remotes",
                    "--list",
                    "--show-current",
                }
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
        action = next(
            (value for value in lowered if value and not value.startswith("-")),
            "",
        )
        return action not in {"list", "show"}

    return False


def _combined_short_flag(tokens: list[str], flag: str) -> bool:
    for token in tokens[1:]:
        clean = _clean_token(token).casefold()
        if clean.startswith("-") and not clean.startswith("--") and flag in clean[1:]:
            return True
    return False


def _git_clean_is_unresolved_delete(tokens: list[str], *, cwd: str) -> bool:
    invocation = parse_git_invocation(tokens, cwd=cwd)
    if invocation.operation != "clean":
        return False
    operation_tokens = ["git", *invocation.tail]
    lowered = {_clean_token(token).casefold() for token in invocation.tail}
    dry_run = "--dry-run" in lowered or _combined_short_flag(operation_tokens, "n")
    force = "--force" in lowered or _combined_short_flag(operation_tokens, "f")
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


def _explicit_write_paths(
    tokens: list[str], command: str, *, cwd: str, shell: str
) -> list[str]:
    paths = _redirection_paths(command, cwd=cwd, shell=shell)
    if not tokens:
        return paths

    program = _program_name(tokens[0])

    if program == "git":
        if _git_local_write_intent(tokens, cwd=cwd):
            invocation = parse_git_invocation(tokens, cwd=cwd)
            paths.extend(invocation.mutation_paths or (invocation.cwd,))
        return list(dict.fromkeys(paths))

    values = _non_option_values(tokens[1:])
    if program == "new-item":
        values = _positional_operands(
            tokens[1:],
            value_options=frozenset(
                {
                    "-credential",
                    "-itemtype",
                    "-name",
                    "-path",
                    "-value",
                }
            ),
        )
    elif program == "touch":
        values = _positional_operands(
            tokens[1:],
            value_options=frozenset(
                {"-d", "--date", "-r", "--reference", "-t", "--time"}
            ),
        )
    elif program in _WRITE_CMDLETS:
        values = _positional_operands(
            tokens[1:],
            value_options=frozenset(
                {
                    "-credential",
                    "-encoding",
                    "-inputobject",
                    "-literalpath",
                    "-path",
                    "-filepath",
                    "-width",
                }
            ),
        )

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
    state: ShellState,
    depth: int,
) -> tuple[InvocationEffects, ShellState]:
    if depth > _MAX_NESTED_COMMAND_DEPTH:
        return InvocationEffects(), state

    segments, final_state = resolve_shell_segments(command, state)
    effects: list[InvocationEffects] = []
    for segment in segments:
        tokens = _tokens(segment.text)
        direct = InvocationEffects(
            write_paths=tuple(
                _explicit_write_paths(
                    tokens,
                    segment.text,
                    cwd=segment.cwd,
                    shell=segment.shell,
                )
            ),
            entry_paths=tuple(_entry_paths(tokens, cwd=segment.cwd)),
            delete_paths=tuple(
                _delete_paths(tokens, segment.text, cwd=segment.cwd)
            ),
            unresolved_delete=(
                bool(tokens)
                and _program_name(tokens[0]) == "git"
                and _git_clean_is_unresolved_delete(tokens, cwd=segment.cwd)
            ),
            external_network=_network_intent(tokens, cwd=segment.cwd),
        )
        effects.append(direct)

        payload = _wrapped_command_payload(tokens)
        if not payload or payload.strip() == segment.text.strip():
            continue
        wrapper = _program_name(tokens[0]) if tokens else ""
        nested_shell = "cmd" if wrapper == "cmd" else "powershell"
        nested_state = ShellState(cwd=segment.cwd, shell=nested_shell)
        nested, _nested_final = _resolve_command_recursive(
            payload,
            state=nested_state,
            depth=depth + 1,
        )
        effects.append(nested)

    return _merge_effects(effects), final_state


def resolve_persistent_shell_startup_state(
    command: str,
    *,
    state: ShellState,
    project_boundary: str,
) -> ShellState:
    """Return the final state of a statically recognized persistent shell."""

    persistent = _persistent_shell_payload(_tokens(command))
    if persistent is None:
        return state
    nested_shell, payload = persistent
    nested_state = ShellState(cwd=state.cwd, shell=nested_shell)
    if not payload:
        return nested_state
    _effects, final_state = resolve_command_effects_with_state(
        payload,
        state=nested_state,
        project_boundary=project_boundary,
    )
    return final_state


def resolve_command_effects_with_state(
    command: str,
    *,
    state: ShellState,
    project_boundary: str,
) -> tuple[InvocationEffects, ShellState]:
    """Resolve concrete effects and the next supported shell state."""

    effective_cwd = normalize_windows_path(
        state.cwd or project_boundary,
        base=project_boundary,
    )
    normalized_state = ShellState(
        cwd=effective_cwd,
        shell=state.shell,
        directory_stack=state.directory_stack,
        terminated=state.terminated,
    )
    return _resolve_command_recursive(command, state=normalized_state, depth=0)


def resolve_command_effects(
    command: str,
    *,
    cwd: str,
    project_boundary: str,
    shell: str | None = None,
) -> InvocationEffects:
    """Resolve only explicit HR-001/HR-002/HR-003 evidence from a command."""

    effective_cwd = normalize_windows_path(cwd or project_boundary, base=project_boundary)
    initial_state = ShellState(
        cwd=effective_cwd,
        shell=shell_from_command(command, shell),
    )
    effects, _final_state = _resolve_command_recursive(
        command,
        state=initial_state,
        depth=0,
    )
    return effects
