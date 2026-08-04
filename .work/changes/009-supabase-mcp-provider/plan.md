# Supabase MCP Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independently executable, project-scoped proxy for the official hosted Supabase MCP server and conform it to the shared Provider foundation without changing Work policy or the provider-neutral core.

**Architecture:** A strict JSON loader produces an immutable `SupabaseProviderConfig`. Pure helpers construct the official upstream URL and redacted readiness. A FastMCP `StreamableHttpTransport` with bearer authentication is wrapped by `create_proxy`, and a small CLI exposes stdio runtime plus non-network `--check` output.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4, pytest 8.4+, JSON Schema draft 2020-12, PowerShell 7.

## Global Constraints

- Write only within the owned paths in `scope.json`.
- Do not store or print access-token or project-reference values.
- Do not add a custom Supabase tool-name allowlist.
- Default to project-scoped read/write operation (`read_only=false`).
- Do not edit the provider-neutral core, Discover, Desktop Commander Work, remote runtime, global settings/config/server, policy, or quarantine.
- Use source revision `5cda0672702c65fe672280ee4cf306593e643fb6` as reviewed upstream evidence.

---

### Task 1: Strict provider configuration and schema

**Files:**
- Create: `settings/providers/supabase-mcp.provider.json`
- Create: `contracts/providers/supabase/settings.schema.json`
- Create: `src/kis_mcp/providers/supabase/__init__.py`
- Create: `src/kis_mcp/providers/supabase/config.py`
- Create: `tests/providers/supabase/test_supabase_config.py`

**Interfaces:**
- Produces: `SupabaseProviderConfig`, `SupabaseProviderConfigError`, `load_supabase_provider_config(repository_root: Path | None = None) -> SupabaseProviderConfig`.
- Configuration properties: `provider_id`, `server_name`, `source_repository`, `source_revision`, `base_url`, `project_ref_env`, `access_token_env`, `read_only`, `features`, `verify_tls`, `downstream_transport`.

- [x] **Step 1: Write failing strict-loader tests**

```python
def test_loads_checked_in_provider_configuration() -> None:
    config = load_supabase_provider_config(REPOSITORY_ROOT)
    assert config.provider_id == "supabase"
    assert config.read_only is False
    assert config.features == ()


def test_rejects_unknown_root_key(tmp_path: Path) -> None:
    path = write_config(tmp_path, extra={"secret": "forbidden"})
    with pytest.raises(SupabaseProviderConfigError, match="unknown keys"):
        load_supabase_provider_config(tmp_path)
```

- [x] **Step 2: Run the focused tests and confirm RED**

Run: `python -m pytest tests/providers/supabase/test_supabase_config.py -q`
Expected: collection/import failure because the module does not exist.

- [x] **Step 3: Add the checked-in JSON, JSON Schema, immutable dataclass, and exact-key validation**

```python
@dataclass(frozen=True, slots=True)
class SupabaseProviderConfig:
    provider_id: str
    server_name: str
    source_repository: str
    source_revision: str
    base_url: str
    project_ref_env: str
    access_token_env: str
    read_only: bool
    features: tuple[str, ...]
    verify_tls: bool
    downstream_transport: str
```

Validation must reject embedded credential keys/values, invalid environment-variable names, arbitrary external hosts, duplicate features, wrong types, and unknown keys.

- [x] **Step 4: Run focused tests and confirm GREEN**

Run: `python -m pytest tests/providers/supabase/test_supabase_config.py -q`
Expected: all tests pass.

### Task 2: URL construction and redacted readiness

**Files:**
- Create: `src/kis_mcp/providers/supabase/runtime.py`
- Create: `tests/providers/supabase/test_supabase_runtime.py`

**Interfaces:**
- Consumes: `SupabaseProviderConfig`.
- Produces: `SupabaseProviderReadiness`, `build_upstream_url(config, environment) -> str`, `provider_readiness(config, environment) -> SupabaseProviderReadiness`, `require_runtime_credentials(config, environment) -> tuple[str, str]`.

- [x] **Step 1: Write failing URL and redaction tests**

```python
def test_default_url_is_project_scoped_read_write() -> None:
    url = build_upstream_url(CONFIG, ENVIRONMENT)
    assert "project_ref=test-project" in url
    assert "read_only" not in url
    assert "features" not in url


def test_readiness_does_not_expose_runtime_values() -> None:
    result = provider_readiness(CONFIG, ENVIRONMENT).as_dict()
    rendered = json.dumps(result)
    assert "test-token" not in rendered
    assert "test-project" not in rendered
```

- [x] **Step 2: Run focused tests and confirm RED**

Run: `python -m pytest tests/providers/supabase/test_supabase_runtime.py -q`
Expected: import failure because runtime helpers do not exist.

- [x] **Step 3: Implement URL encoding, credential checks, and redacted readiness**

```python
def build_upstream_url(config: SupabaseProviderConfig, environment: Mapping[str, str]) -> str:
    project_ref, _ = require_runtime_credentials(config, environment)
    query = {"project_ref": project_ref}
    if config.read_only:
        query["read_only"] = "true"
    if config.features:
        query["features"] = ",".join(config.features)
    return f"{config.base_url}?{urlencode(query)}"
```

Readiness must contain booleans for token/project-ref presence, never their values.

- [x] **Step 4: Run focused tests and confirm GREEN**

Run: `python -m pytest tests/providers/supabase/test_supabase_runtime.py -q`
Expected: all tests pass.

### Task 3: FastMCP proxy and standalone CLI

