from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .command_intent import resolve_command_effects
from .contracts import ProviderCapabilities
from .models import InvocationEffects


NETWORK_ONLY_TOOLS = frozenset({"give_feedback_to_desktop_commander"})
UNEXPOSED_TOOL_ARGUMENTS: dict[str, frozenset[str]] = {
    "read_file": frozenset({"isUrl"}),
}
UNEXPOSED_CONFIG_KEYS = frozenset({"blockedCommands", "allowedDirectories"})
CONFIGURATION_TOOL_NAME = "set_config_value"
COMMAND_TOOLS = frozenset(
    {"start_process", "execute_command", "interact_with_process"}
)

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


@dataclass(frozen=True, slots=True)
class DesktopCommanderEffectResolver:
    project_boundary: str
    provider_state_file: str

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
            cwd = self._working_directory(args)
            return resolve_command_effects(
                command,
                cwd=cwd,
                project_boundary=self.project_boundary,
            )

        if normalized_name == "set_config_value":
            external_network = (
                str(args.get("key", "")).casefold() == "telemetryenabled"
                and not self._telemetry_disabled(args.get("value"))
            )
            return InvocationEffects(
                write_paths=(self.provider_state_file,),
                external_network=external_network,
            )

        if normalized_name == "move_file":
            paths = self._collect_paths(args, ("source", "destination"))
            return InvocationEffects(entry_paths=paths)

        if normalized_name == "write_pdf":
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
            if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
                return " ".join(str(item) for item in value)
        return ""

    @staticmethod
    def _collect_paths(
        arguments: Mapping[str, Any], keys: tuple[str, ...]
    ) -> tuple[str, ...]:
        paths: list[str] = []
        for key in keys:
            value = arguments.get(key)
            if isinstance(value, str) and value.strip():
                paths.append(value)
            elif isinstance(value, Sequence) and not isinstance(
                value, (str, bytes, bytearray)
            ):
                paths.extend(
                    str(item) for item in value if isinstance(item, str) and item.strip()
                )
        return tuple(dict.fromkeys(paths))

    @staticmethod
    def _telemetry_disabled(value: Any) -> bool:
        return value is False or (
            isinstance(value, str) and value.strip().casefold() == "false"
        )
