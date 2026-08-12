from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from kis_mcp.workflows.agent_validation.execution import (
    AgentValidationError,
    AgentValidationService,
)
from kis_mcp.workflows.agent_validation.settings import AgnixValidationSettings


def _settings(binary: Path) -> AgnixValidationSettings:
    return AgnixValidationSettings(
        version="0.45.0",
        install_root=binary.parents[3],
        binary_relative_path=str(binary.relative_to(binary.parents[3])),
        timeout_ms=5000,
        default_max_files=100,
        max_files=1000,
        max_output_chars=10000,
        max_findings=2,
        targets=("generic", "codex"),
    )


def test_validation_builds_only_fixed_read_only_agnix_command(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    binary = tmp_path / "install" / "node_modules" / "agnix" / "bin" / "agnix-binary.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"x")
    calls: list[tuple[str, dict[str, Any]]] = []
    payload = json.dumps(
        {
            "version": "0.45.0",
            "files_checked": 1,
            "diagnostics": [{"level": "warning", "rule": "A"}],
            "summary": {"errors": 0, "warnings": 1, "info": 0},
        }
    )

    async def runner(name: str, arguments: dict[str, Any]) -> Any:
        calls.append((name, arguments))
        return {"text": payload + "\n__KIS_AGNIX_EXIT_CODE=0"}

    service = AgentValidationService(boundary=tmp_path, settings=_settings(binary), runner=runner)
    result = asyncio.run(
        service.validate(project=str(project), target="codex", strict=True, max_files=50)
    )

    assert result.warnings == 1
    assert result.files_checked == 1
    command = calls[0][1]["command"]
    assert calls[0][0] == "start_process"
    assert "--format' 'json" in command
    assert "--target' 'codex" in command
    assert "--max-files' '50" in command
    assert "--strict" in command
    assert "--fix" not in command
    assert "--watch" not in command
    assert " telemetry " not in command


def test_findings_are_bounded_without_changing_summary(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    binary = tmp_path / "install" / "node_modules" / "agnix" / "bin" / "agnix-binary.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"x")
    payload = json.dumps(
        {
            "version": "0.45.0",
            "files_checked": 3,
            "diagnostics": [{"rule": "A"}, {"rule": "B"}, {"rule": "C"}],
            "summary": {"errors": 1, "warnings": 2, "info": 0},
        }
    )

    async def runner(_name: str, _arguments: dict[str, Any]) -> Any:
        return {"text": payload + "\n__KIS_AGNIX_EXIT_CODE=1"}

    result = asyncio.run(
        AgentValidationService(boundary=tmp_path, settings=_settings(binary), runner=runner).validate(
            project=str(project)
        )
    )
    assert len(result.diagnostics) == 2
    assert result.truncated is True
    assert (result.errors, result.warnings) == (1, 2)


def test_invalid_request_fails_before_process_execution(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    binary = tmp_path / "install" / "node_modules" / "agnix" / "bin" / "agnix-binary.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"x")

    async def runner(_name: str, _arguments: dict[str, Any]) -> Any:
        raise AssertionError("runner must not execute")

    service = AgentValidationService(boundary=tmp_path, settings=_settings(binary), runner=runner)
    with pytest.raises(AgentValidationError, match="AGNIX_TARGET_INVALID"):
        asyncio.run(service.validate(project=str(project), target="other"))
    with pytest.raises(AgentValidationError, match="AGNIX_MAX_FILES_INVALID"):
        asyncio.run(service.validate(project=str(project), max_files=1001))


def test_plain_text_agnix_file_limit_is_classified_explicitly(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    binary = tmp_path / "install" / "node_modules" / "agnix" / "bin" / "agnix-binary.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"x")

    async def runner(_name: str, _arguments: dict[str, Any]) -> Any:
        return {
            "text": "Error: Too many files to validate: 51 files found, limit is 50\n"
            "__KIS_AGNIX_EXIT_CODE=1"
        }

    service = AgentValidationService(boundary=tmp_path, settings=_settings(binary), runner=runner)
    with pytest.raises(AgentValidationError) as captured:
        asyncio.run(service.validate(project=str(project), max_files=50))

    assert captured.value.code == "AGNIX_FILE_LIMIT_EXCEEDED"
    assert "51 files" in captured.value.reason
    assert "limit 50" in captured.value.reason
