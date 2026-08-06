from __future__ import annotations

import ntpath
from collections.abc import Mapping
from threading import RLock
from typing import Any

from ...command_intent import resolve_command_effects
from ...contracts import ProviderCapabilities
from ...models import InvocationEffects
from ...paths import is_within_windows_boundary, normalize_windows_path
from .memory import resolve_memory_path
from .settings import SerenaSettings

_FILE_MUTATIONS = frozenset(
    {
        "replace_symbol_body",
        "insert_after_symbol",
        "insert_before_symbol",
        "rename_symbol",
        "replace_content",
    }
)
_MEMORY_WRITES = frozenset({"write_memory", "edit_memory"})


def _operation(tool_name: str) -> str | None:
    folded = tool_name.casefold()
    if not folded.startswith("serena_"):
        return None
    return folded[len("serena_") :].replace("-", "_")


def _required_argument(arguments: Mapping[str, Any], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


class SerenaEffectResolver:
    """Resolve only concrete Serena invocation effects into the three-rule contract."""

    def __init__(self, settings: SerenaSettings, *, project_root: str) -> None:
        self.settings = settings
        self._lock = RLock()
        self._project_root = self._validated_project_root(project_root)
        self._capabilities = ProviderCapabilities(
            network_only_tools=frozenset(),
            direct_delete_tools=frozenset({"serena_delete_memory"}),
            unexposed_tool_arguments={},
            unexposed_config_keys=frozenset(),
            configuration_tool_name=None,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    @property
    def project_root(self) -> str:
        with self._lock:
            return self._project_root

    def _validated_project_root(self, value: str) -> str:
        root = normalize_windows_path(value, base=self.settings.project_boundary)
        if not is_within_windows_boundary(root, boundary=self.settings.project_boundary):
            raise ValueError("Serena project root must remain inside project_boundary")
        return root

    def _project_path(self, relative_path: str) -> str:
        raw = relative_path.strip()
        if not raw:
            raise ValueError("relative_path must be a non-empty string")
        if ntpath.isabs(raw.replace("/", "\\")):
            raise ValueError("relative_path must be project-relative")
        root = self.project_root
        path = normalize_windows_path(raw, base=root)
        if not is_within_windows_boundary(path, boundary=root):
            raise ValueError("relative_path resolves outside the active Serena project")
        return path

    def resolve(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
    ) -> InvocationEffects:
        operation = _operation(tool_name)
        if operation is None:
            return InvocationEffects()
        values = dict(arguments or {})

        if operation in _FILE_MUTATIONS:
            return InvocationEffects(
                write_paths=(
                    self._project_path(_required_argument(values, "relative_path")),
                )
            )

        if operation in _MEMORY_WRITES:
            path, _root = resolve_memory_path(
                self.settings,
                _required_argument(values, "memory_name"),
                project_root=self.project_root,
            )
            return InvocationEffects(write_paths=(path,))

        if operation == "delete_memory":
            path, _root = resolve_memory_path(
                self.settings,
                _required_argument(values, "memory_name"),
                project_root=self.project_root,
            )
            return InvocationEffects(delete_paths=(path,))

        if operation == "rename_memory":
            source, source_root = resolve_memory_path(
                self.settings,
                _required_argument(values, "old_name"),
                project_root=self.project_root,
            )
            destination, destination_root = resolve_memory_path(
                self.settings,
                _required_argument(values, "new_name"),
                project_root=self.project_root,
            )
            if source_root != destination_root:
                raise ValueError("rename_memory cannot cross project and global memory roots")
            return InvocationEffects(
                write_paths=(source_root,),
                entry_paths=(source, destination),
            )

        if operation == "execute_shell_command":
            command = _required_argument(values, "command")
            cwd_value = values.get("cwd")
            cwd = (
                self._validated_project_root(cwd_value)
                if isinstance(cwd_value, str) and cwd_value.strip()
                else self.project_root
            )
            shell = values.get("shell")
            return resolve_command_effects(
                command,
                cwd=cwd,
                project_boundary=self.settings.project_boundary,
                shell=shell if isinstance(shell, str) else None,
            )

        return InvocationEffects()

    def observe_success(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None,
        result: Any,
    ) -> None:
        if _operation(tool_name) != "activate_project":
            return
        values = dict(arguments or {})
        project = values.get("project")
        if not isinstance(project, str) or not project.strip():
            return
        normalized = self._validated_project_root(project)
        with self._lock:
            self._project_root = normalized


__all__ = ["SerenaEffectResolver"]