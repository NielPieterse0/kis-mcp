from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

Runner = Callable[[str, dict[str, Any]], Awaitable[Any]]
_EXIT_MARKER = re.compile(
    r"(?m)^__KIS_(?:EXECUTION|VERIFICATION)_EXIT_CODE=(-?\d+)\s*$"
)
_PROCESS_STARTED_PID = re.compile(r"(?m)^Process started with PID ([1-9]\d*)\b")


@dataclass(frozen=True, slots=True)
class ProcessOutcome:
    text: str
    exit_code: int | None
    duration_ms: int


async def run_nested_process(
    runner: Runner,
    *,
    command: str,
    timeout_ms: int,
    shell: str = "powershell.exe",
) -> ProcessOutcome:
    started = time.perf_counter()
    deadline = started + (timeout_ms / 1000)
    result = await runner(
        "start_process",
        {"command": command, "timeout_ms": timeout_ms, "shell": shell},
    )
    text = result_text(result)
    exit_code = exit_marker(text)
    pid = result_pid(result) if exit_code is None else None
    while exit_code is None and pid is not None:
        remaining_ms = int((deadline - time.perf_counter()) * 1000)
        if remaining_ms < 1:
            break
        follow_up = await runner(
            "read_process_output",
            {
                "pid": pid,
                "timeout_ms": remaining_ms,
                "offset": 0,
                "length": 200,
            },
        )
        follow_text = result_text(follow_up)
        text = "\n".join(item for item in (text, follow_text) if item)
        exit_code = exit_marker(text)
    return ProcessOutcome(
        text=text,
        exit_code=exit_code,
        duration_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )


def result_text(result: Any) -> str:
    parts: list[str] = []
    seen: set[int] = set()

    def visit(value: Any, depth: int) -> None:
        if value is None or depth > 4:
            return
        if not isinstance(value, (str, int, float, bool)):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
        if isinstance(value, str):
            parts.append(value)
            return
        if isinstance(value, Mapping):
            for key in ("text", "output", "content", "structured_content", "result"):
                if key in value:
                    visit(value[key], depth + 1)
            return
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                visit(item, depth + 1)
            return
        for attribute in ("text", "content", "structured_content", "result"):
            if hasattr(value, attribute):
                visit(getattr(value, attribute), depth + 1)

    visit(result, 0)
    return "\n".join(part for part in parts if part).strip()


def result_pid(result: Any) -> int | None:
    seen: set[int] = set()

    def visit(value: Any, depth: int) -> int | None:
        if value is None or depth > 4:
            return None
        if not isinstance(value, (str, int, float, bool)):
            identity = id(value)
            if identity in seen:
                return None
            seen.add(identity)
        if isinstance(value, Mapping):
            pid = value.get("pid")
            if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0:
                return pid
            for nested in value.values():
                found = visit(nested, depth + 1)
                if found is not None:
                    return found
            return None
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for nested in value:
                found = visit(nested, depth + 1)
                if found is not None:
                    return found
            return None
        for attribute in ("pid", "content", "structured_content", "result"):
            if not hasattr(value, attribute):
                continue
            candidate = getattr(value, attribute)
            if attribute == "pid" and isinstance(candidate, int) and candidate > 0:
                return candidate
            found = visit(candidate, depth + 1)
            if found is not None:
                return found
        return None

    pid = visit(result, 0)
    if pid is not None:
        return pid
    match = _PROCESS_STARTED_PID.search(result_text(result))
    return int(match.group(1)) if match else None


def exit_marker(text: str) -> int | None:
    matches = _EXIT_MARKER.findall(text)
    return int(matches[-1]) if matches else None


def clean_process_text(text: str, max_chars: int) -> tuple[str, bool]:
    cleaned = _EXIT_MARKER.sub("", text).strip()
    if len(cleaned) <= max_chars:
        return cleaned, False
    head = max_chars // 2
    tail = max_chars - head
    return (
        f"{cleaned[:head]}\n... [execution evidence truncated] ...\n{cleaned[-tail:]}",
        True,
    )
