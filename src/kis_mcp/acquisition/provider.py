from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PureWindowsPath
from typing import Any

from fastmcp.exceptions import ToolError

CommandRunner = Callable[[Sequence[str], Path, Mapping[str, str]], Any]


def _default_runner(args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(args),
            cwd=cwd,
            env=dict(env),
            text=True,
            capture_output=True,
            check=False,
            timeout=900,
        )
    except FileNotFoundError as exc:
        raise ToolError(f"IMPORT_ISOLATE_COMMAND_MISSING: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolError("IMPORT_ISOLATE_COMMAND_TIMEOUT: registered acquisition exceeded 900 seconds") from exc


class ImportIsolateProvider:
    """Invoke only the registered import-isolate acquisition dispatcher."""

    def __init__(
        self,
        provider_root: str,
        script_relative_path: str,
        temp_root: str,
        *,
        runner: CommandRunner | None = None,
    ) -> None:
        root = PureWindowsPath(provider_root)
        script = root / PureWindowsPath(script_relative_path)
        self.provider_root = Path(str(root))
        self.script_path = Path(str(script))
        self.temp_root = Path(temp_root) / "external-acquisition"
        self.runner = runner or _default_runner

    def acquire(self, request: dict[str, object], recipe_path: str) -> dict[str, object]:
        try:
            serialized = json.dumps(
                request,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ToolError("INVALID_ACQUISITION_REQUEST: request is not strict JSON") from exc
        self.temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="request-", dir=self.temp_root) as directory:
            request_path = Path(directory) / "request.json"
            request_path.write_text(serialized, encoding="utf-8")
            result = self.runner(
                (
                    "pwsh",
                    "-NoProfile",
                    "-NonInteractive",
                    "-File",
                    str(self.script_path),
                    "-RequestPath",
                    str(request_path),
                    "-RecipePath",
                    str(recipe_path),
                ),
                self.provider_root,
                dict(os.environ),
            )
        returncode = int(getattr(result, "returncode", -1))
        if returncode != 0:
            raise ToolError(f"IMPORT_ISOLATE_ACQUISITION_FAILED: provider exited with code {returncode}")
        lines = [line.strip() for line in str(getattr(result, "stdout", "")).splitlines() if line.strip()]
        if not lines:
            raise ToolError("IMPORT_ISOLATE_RESULT_MISSING: provider emitted no result")
        try:
            payload = json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: final provider output is not JSON") from exc
        if not isinstance(payload, dict):
            raise ToolError("IMPORT_ISOLATE_RESULT_INVALID: provider result must be an object")
        return dict(payload)


__all__ = ["ImportIsolateProvider"]
