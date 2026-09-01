from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_RUNTIME_INSTANCE = "KIS_MCP_RUNTIME_INSTANCE"
_WORK_ID = "KIS_MCP_CANDIDATE_WORK_ID"
_CONTRACT = "KIS_MCP_CANDIDATE_CONTRACT_FINGERPRINT"
_INSTANCE = "KIS_MCP_CANDIDATE_INSTANCE_ID"
_SOURCE = "KIS_MCP_CANDIDATE_SOURCE_IDENTITY"
_SOURCE_PATH = "KIS_MCP_CANDIDATE_SOURCE_PATH"
_CHANGE_ID = "KIS_MCP_CANDIDATE_CHANGE_ID"
_SOURCE_COMMIT = "KIS_MCP_CANDIDATE_SOURCE_COMMIT"
_SOURCE_TREE = "KIS_MCP_CANDIDATE_SOURCE_TREE"
_POLICY = "KIS_MCP_CANDIDATE_POLICY_FINGERPRINT"
_RUNTIME = "KIS_MCP_CANDIDATE_RUNTIME_FINGERPRINT"
_ENDPOINT = "KIS_MCP_CANDIDATE_ENDPOINT"


def _runtime_instance_id(work_id: str) -> str:
    canonical = work_id.casefold()
    suffix = re.sub(r"[^a-z0-9]+", "-", canonical).strip("-")
    digest = hashlib.sha256(work_id.encode("utf-8")).hexdigest()[:10]
    return f"candidate-{suffix or 'work'}-{digest}"


def _file_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_identity(source_root: Path) -> tuple[str, str]:
    def resolve(ref: str) -> str:
        result = subprocess.run(
            ["git", "rev-parse", ref], cwd=source_root, check=True,
            capture_output=True, text=True, timeout=15,
        )
        value = result.stdout.strip().lower()
        if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError(f"invalid Git identity for {ref}")
        return value
    return resolve("HEAD"), resolve("HEAD^{tree}")


def candidate_binding(source_path: str | Path, port: int) -> dict[str, str]:
    source_root = Path(source_path).resolve()
    commit, tree = _git_identity(source_root)
    return {
        "source_commit": commit,
        "source_tree": tree,
        "policy_fingerprint": _file_fingerprint(source_root / "policy" / "kis-mcp.policy.json"),
        "runtime_fingerprint": _file_fingerprint(source_root / "settings" / "kis-mcp.settings.json"),
        "endpoint": f"http://127.0.0.1:{port}/mcp",
    }


def select_live_verification_scenarios(
    affected_surfaces: Sequence[str],
    tool_schemas: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Select a deterministic, effect-aware normal candidate scenario set."""
    selected: list[dict[str, Any]] = [{"tool": "candidate_identity", "arguments": {}}]
    normalized = {item.casefold().replace("-", "_") for item in affected_surfaces if item.strip()}
    for tool_name in sorted(tool_schemas):
        if tool_name == "candidate_identity":
            continue
        key = tool_name.casefold().replace("-", "_")
        if key not in normalized and not any(part and part in key for part in normalized):
            continue
        schema = tool_schemas[tool_name]
        required = tuple(schema.get("required", ()))
        read_only = schema.get("read_only") is True
        if read_only and not required:
            selected.append({"tool": tool_name, "arguments": {}})
        elif read_only:
            selected.append({
                "tool": tool_name,
                "arguments": {},
                "expect_error": True,
                "negative_path": "missing_required_arguments",
            })
        else:
            selected.append({
                "tool": tool_name,
                "arguments": {},
                "expect_error": True,
                "negative_path": "effect_boundary",
            })
    return tuple(selected)


def _candidate_environment(args: argparse.Namespace) -> dict[str, str]:
    binding = candidate_binding(args.source_path, args.port)
    return {
        _RUNTIME_INSTANCE: _runtime_instance_id(args.work_id),
        _WORK_ID: args.work_id,
        _CONTRACT: args.contract_fingerprint,
        _INSTANCE: args.instance_id,
        _SOURCE: args.source_identity,
        _SOURCE_PATH: str(Path(args.source_path).resolve()),
        _CHANGE_ID: args.change_id,
        _SOURCE_COMMIT: binding["source_commit"],
        _SOURCE_TREE: binding["source_tree"],
        _POLICY: binding["policy_fingerprint"],
        _RUNTIME: binding["runtime_fingerprint"],
        _ENDPOINT: binding["endpoint"],
    }


def main(argv: Sequence[str] | None = None) -> None:
    from ...config import load_runtime_config
    from ...server import build_server

    parser = argparse.ArgumentParser(description="Run one isolated task-candidate KIS MCP server.")
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--work-id", required=True)
    parser.add_argument("--contract-fingerprint", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--source-identity", required=True)
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--change-id", required=True)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    os.environ.update(_candidate_environment(args))
    config = load_runtime_config()
    server = build_server(config)
    server.run(
        transport="http", host="127.0.0.1", port=args.port, path="/mcp",
        stateless_http=config.remote_stateless_http,
        json_response=config.remote_json_response, show_banner=False,
    )


if __name__ == "__main__":
    main()
