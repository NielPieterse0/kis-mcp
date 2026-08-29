from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from ...config import load_runtime_config
from ...server import build_server

_RUNTIME_INSTANCE = "KIS_MCP_RUNTIME_INSTANCE"
_WORK_ID = "KIS_MCP_CANDIDATE_WORK_ID"
_CONTRACT = "KIS_MCP_CANDIDATE_CONTRACT_FINGERPRINT"
_INSTANCE = "KIS_MCP_CANDIDATE_INSTANCE_ID"
_SOURCE = "KIS_MCP_CANDIDATE_SOURCE_IDENTITY"
_SOURCE_PATH = "KIS_MCP_CANDIDATE_SOURCE_PATH"
_CHANGE_ID = "KIS_MCP_CANDIDATE_CHANGE_ID"


def main(argv: Sequence[str] | None = None) -> None:
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
    os.environ[_RUNTIME_INSTANCE] = f"candidate:{args.work_id}"
    os.environ[_WORK_ID] = args.work_id
    os.environ[_CONTRACT] = args.contract_fingerprint
    os.environ[_INSTANCE] = args.instance_id
    os.environ[_SOURCE] = args.source_identity
    os.environ[_SOURCE_PATH] = args.source_path
    os.environ[_CHANGE_ID] = args.change_id
    config = load_runtime_config()
    server = build_server(config)
    server.run(
        transport="http", host="127.0.0.1", port=args.port, path="/mcp",
        stateless_http=config.remote_stateless_http,
        json_response=config.remote_json_response, show_banner=False,
    )


if __name__ == "__main__":
    main()
