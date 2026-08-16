from __future__ import annotations

from dataclasses import dataclass
import shlex

from .paths import PathValidationError, normalize_windows_path


_CMD_SHELLS = {"cmd", "cmd.exe"}
_POWERSHELL_SHELLS = {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}
_DIRECTORY_COMMANDS = {"cd", "chdir", "set-location", "sl"}


@dataclass(frozen=True, slots=True)
class ShellState:
    cwd: str
    shell: str = "generic"
    directory_stack: tuple[str, ...] = ()
    terminated: bool = False
    cmd_delayed_expansion: bool = False


@dataclass(frozen=True, slots=True)
class ShellSegment:
    text: str
    cwd: str
    shell: str


def normalize_shell(value: str | None) -> str:
    raw = (value or "").strip().strip("\"'").replace("/", "\\")
    name = raw.rsplit("\\", 1)[-1].casefold()
    if name in _CMD_SHELLS:
        return "cmd"
    if name in _POWERSHELL_SHELLS:
        return "powershell"
    return "generic"


def split_shell_segments(command: str, *, shell: str = "generic") -> tuple[str, ...]:
    dialect = normalize_shell(shell)
    segments: list[str] = []
    current: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(command):
        character = command[index]
        escape = "^" if dialect == "cmd" else "`" if dialect == "powershell" else "\\"
        if quote is not None:
            current.append(character)
            if character == quote:
                quote = None
            elif character == escape and index + 1 < len(command):
                index += 1
                current.append(command[index])
            index += 1
            continue
        if character in {'"', "'"}:
            quote = character
            current.append(character)
            index += 1
            continue
        if character == escape and index + 1 < len(command):
            current.append(character)
            index += 1
            current.append(command[index])
            index += 1
            continue

        separator_length = 0
        if command.startswith("&&", index) or command.startswith("||", index):
            separator_length = 2
        elif dialect == "cmd" and character == "&":
            separator_length = 1
        elif character in {"|", "\n", "\r"}:
            separator_length = 1
        elif dialect != "cmd" and character == ";":
            separator_length = 1
        if separator_length:
            value = _normalize_segment("".join(current), dialect)
            if value:
                segments.append(value)
            current = []
            index += separator_length
            continue
        current.append(character)
        index += 1

    value = _normalize_segment("".join(current), dialect)
    if value:
        segments.append(value)
    return tuple(segments)


def resolve_shell_segments(command: str, state: ShellState) -> tuple[tuple[ShellSegment, ...], ShellState]:
    current = state
    resolved: list[ShellSegment] = []
    for text in split_shell_segments(command, shell=current.shell):
        next_state = _directory_transition(text, current)
        if next_state is not None:
            current = next_state
            continue
        if _is_exit(text):
            current = ShellState(
                cwd=current.cwd,
                shell=current.shell,
                directory_stack=current.directory_stack,
                terminated=True,
                cmd_delayed_expansion=current.cmd_delayed_expansion,
            )
            continue
        resolved.append(ShellSegment(text=text, cwd=current.cwd, shell=current.shell))
    return tuple(resolved), current


def shell_from_command(command: str, explicit_shell: str | None = None) -> str:
    selected = normalize_shell(explicit_shell)
    if selected != "generic":
        return selected
    tokens = _tokens(command)
    return normalize_shell(tokens[0]) if tokens else "generic"


def _normalize_segment(value: str, shell: str) -> str:
    text = value.strip()
    if shell == "cmd":
        while len(text) >= 2 and text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()
    if shell == "powershell":
        if text.startswith("&"):
            text = text[1:].strip()
        if len(text) >= 2 and text.startswith("{") and text.endswith("}"):
            text = text[1:-1].strip()
    return text


