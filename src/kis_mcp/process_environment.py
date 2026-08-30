from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
import re
import shlex
from typing import Any

from .projects.registry import ProjectRegistry
from .shell_parser import (
    ShellState,
    normalize_shell,
    resolve_shell_segments,
    split_shell_segments,
)


_PROCESS_LAUNCH_TOOLS = frozenset({"start_process", "execute_command"})
_POWERSHELL_PYTHONPATH_ASSIGNMENT = re.compile(
    r"(?i)\$env\s*:\s*PYTHONPATH\s*(?:\+?=)"
)
_CMD_PYTHONPATH_ASSIGNMENT = re.compile(
    r'(?i)(?:^|[&|;\r\n])\s*setx?\s+(?:"?PYTHONPATH(?:=|\s))'
)
_GENERIC_PYTHONPATH_ASSIGNMENT = re.compile(
    r"(?i)(?:^|\s)(?:env\s+)?PYTHONPATH\s*="
)
_POWERSHELL_ENVIRONMENT_API_MUTATION = re.compile(
    r"(?i)\[\s*(?:System\.)?Environment\s*\]\s*::\s*SetEnvironmentVariable\s*"
    r"\(\s*['\"]PYTHONPATH['\"]"
)
_POWERSHELL_MUTATION_TARGETS: dict[
    str,
    tuple[dict[str, int], frozenset[int]],
] = {
    "set-item": (
        {"-path": 0, "-literalpath": 0, "-value": 1},
        frozenset({0}),
    ),
    "new-item": ({"-path": 0}, frozenset({0})),
    "clear-item": ({"-path": 0, "-literalpath": 0}, frozenset({0})),
    "remove-item": ({"-path": 0, "-literalpath": 0}, frozenset({0})),
    "set-content": (
        {"-path": 0, "-literalpath": 0, "-value": 1},
        frozenset({0}),
    ),
    "add-content": (
        {"-path": 0, "-literalpath": 0, "-value": 1},
        frozenset({0}),
    ),
    "clear-content": ({"-path": 0, "-literalpath": 0}, frozenset({0})),
    "move-item": (
        {"-path": 0, "-literalpath": 0, "-destination": 1},
        frozenset({0, 1}),
    ),
    "rename-item": (
        {"-path": 0, "-literalpath": 0, "-newname": 1},
        frozenset({0}),
    ),
    "copy-item": (
        {"-path": 0, "-literalpath": 0, "-destination": 1},
        frozenset({1}),
    ),
}
_POWERSHELL_VALUE_PARAMETERS = frozenset(
    {
        "-value",
        "-filter",
        "-include",
        "-exclude",
        "-credential",
        "-itemtype",
        "-name",
        "-newname",
        "-encoding",
        "-stream",
        "-delimiter",
        "-erroraction",
        "-warningaction",
        "-informationaction",
        "-errorvariable",
        "-warningvariable",
        "-informationvariable",
        "-outvariable",
        "-outbuffer",
        "-pipelinevariable",
    }
)


class ProcessSourceIsolationError(ValueError):
    def __init__(self, code: str, reason: str) -> None:
        self.code = code
        self.reason = reason
        super().__init__(f"{code}: {reason}")


