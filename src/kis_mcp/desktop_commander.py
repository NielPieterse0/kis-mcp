from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import re
from typing import Any

from .command_intent import resolve_command_effects
from .contracts import ProviderCapabilities
from .models import InvocationEffects
from .process_state import ProcessStateRegistry
from .runtime_observability import RuntimeObservability, get_runtime_observability


NETWORK_ONLY_TOOLS = frozenset({"give_feedback_to_desktop_commander"})
UNEXPOSED_TOOL_ARGUMENTS: dict[str, frozenset[str]] = {
    "read_file": frozenset({"isUrl"}),
}
UNEXPOSED_CONFIG_KEYS = frozenset({"blockedCommands", "allowedDirectories"})
CONFIGURATION_TOOL_NAME = "set_config_value"
_SEARCH_START_TOOLS = frozenset({"start_search"})
_SEARCH_INTERACTION_TOOLS = frozenset({"get_more_search_results"})
_SEARCH_STOP_TOOLS = frozenset({"stop_search"})
_SEARCH_ID_PATTERN = re.compile(
    r"(?i)\bsearch(?:\s+id)?\s*[:=]\s*([A-Za-z0-9._-]{1,128})"
)
COMMAND_TOOLS = frozenset(
    {"start_process", "execute_command", "interact_with_process"}
)
ENTRY_PATH_KEYS: dict[str, tuple[str, ...]] = {
    "move_file": ("source", "destination"),
}
CONDITIONAL_WRITE_PATH_KEYS: dict[str, tuple[str, ...]] = {
    "write_pdf": ("path", "outputPath"),
}

WRITE_PATH_KEYS: dict[str, tuple[str, ...]] = {
    "write_file": ("path",),
    "write_docx": ("path",),
    "write_excel": ("path",),
    "create_directory": ("path",),
    "edit_block": ("file_path", "path"),
}

DELETE_PATH_KEYS: dict[str, tuple[str, ...]] = {
    "delete_file": ("path",),
    "delete_directory": ("path",),
    "remove_file": ("path",),
    "remove_directory": ("path",),
}