def _directory_transition(text: str, state: ShellState) -> ShellState | None:
    tokens = _tokens(text)
    if not tokens:
        return None
    program = _program(tokens[0])
    values = [_clean(value) for value in tokens[1:]]

    if program in _DIRECTORY_COMMANDS:
        candidates = [
            value
            for value in values
            if value
            and value.casefold() not in {"/d", "-path", "-literalpath"}
            and not value.startswith("-")
        ]
        if not candidates:
            return state
        target = _resolve(candidates[-1], state.cwd)
        return ShellState(
            cwd=target or state.cwd,
            shell=state.shell,
            directory_stack=state.directory_stack,
            cmd_delayed_expansion=state.cmd_delayed_expansion,
        )
    if program == "pushd":
        candidates = [value for value in values if value and not value.startswith("-")]
        if not candidates:
            return state
        target = _resolve(candidates[-1], state.cwd)
        if target is None:
            return state
        stack = (*state.directory_stack[-31:], state.cwd)
        return ShellState(
            cwd=target,
            shell=state.shell,
            directory_stack=stack,
            cmd_delayed_expansion=state.cmd_delayed_expansion,
        )
    if program == "popd":
        if not state.directory_stack:
            return state
        return ShellState(
            cwd=state.directory_stack[-1],
            shell=state.shell,
            directory_stack=state.directory_stack[:-1],
            cmd_delayed_expansion=state.cmd_delayed_expansion,
        )
    return None


def _is_exit(text: str) -> bool:
    tokens = _tokens(text)
    return bool(tokens) and _program(tokens[0]) in {"exit", "logout"}


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=False)
    except ValueError:
        return command.split()


def _clean(value: str) -> str:
    return value.strip().strip("\"'").rstrip(",;")


def _program(value: str) -> str:
    clean = _clean(value).replace("/", "\\").rsplit("\\", 1)[-1].casefold()
    if clean.endswith((".exe", ".cmd", ".bat")):
        clean = clean.rsplit(".", 1)[0]
    return clean


def _resolve(value: str, cwd: str) -> str | None:
    if any(marker in value for marker in ("$env:", "%", "${", "$(")):
        return None
    try:
        return normalize_windows_path(value, base=cwd)
    except PathValidationError:
        return None


def output_redirection_targets(command: str, *, shell: str = "generic") -> tuple[str, ...]:
    """Return syntactic output-redirection targets while preserving shell quoting."""

    dialect = normalize_shell(shell)
    escape = "^" if dialect == "cmd" else "`" if dialect == "powershell" else None
    targets: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(command):
        character = command[index]
        if quote is not None:
            if character == escape and index + 1 < len(command):
                index += 2
                continue
            if character == quote:
                quote = None
            index += 1
            continue
        if character in {'"', "'"}:
            quote = character
            index += 1
            continue
        if character == escape and index + 1 < len(command):
            index += 2
            continue
        if character != ">" or (index > 0 and command[index - 1] == "<"):
            index += 1
            continue

        index += 2 if command.startswith(">>", index) else 1
        while index < len(command) and command[index].isspace():
            index += 1
        if index >= len(command):
            break

        target: list[str] = []
        target_quote: str | None = None
        quoted_fragments = 0
        saw_unquoted_content = False
        while index < len(command):
            character = command[index]
            if target_quote is not None:
                target.append(character)
                if (
                    dialect == "powershell"
                    and target_quote == "'"
                    and character == "'"
                    and index + 1 < len(command)
                    and command[index + 1] == "'"
                ):
                    target.append(command[index + 1])
                    index += 2
                    continue
                if (
                    character == escape
                    and target_quote != "'"
                    and index + 1 < len(command)
                ):
                    target.append(command[index + 1])
                    index += 2
                    continue
                if character == target_quote:
                    target_quote = None
                index += 1
                continue
            if character.isspace() or character in ";|&":
                break
            if character in {'"', "'"}:
                target_quote = character
                quoted_fragments += 1
                target.append(character)
                index += 1
                continue
            if character == escape and index + 1 < len(command):
                target.append(character)
                target.append(command[index + 1])
                saw_unquoted_content = True
                index += 2
                continue
            saw_unquoted_content = True
            target.append(character)
            index += 1
        raw_value = "".join(target).strip()
        value = raw_value
        if (
            quoted_fragments == 1
            and not saw_unquoted_content
            and len(raw_value) >= 2
            and raw_value[0] == raw_value[-1]
            and raw_value[0] in {'"', "'"}
            and not (dialect == "powershell" and raw_value[0] == "'")
        ):
            value = raw_value[1:-1]
        if value:
            targets.append(value)
    return tuple(targets)


__all__ = [
    "ShellSegment",
    "ShellState",
    "normalize_shell",
    "output_redirection_targets",
    "resolve_shell_segments",
    "shell_from_command",
    "split_shell_segments",
]
