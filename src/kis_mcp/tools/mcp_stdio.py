from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

_ENVIRONMENT_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_ACQUISITION_COMMANDS = {"npx", "npx.cmd", "uvx", "uvx.exe"}
_ACQUISITION_FLAGS = {"-y", "--yes"}


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _command_name(value: str) -> str:
    return PurePath(value.replace("\\", "/")).name.lower()


@dataclass(frozen=True, slots=True)
class StdioMcpCommand:
    """Validated local stdio command metadata with no execution behavior."""

    executable: str
    arguments: tuple[str, ...] = ()
    environment_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        executable = _required_text(self.executable, "executable")
        if _command_name(executable) in _ACQUISITION_COMMANDS:
            raise ValueError("package acquisition commands are not permitted")

        arguments = tuple(_required_text(item, "argument") for item in self.arguments)
        if len(set(arguments)) != len(arguments):
            raise ValueError("arguments must be unique")
        for argument in arguments:
            lowered = argument.lower()
            if lowered in _ACQUISITION_FLAGS or _command_name(argument) in _ACQUISITION_COMMANDS:
                raise ValueError("package acquisition arguments are not permitted")
            if lowered.endswith("@latest"):
                raise ValueError("floating package versions are not permitted")

        environment_names = tuple(
            _required_text(item, "environment variable name")
            for item in self.environment_names
        )
        if len(set(environment_names)) != len(environment_names):
            raise ValueError("environment variable names must be unique")
        for name in environment_names:
            if not _ENVIRONMENT_NAME.fullmatch(name):
                raise ValueError(
                    "environment variable names must use upper-case shell syntax"
                )

        object.__setattr__(self, "executable", executable)
        object.__setattr__(self, "arguments", arguments)
        object.__setattr__(self, "environment_names", tuple(sorted(environment_names)))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "executable": self.executable,
            "arguments": list(self.arguments),
            "environment_names": list(self.environment_names),
        }


__all__ = ["StdioMcpCommand"]