**Files:**
- Create: `src/kis_mcp/providers/supabase/server.py`
- Create: `src/kis_mcp/providers/supabase/__main__.py`
- Create: `tests/providers/supabase/test_supabase_server.py`
- Create: `tests/providers/supabase/test_supabase_cli.py`

**Interfaces:**
- Consumes: config and runtime helpers.
- Produces: `build_transport(config, environment) -> StreamableHttpTransport`, `build_server(config=None, environment=None) -> FastMCP`, `main(argv: Sequence[str] | None = None) -> int`.

- [x] **Step 1: Write failing transport, server, and CLI tests**

```python
def test_transport_uses_bearer_auth_without_exposing_token(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr(server_module, "StreamableHttpTransport", capture_transport(captured))
    build_transport(CONFIG, ENVIRONMENT)
    assert captured["url"].startswith("https://mcp.supabase.com/mcp?")
    assert captured["auth"] == "test-token"


def test_check_mode_is_non_network_and_redacted(capsys) -> None:
    assert main(["--check"]) == 0
    output = capsys.readouterr().out
    assert "access_token" not in output
```

- [x] **Step 2: Run focused tests and confirm RED**

Run: `python -m pytest tests/providers/supabase/test_supabase_server.py tests/providers/supabase/test_supabase_cli.py -q`
Expected: import failure because server/CLI modules do not exist.

- [x] **Step 3: Implement transport, proxy, health tool, and CLI**

```python
transport = StreamableHttpTransport(
    url=build_upstream_url(config, environment),
    auth=access_token,
    verify=config.verify_tls,
)
server = create_proxy(ProxyClient(transport), name=config.server_name)
```

Register `kis_supabase_health` on the proxy. `--check` loads config and prints readiness JSON without constructing a transport. Normal mode requires credentials and runs the configured stdio transport.

- [x] **Step 4: Run focused tests and confirm GREEN**

Run: `python -m pytest tests/providers/supabase/test_supabase_server.py tests/providers/supabase/test_supabase_cli.py -q`
Expected: all tests pass without external network access.

### Task 4: Smoke workflow, documentation, scope review, and complete verification

**Files:**
- Create: `scripts/smoke-supabase-mcp.ps1`
- Create: `docs/development/supabase-mcp-provider/README.md`
- Create: `tests/providers/supabase/test_supabase_artifacts.py`
- Update: `.work/changes/009-supabase-mcp-provider/tasks.md`
- Update: `.work/changes/009-supabase-mcp-provider/closeout.md`

**Interfaces:**
- Smoke script invokes the exact project interpreter with `-m kis_mcp.providers.supabase --check`. Live authentication and tool listing are explicitly deferred until operator credentials are supplied.

- [x] **Step 1: Write failing artifact and boundary tests**

```python
def test_smoke_script_uses_exact_project_interpreter() -> None:
    text = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert ".kis-mcp\\python-env\\Scripts\\python.exe" in text
    assert "--check" in text


def test_slice_does_not_modify_excluded_paths() -> None:
    assert excluded_paths_are_unchanged()
```

- [x] **Step 2: Run focused tests and confirm RED**

Run: `python -m pytest tests/providers/supabase/test_supabase_artifacts.py -q`
Expected: failure because smoke/documentation artifacts do not exist.

- [x] **Step 3: Implement smoke script and concise operator documentation**

Document environment variables, development/test-only use, project scoping, read/write default, non-network `--check`, deferred live verification, credential rotation, and removal/recovery.

- [x] **Step 4: Run focused provider tests**

Run: `python -m pytest tests/providers/supabase -q`
Expected: all provider tests pass.

- [x] **Step 5: Run repository scope and full verification**

Run: `pwsh -File scripts/change-workflow.ps1 check`
Expected: exit code 0 with every changed path inside the declared adapter scope.

Run: `pwsh -File scripts/verify.ps1`
Expected: exit code 0 and complete test suite pass.

- [x] **Step 6: Review final diff against all requirements**

Confirm every changed path is owned, no credential values exist, no excluded path changed, no custom tool allowlist exists, and all requirements map to tests or documentation.

- [x] **Step 7: Commit and push the branch**

```powershell
git add .work/changes/009-supabase-mcp-provider src/kis_mcp/providers/supabase settings/providers/supabase-mcp.provider.json contracts/providers/supabase tests/providers/supabase scripts/smoke-supabase-mcp.ps1 docs/development/supabase-mcp-provider
git commit -m "feat: add Supabase MCP provider"
git push -u origin change/009-supabase-mcp-provider
```

- [x] **Step 8: Create a draft pull request without merging**

Create a draft PR targeting `main` with implementation, verification, security boundary, and remaining live-auth limitation clearly stated.

### Task 5: Conform to the merged shared Provider foundation

**Files:**
- Update: `src/kis_mcp/providers/supabase/__init__.py`
- Update: `src/kis_mcp/providers/supabase/server.py`
- Update: `tests/providers/supabase/test_supabase_server.py`
- Update: provider documentation and change artifacts.

- [x] **Step 1: Merge current `main` containing the shared Provider foundation and integrated GitHub adapter into the branch without rewriting history.**
- [x] **Step 2: Write failing tests for the canonical descriptor, provider-neutral readiness, explicit registration, and package exports.**
- [x] **Step 3: Replace the private descriptor with shared Provider contracts and keep registration explicit and non-networked.**
- [x] **Step 4: Confirm FastMCP bearer-token handling and current official Supabase endpoint, query parameters, and manual PAT authentication.**
- [x] **Step 5: Run scope check, non-network smoke, complete repository verification, and final diff review.**
- [x] **Step 6: Commit the conformance repair as `4454506` and update the PR evidence before landing.**