@dataclass(slots=True)
class DesktopCommanderEffectResolver:
    project_boundary: str
    provider_state_file: str
    observability: RuntimeObservability = field(default_factory=get_runtime_observability)
    process_states: ProcessStateRegistry | None = None

    def __post_init__(self) -> None:
        if self.process_states is None:
            self.process_states = ProcessStateRegistry(observability=self.observability)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            network_only_tools=NETWORK_ONLY_TOOLS,
            direct_delete_tools=frozenset(DELETE_PATH_KEYS),
            unexposed_tool_arguments=UNEXPOSED_TOOL_ARGUMENTS,
            unexposed_config_keys=UNEXPOSED_CONFIG_KEYS,
            configuration_tool_name=CONFIGURATION_TOOL_NAME,
        )

    @property
    def network_only_tools(self) -> frozenset[str]:
        return self.capabilities.network_only_tools

    @property
    def direct_delete_tools(self) -> frozenset[str]:
        return self.capabilities.direct_delete_tools

    @property
    def unexposed_tool_arguments(self) -> Mapping[str, frozenset[str]]:
        return self.capabilities.unexposed_tool_arguments

    @property
    def unexposed_config_keys(self) -> frozenset[str]:
        return self.capabilities.unexposed_config_keys

    def resolve(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
    ) -> InvocationEffects:
        args = dict(arguments or {})
        normalized_name = tool_name.casefold()

        if normalized_name in COMMAND_TOOLS:
            command = self._command_text(normalized_name, args)
            if not command:
                return InvocationEffects()
            if normalized_name == "interact_with_process":
                tracked = self.process_states.resolve_interaction(
                    args,
                    project_boundary=self.project_boundary,
                )
                if tracked is not None:
                    return tracked
            cwd = self._working_directory(args)
            shell = args.get("shell") if isinstance(args.get("shell"), str) else None
            return resolve_command_effects(
                command,
                cwd=cwd,
                project_boundary=self.project_boundary,
                shell=shell,
            )

        if normalized_name == CONFIGURATION_TOOL_NAME:
            external_network = (
                str(args.get("key", "")).casefold() == "telemetryenabled"
                and not self._telemetry_disabled(args.get("value"))
            )
            return InvocationEffects(
                write_paths=(self.provider_state_file,),
                external_network=external_network,
            )

        if normalized_name in ENTRY_PATH_KEYS:
            paths = self._collect_paths(args, ENTRY_PATH_KEYS[normalized_name])
            return InvocationEffects(entry_paths=paths)

        if normalized_name in CONDITIONAL_WRITE_PATH_KEYS:
            output_path = args.get("outputPath")
            effective_key = (
                "outputPath"
                if isinstance(output_path, str) and output_path.strip()
                else "path"
            )
            return InvocationEffects(
                write_paths=self._collect_paths(args, (effective_key,))
            )

        if normalized_name in WRITE_PATH_KEYS:
            paths = self._collect_paths(args, WRITE_PATH_KEYS[normalized_name])
            return InvocationEffects(write_paths=paths)

        if normalized_name in DELETE_PATH_KEYS:
            paths = self._collect_paths(args, DELETE_PATH_KEYS[normalized_name])
            return InvocationEffects(delete_paths=paths)

        return InvocationEffects()

    def observe_success(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
        result: Any,
    ) -> None:
        args = dict(arguments or {})
        process_states = self.process_states
        if process_states is not None:
            process_states.observe_success(
                tool_name,
                args,
                result,
                project_boundary=self.project_boundary,
            )

        normalized = tool_name.casefold()
        if normalized in _SEARCH_START_TOOLS:
            search_id = self._search_id_from_result(result)
            if search_id:
                self.observability.search_started(
                    search_id=search_id,
                    tool_name=normalized,
                )
        elif normalized in _SEARCH_INTERACTION_TOOLS:
            search_id = self._search_id_from_arguments(args)
            if search_id:
                self.observability.search_interacted(search_id=search_id)
        elif normalized in _SEARCH_STOP_TOOLS:
            search_id = self._search_id_from_arguments(args)
            if search_id:
                self.observability.search_stopped(search_id=search_id)

    def _working_directory(self, arguments: Mapping[str, Any]) -> str:
        for key in ("cwd", "working_directory", "workingDirectory"):
            value = arguments.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return self.project_boundary

    @staticmethod
    def _command_text(tool_name: str, arguments: Mapping[str, Any]) -> str:
        keys = ("input", "command") if tool_name == "interact_with_process" else (
            "command",
            "input",
        )
        for key in keys:
            value = arguments.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Sequence) and not isinstance(
                value,
                (str, bytes, bytearray),
            ):
                return " ".join(str(item) for item in value)
        return ""

    @staticmethod
    def _collect_paths(
        arguments: Mapping[str, Any],
        keys: tuple[str, ...],
    ) -> tuple[str, ...]:
        paths: list[str] = []
        for key in keys:
            value = arguments.get(key)
            if isinstance(value, str) and value.strip():
                paths.append(value)
            elif isinstance(value, Sequence) and not isinstance(
                value,
                (str, bytes, bytearray),
            ):
                paths.extend(
                    str(item)
                    for item in value
                    if isinstance(item, str) and item.strip()
                )
        return tuple(dict.fromkeys(paths))

    @staticmethod
    def _search_id_from_arguments(arguments: Mapping[str, Any]) -> str | None:
        for key in ("search_id", "searchId", "id"):
            value = arguments.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:128]
        return None

    @staticmethod
    def _search_id_from_result(result: Any) -> str | None:
        seen: set[int] = set()

        def visit(value: Any, depth: int) -> str | None:
            if value is None or depth > 4:
                return None
            identity = id(value)
            if identity in seen:
                return None
            seen.add(identity)
            if isinstance(value, str):
                match = _SEARCH_ID_PATTERN.search(value)
                return match.group(1) if match else None
            if isinstance(value, Mapping):
                direct = DesktopCommanderEffectResolver._search_id_from_arguments(value)
                if direct:
                    return direct
                for nested in value.values():
                    found = visit(nested, depth + 1)
                    if found:
                        return found
                return None
            if isinstance(value, Sequence) and not isinstance(
                value,
                (str, bytes, bytearray),
            ):
                for nested in value:
                    found = visit(nested, depth + 1)
                    if found:
                        return found
                return None
            for attribute in ("content", "structured_content", "text", "data", "result"):
                if hasattr(value, attribute):
                    found = visit(getattr(value, attribute), depth + 1)
                    if found:
                        return found
            return None

        return visit(result, 0)

    @staticmethod
    def _telemetry_disabled(value: Any) -> bool:
        return value is False or (
            isinstance(value, str) and value.strip().casefold() == "false"
        )