class RepositoryProcessEnvironmentNormalizer:
    """Bind launched processes to the selected registered checkout's Python source."""

    def __init__(
        self,
        *,
        project_boundary: str | Path,
        projects: ProjectRegistry,
    ) -> None:
        self.project_boundary = Path(project_boundary).resolve(strict=False)
        self.projects = projects

    def normalize(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        normalized = dict(arguments or {})
        if tool_name.casefold() not in _PROCESS_LAUNCH_TOOLS:
            return normalized

        command = normalized.get("command")
        if not isinstance(command, str) or not command.strip():
            return normalized

        shell_value = normalized.get("shell")
        shell = self._effective_shell(shell_value)
        initial_cwd = self._working_directory(normalized)
        segments, _ = resolve_shell_segments(
            command,
            ShellState(cwd=initial_cwd, shell=shell),
        )
        source_roots = self._source_roots(segment.cwd for segment in segments)
        if not source_roots:
            return normalized
        if len(source_roots) > 1:
            rendered = ", ".join(source_roots)
            raise ProcessSourceIsolationError(
                "PROCESS_SOURCE_AMBIGUOUS",
                "One process command resolves to multiple registered Python source roots: "
                f"{rendered}.",
            )

        source_root = source_roots[0]
        if self._rewrites_pythonpath(command, shell=shell):
            raise ProcessSourceIsolationError(
                "PROCESS_SOURCE_OVERRIDE_UNSAFE",
                "The command explicitly rewrites PYTHONPATH after selecting a registered "
                "repository/worktree, so KIS cannot guarantee source identity.",
            )

        normalized["command"] = self._bind_source(
            command,
            source_root=source_root,
            shell=shell,
        )
        if shell_value is None or (
            isinstance(shell_value, str) and not shell_value.strip()
        ):
            normalized["shell"] = "powershell.exe"
        return normalized

    def _working_directory(self, arguments: Mapping[str, Any]) -> str:
        for key in ("cwd", "working_directory", "workingDirectory"):
            value = arguments.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return str(self.project_boundary)

    @staticmethod
    def _effective_shell(value: Any) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return "powershell"
        if not isinstance(value, str):
            return "generic"
        return normalize_shell(value)

    def _source_roots(self, working_directories: Iterable[str]) -> tuple[str, ...]:
        roots: dict[str, str] = {}
        for cwd in working_directories:
            source = self._source_root(cwd)
            if source is None:
                continue
            roots.setdefault(source.casefold(), source)
        return tuple(roots.values())

    def _source_root(self, cwd: str) -> str | None:
        try:
            project = self.projects.project_for_root(cwd)
        except (KeyError, ValueError):
            return None

        current = Path(cwd).resolve(strict=False)
        if current.is_file():
            current = current.parent
        project_root = Path(project.local_root).resolve(strict=False)
        while True:
            try:
                current.relative_to(project_root)
            except ValueError:
                return None
            if (current / ".git").exists():
                source = current / "src"
                return str(source) if source.is_dir() else None
            if current == project_root:
                return None
            parent = current.parent
            if parent == current:
                return None
            current = parent

    @staticmethod
    def _rewrites_pythonpath(command: str, *, shell: str) -> bool:
        return bool(
            _POWERSHELL_PYTHONPATH_ASSIGNMENT.search(command)
            or _CMD_PYTHONPATH_ASSIGNMENT.search(command)
            or _GENERIC_PYTHONPATH_ASSIGNMENT.search(command)
            or _POWERSHELL_ENVIRONMENT_API_MUTATION.search(command)
            or (
                shell == "powershell"
                and _powershell_provider_mutates_pythonpath(command)
            )
        )

    @staticmethod
    def _bind_source(command: str, *, source_root: str, shell: str) -> str:
        if shell == "powershell":
            source = _ps_quote(source_root)
            return (
                f"$kisProcessSource = {source}; "
                "if (-not (Test-Path -LiteralPath $kisProcessSource -PathType Container)) { "
                "throw 'PROCESS_SOURCE_UNAVAILABLE: selected Python source root disappeared before execution.'; "
                "}; "
                "$env:PYTHONPATH = if ($env:PYTHONPATH) { "
                "$kisProcessSource + [IO.Path]::PathSeparator + $env:PYTHONPATH "
                "} else { $kisProcessSource }; "
                f"{command}"
            )
        if shell == "cmd":
            if any(character in source_root for character in ('"', "%", "!", "\r", "\n")):
                raise ProcessSourceIsolationError(
                    "PROCESS_SOURCE_PATH_UNSAFE",
                    "The selected Python source root cannot be represented safely for cmd.exe.",
                )
            return (
                f'((pushd "{source_root}" >nul 2>&1 && popd) || '
                "(echo PROCESS_SOURCE_UNAVAILABLE: selected Python source root disappeared before execution. 1>&2 & exit /b 1)) && "
                f'set "PYTHONPATH={source_root};%PYTHONPATH%" && {command}'
            )
        raise ProcessSourceIsolationError(
            "PROCESS_SOURCE_SHELL_UNSUPPORTED",
            "KIS cannot safely bind the selected repository/worktree Python source "
            "for this shell.",
        )


def _powershell_provider_mutates_pythonpath(command: str) -> bool:
    for segment in split_shell_segments(command, shell="powershell"):
        try:
            tokens = shlex.split(segment, posix=False)
        except ValueError:
            tokens = segment.split()
        if not tokens:
            continue

        program = _ps_token(tokens[0]).casefold()
        target_spec = _POWERSHELL_MUTATION_TARGETS.get(program)
        if target_spec is None:
            continue
        parameter_positions, target_positions = target_spec

        bound_positions: set[int] = set()
        index = 1
        while index < len(tokens):
            token = _ps_token(tokens[index])
            parameter = token.casefold() if token.startswith("-") else ""
            parameter_position = parameter_positions.get(parameter)
            if parameter_position is not None:
                if (
                    parameter_position in target_positions
                    and index + 1 < len(tokens)
                    and _is_pythonpath_provider(tokens[index + 1])
                ):
                    return True
                bound_positions.add(parameter_position)
                index += 2
                continue
            if parameter:
                if parameter in _POWERSHELL_VALUE_PARAMETERS:
                    index += 2
                else:
                    index += 1
                continue

            positional_index = 0
            while positional_index in bound_positions:
                positional_index += 1
            if positional_index in target_positions and _is_pythonpath_provider(token):
                return True
            bound_positions.add(positional_index)
            index += 1
    return False


def _is_pythonpath_provider(value: str) -> bool:
    token = _ps_token(value).strip()
    provider, separator, provider_path = token.partition(":")
    if separator != ":" or provider.casefold() != "env":
        return False

    # PowerShell's Env: provider consumes one leading slash, or up to two
    # leading backslashes. A slash followed by one backslash is also the
    # provider root. Additional/mixed separators become part of the variable
    # name (for example Env://PYTHONPATH addresses /PYTHONPATH).
    if provider_path.startswith("/"):
        provider_path = provider_path[1:]
        if provider_path.startswith("\\"):
            provider_path = provider_path[1:]
    elif provider_path.startswith("\\"):
        provider_path = provider_path[1:]
        if provider_path.startswith("\\"):
            provider_path = provider_path[1:]

    return provider_path.casefold() == "pythonpath"


def _ps_token(value: str) -> str:
    return value.strip().strip("\"'")


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


__all__ = [
    "ProcessSourceIsolationError",
    "RepositoryProcessEnvironmentNormalizer",
]
