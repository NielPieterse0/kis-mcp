from __future__ import annotations

import importlib
import json
import os
import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "kis_mcp"
ATOMIC_ADAPTER_PATH = PACKAGE_ROOT / "provider_state_atomic.cjs"
STARTUP_ADAPTER_PATH = PACKAGE_ROOT / "provider_startup_compat.cjs"
LIFECYCLE_PATH = PACKAGE_ROOT / "provider_lifecycle.py"


def _run_node_json(script: str) -> object:
    environment = dict(os.environ)
    environment.pop("KIS_MCP_PROVIDER_STATE_FILE", None)
    environment.pop("KIS_MCP_PROVIDER_STARTUP_COMPAT", None)
    environment.pop("KIS_MCP_PROVIDER_FLAG_URL", None)
    completed = subprocess.run(
        ["node.exe", "-e", script],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_atomic_provider_state_adapter_writes_temp_then_renames(
    tmp_path: Path,
) -> None:
    assert ATOMIC_ADAPTER_PATH.is_file()
    target = tmp_path / "config.json"
    other = tmp_path / "other.json"
    script = f"""
const adapter = require({json.dumps(str(ATOMIC_ADAPTER_PATH))});

async function main() {{
  const atomicCalls = [];
  const atomicFs = {{
    writeFile: async (...args) => atomicCalls.push(["writeFile", ...args.map(String)]),
    rename: async (...args) => atomicCalls.push(["rename", ...args.map(String)]),
  }};
  adapter.installAtomicStateWriter({{
    fsPromises: atomicFs,
    target: {json.dumps(str(target))},
    processId: 41,
    randomId: () => "fixed",
  }});
  await atomicFs.writeFile({json.dumps(str(target))}, "new", "utf8");

  const passthroughCalls = [];
  const passthroughFs = {{
    writeFile: async (...args) => passthroughCalls.push(["writeFile", ...args.map(String)]),
    rename: async (...args) => passthroughCalls.push(["rename", ...args.map(String)]),
  }};
  adapter.installAtomicStateWriter({{
    fsPromises: passthroughFs,
    target: {json.dumps(str(target))},
    processId: 42,
    randomId: () => "unused",
  }});
  await passthroughFs.writeFile({json.dumps(str(other))}, "other", "utf8");

  console.log(JSON.stringify({{ atomicCalls, passthroughCalls }}));
}}

main().catch((error) => {{
  console.error(error);
  process.exitCode = 1;
}});
"""

    result = _run_node_json(script)
    assert isinstance(result, dict)
    atomic_calls = result["atomicCalls"]
    passthrough_calls = result["passthroughCalls"]

    assert atomic_calls[0][0] == "writeFile"
    temporary_path = Path(atomic_calls[0][1])
    assert temporary_path.parent == target.parent
    assert temporary_path.name == f".{target.name}.41.fixed.tmp"
    assert atomic_calls[0][2:] == ["new", "utf8"]
    assert atomic_calls[1] == ["rename", str(temporary_path), str(target)]
    assert passthrough_calls == [["writeFile", str(other), "other", "utf8"]]


def test_startup_adapter_contains_exact_feature_flag_fetch() -> None:
    script = f"""
const adapter = require({json.dumps(str(STARTUP_ADAPTER_PATH))});

async function main() {{
  const calls = [];
  const originalFetch = async (...args) => {{
    calls.push(args.map(String));
    return new Response('{{"source":"network"}}', {{ status: 200 }});
  }};
  const contained = adapter.createContainedFetch({{
    originalFetch,
    flagUrl: 'http://127.0.0.1:9/kis-mcp-offline',
    ResponseClass: Response,
  }});
  const response = await contained('http://127.0.0.1:9/kis-mcp-offline');
  console.log(JSON.stringify({{
    body: await response.json(),
    calls,
  }}));
}}

main().catch((error) => {{
  console.error(error);
  process.exitCode = 1;
}});
"""

    result = _run_node_json(script)
    assert result == {"body": {"flags": {}}, "calls": []}


def test_startup_adapter_passes_unrelated_fetch_through() -> None:
    script = f"""
const adapter = require({json.dumps(str(STARTUP_ADAPTER_PATH))});

async function main() {{
  const calls = [];
  const originalFetch = async (...args) => {{
    calls.push(args.map(String));
    return new Response('{{"source":"original"}}', {{ status: 201 }});
  }};
  const contained = adapter.createContainedFetch({{
    originalFetch,
    flagUrl: 'http://127.0.0.1:9/kis-mcp-offline',
    ResponseClass: Response,
  }});
  const response = await contained('http://127.0.0.1:9/ordinary-local-request');
  console.log(JSON.stringify({{
    status: response.status,
    body: await response.json(),
    calls,
  }}));
}}

main().catch((error) => {{
  console.error(error);
  process.exitCode = 1;
}});
"""

    result = _run_node_json(script)
    assert result == {
        "status": 201,
        "body": {"source": "original"},
        "calls": [["http://127.0.0.1:9/ordinary-local-request"]],
    }


def test_startup_adapter_suppresses_provider_logs_and_strips_ui_metadata() -> None:
    script = f"""
const adapter = require({json.dumps(str(STARTUP_ADAPTER_PATH))});

const writes = [];
const callbacks = [];
const filtered = adapter.createFilteredStdoutWrite({{
  originalWrite: (value) => {{ writes.push(String(value)); return true; }},
}});

filtered(JSON.stringify({{
  jsonrpc: '2.0',
  method: 'notifications/message',
  params: {{ level: 'info', logger: 'desktop-commander', data: 'startup noise' }},
}}) + '\\n', undefined, () => callbacks.push('log'));

filtered(JSON.stringify({{
  jsonrpc: '2.0',
  id: 2,
  result: {{
    tools: [
      {{
        name: 'read_file',
        inputSchema: {{ type: 'object' }},
        _meta: {{ ui: {{ resourceUri: 'ui://desktop-commander/preview' }} }},
        meta: {{ provider: 'desktop-commander' }},
      }},
      {{ name: 'get_config', inputSchema: {{ type: 'object' }} }},
      {{ name: 'set_config_value', inputSchema: {{ type: 'object' }} }},
      {{ name: 'get_prompts', inputSchema: {{ type: 'object' }} }},
      {{ name: 'get_usage_stats', inputSchema: {{ type: 'object' }} }},
      {{ name: 'get_recent_tool_calls', inputSchema: {{ type: 'object' }} }},
    ],
  }},
}}) + '\\n', undefined, () => callbacks.push('tools'));

const parsed = JSON.parse(writes[0]);
console.log(JSON.stringify({{
  writes,
  callbacks,
  tools: parsed.result.tools,
}}));
"""

    result = _run_node_json(script)
    assert isinstance(result, dict)
    assert result["callbacks"] == ["log"]
    assert len(result["writes"]) == 1
    assert result["tools"] == [
        {
            "name": "read_file",
            "inputSchema": {"type": "object"},
        },
        {"name": "get_config", "inputSchema": {"type": "object"}},
        {"name": "set_config_value", "inputSchema": {"type": "object"}},
        {"name": "get_prompts", "inputSchema": {"type": "object"}},
        {"name": "get_usage_stats", "inputSchema": {"type": "object"}},
        {"name": "get_recent_tool_calls", "inputSchema": {"type": "object"}},
    ]


def test_startup_adapter_preserves_non_log_notifications() -> None:
    script = f"""
const adapter = require({json.dumps(str(STARTUP_ADAPTER_PATH))});
const writes = [];
const filtered = adapter.createFilteredStdoutWrite({{
  originalWrite: (value) => {{ writes.push(String(value)); return true; }},
}});
filtered(JSON.stringify({{
  jsonrpc: '2.0',
  method: 'notifications/progress',
  params: {{ progressToken: 1, progress: 0.5 }},
}}) + '\\n');
console.log(JSON.stringify({{ writes }}));
"""

    result = _run_node_json(script)
    assert isinstance(result, dict)
    assert len(result["writes"]) == 1
    assert "notifications/progress" in result["writes"][0]


def test_prepare_provider_launch_preloads_both_adapters_without_mutating_inputs(
    tmp_path: Path,
) -> None:
    assert LIFECYCLE_PATH.is_file()
    lifecycle = importlib.import_module("kis_mcp.provider_lifecycle")
    target = tmp_path / "config.json"
    original_args = ["provider-entry.js", "--no-onboarding"]
    original_environment = {
        "NO_UPDATE_NOTIFIER": "1",
        "DC_FLAG_URL": "http://127.0.0.1:9/kis-mcp-offline",
    }

    prepared_args, prepared_environment = lifecycle.prepare_provider_launch(
        args=original_args,
        environment=original_environment,
        provider_state_file=str(target),
    )

    assert prepared_args[:4:2] == ["--require", "--require"]
    assert Path(prepared_args[1]).resolve() == ATOMIC_ADAPTER_PATH.resolve()
    assert Path(prepared_args[3]).resolve() == STARTUP_ADAPTER_PATH.resolve()
    assert prepared_args[4:] == original_args
    assert prepared_environment["KIS_MCP_PROVIDER_STATE_FILE"] == str(target)
    assert prepared_environment["KIS_MCP_PROVIDER_STARTUP_COMPAT"] == "1"
    assert (
        prepared_environment["KIS_MCP_PROVIDER_FLAG_URL"]
        == "http://127.0.0.1:9/kis-mcp-offline"
    )
    assert prepared_environment["NO_UPDATE_NOTIFIER"] == "1"
    assert original_args == ["provider-entry.js", "--no-onboarding"]
    assert original_environment == {
        "NO_UPDATE_NOTIFIER": "1",
        "DC_FLAG_URL": "http://127.0.0.1:9/kis-mcp-offline",
    }
