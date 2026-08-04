from __future__ import annotations

import importlib
import json
import os
import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "kis_mcp"
ADAPTER_PATH = PACKAGE_ROOT / "provider_state_atomic.cjs"
LIFECYCLE_PATH = PACKAGE_ROOT / "provider_lifecycle.py"


def _run_node_json(script: str) -> object:
    environment = dict(os.environ)
    environment.pop("KIS_MCP_PROVIDER_STATE_FILE", None)
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
    assert ADAPTER_PATH.is_file()
    target = tmp_path / "config.json"
    other = tmp_path / "other.json"
    script = f"""
const adapter = require({json.dumps(str(ADAPTER_PATH))});

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


def test_prepare_provider_launch_preloads_adapter_without_mutating_inputs(
    tmp_path: Path,
) -> None:
    assert LIFECYCLE_PATH.is_file()
    lifecycle = importlib.import_module("kis_mcp.provider_lifecycle")
    target = tmp_path / "config.json"
    original_args = ["provider-entry.js", "--no-onboarding"]
    original_environment = {"NO_UPDATE_NOTIFIER": "1"}

    prepared_args, prepared_environment = lifecycle.prepare_provider_launch(
        args=original_args,
        environment=original_environment,
        provider_state_file=str(target),
    )

    assert prepared_args[0] == "--require"
    assert Path(prepared_args[1]).resolve() == ADAPTER_PATH.resolve()
    assert prepared_args[2:] == original_args
    assert prepared_environment["KIS_MCP_PROVIDER_STATE_FILE"] == str(target)
    assert prepared_environment["NO_UPDATE_NOTIFIER"] == "1"
    assert original_args == ["provider-entry.js", "--no-onboarding"]
    assert original_environment == {"NO_UPDATE_NOTIFIER": "1"}
