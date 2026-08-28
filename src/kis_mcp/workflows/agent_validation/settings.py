from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_ALLOWED_TARGETS = ("generic", "claude-code", "cursor", "codex", "kiro")


@dataclass(frozen=True, slots=True)
class AgnixValidationSettings:
    version: str
    install_root: Path
    binary_relative_path: str
    runtime_kind: str
    wsl_distribution: str
    timeout_ms: int
    default_max_files: int
    max_files: int
    max_output_chars: int
    max_findings: int
    targets: tuple[str, ...]

    @property
    def binary_path(self) -> Path:
        return self.install_root / Path(self.binary_relative_path)

    @classmethod
    def load(cls, path: Path) -> "AgnixValidationSettings":
        data = json.loads(path.read_text(encoding="utf-8"))
        validation = data.get("validation", {})
        targets = tuple(validation.get("targets", _ALLOWED_TARGETS))
        if data.get("package") != "agnix" or data.get("version") != "0.45.0":
            raise ValueError("agnix validation requires pinned agnix 0.45.0 settings")
        if not targets or any(item not in _ALLOWED_TARGETS for item in targets):
            raise ValueError("agnix validation targets are invalid")
        values = {
            "timeout_ms": validation.get("timeout_ms", 120_000),
            "default_max_files": validation.get("default_max_files", 1000),
            "max_files": validation.get("max_files", 10_000),
            "max_output_chars": validation.get("max_output_chars", 200_000),
            "max_findings": validation.get("max_findings", 500),
        }
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in values.values()):
            raise ValueError("agnix validation numeric limits must be positive integers")
        if values["default_max_files"] > values["max_files"]:
            raise ValueError("agnix default_max_files exceeds max_files")
        runtime_kind = validation.get("runtime_kind", "wsl")
        wsl_distribution = validation.get("wsl_distribution", "Ubuntu")
        if runtime_kind != "wsl":
            raise ValueError("agnix validation runtime_kind must be wsl")
        if not isinstance(wsl_distribution, str) or not wsl_distribution.strip():
            raise ValueError("agnix validation wsl_distribution must be a non-empty string")
        return cls(
            version="0.45.0",
            install_root=Path(data["install_root"]),
            binary_relative_path=validation.get("binary_relative_path", r"bin\agnix"),
            runtime_kind=runtime_kind,
            wsl_distribution=wsl_distribution,
            targets=targets,
            **values,
        )


__all__ = ["AgnixValidationSettings"]
