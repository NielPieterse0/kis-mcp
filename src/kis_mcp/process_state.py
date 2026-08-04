from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import re
from threading import RLock
from typing import Any

from .command_intent import (
    resolve_command_effects_with_state,
    resolve_persistent_shell_startup_state,
)
from .models import InvocationEffects
from .shell_parser import ShellState, shell_from_command


_PID_RE = re.compile(r"(?i)\bpid(?:\s*(?:is|:|=))?\s*(\d+)\b")
_TERMINATION_TOOLS = frozenset({"kill_process", "force_terminate"})


class ProcessStateRegistry:
    """Maintain bounded in-memory shell state for provider process identifiers."""

    def __init__(self) -> None:
        self._states: dict[int, ShellState] = {}
        self._lock = RLock()

    def resolve_interaction(
        self,
        arguments: Mapping[str, Any],
        *,
        project_boundary: str,
    ) -> InvocationEffects | None:
        pid = _pid_argument(arguments)
        command = _command_text(arguments)
        if pid is None or not command:
            return None
        with self._lock:
            state = self._states.get(pid)
        if state is None:
            return None
        effects, _next_state = resolve_command_effects_with_state(
            command,
            state=state,
            project_boundary=project_boundary,
        )
        return effects

    def observe_success(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
        result: Any,
        *,
        project_boundary: str,
    ) -> None:
        normalized = tool_name.casefold()
        if normalized == "start_process":
            pid = _result_pid(result)
            if pid is None:
                return
            cwd = _working_directory(arguments) or project_boundary
            command = _command_text(arguments)
            state = ShellState(
                cwd=cwd,
                shell=shell_from_command(command, _shell_argument(arguments)),
            )
            state = resolve_persistent_shell_startup_state(
                command,
                state=state,
                project_boundary=project_boundary,
            )
            with self._lock:
                if state.terminated:
                    self._states.pop(pid, None)
                else:
                    self._states[pid] = state
            return

        if normalized == "interact_with_process":
            pid = _pid_argument(arguments)
            command = _command_text(arguments)
            if pid is None or not command:
                return
            with self._lock:
                state = self._states.get(pid)
            if state is None:
                return
            _effects, next_state = resolve_command_effects_with_state(
                command,
                state=state,
                project_boundary=project_boundary,
            )
            with self._lock:
                if next_state.terminated:
                    self._states.pop(pid, None)
                else:
                    self._states[pid] = next_state
            return

        if normalized in _TERMINATION_TOOLS:
            pid = _pid_argument(arguments)
            if pid is not None:
                with self._lock:
                    self._states.pop(pid, None)

    def snapshot(self) -> dict[int, ShellState]:
        with self._lock:
            return dict(self._states)


def _pid_argument(arguments: Mapping[str, Any]) -> int | None:
    value = arguments.get("pid")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _working_directory(arguments: Mapping[str, Any]) -> str | None:
    for key in ("cwd", "working_directory", "workingDirectory"):
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _shell_argument(arguments: Mapping[str, Any]) -> str | None:
    value = arguments.get("shell")
    return value if isinstance(value, str) and value.strip() else None


def _command_text(arguments: Mapping[str, Any]) -> str:
    for key in ("input", "command"):
        value = arguments.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, Sequence) and not isinstance(
            value,
            (str, bytes, bytearray),
        ):
            return " ".join(str(item) for item in value)
    return ""


def _result_pid(result: Any) -> int | None:
    for text in _result_texts(result):
        match = _PID_RE.search(text)
        if match:
            return int(match.group(1))
    return None


def _result_texts(value: Any) -> tuple[str, ...]:
    texts: list[str] = []
    seen: set[int] = set()

    def visit(item: Any, depth: int) -> None:
        if depth > 5 or item is None:
            return
        identity = id(item)
        if identity in seen:
            return
        seen.add(identity)
        if isinstance(item, str):
            texts.append(item)
            return
        if isinstance(item, bytes):
            texts.append(item.decode("utf-8", errors="replace"))
            return
        if isinstance(item, Mapping):
            for nested in item.values():
                visit(nested, depth + 1)
            return
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            for nested in item:
                visit(nested, depth + 1)
            return
        for attribute in ("content", "structured_content", "text", "data", "result"):
            if hasattr(item, attribute):
                visit(getattr(item, attribute), depth + 1)
        if depth == 0:
            try:
                texts.append(json.dumps(item, default=str))
            except (TypeError, ValueError):
                texts.append(str(item))

    visit(value, 0)
    return tuple(texts)


__all__ = ["ProcessStateRegistry"]
