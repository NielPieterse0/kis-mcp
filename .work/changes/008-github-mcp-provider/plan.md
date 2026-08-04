# GitHub MCP Provider Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for each behavior task and superpowers:verification-before-completion before closeout. Execute inline in `C:\Projects\kis-mcp\.work\worktrees\008-github-mcp-provider` because the operator requested implementation in this session.

**Goal:** Add an isolated, settings-driven provider module for the official GitHub MCP server with token indirection, approved private-repository scoping, readiness, registry metadata, operator bootstrap, and smoke verification.

**Architecture:** A dedicated provider JSON is parsed into immutable settings. `GitHubRepositoryScopeMiddleware` validates explicit repository identities while preserving the official tool catalogue. `build_github_provider_server()` creates an official stdio proxy and adds a redacted health tool. `ProviderRegistry` records the provider without modifying the active Desktop Commander/Discover composition roots.

**Tech Stack:** Python 3.11+, FastMCP 3.4.4, standard library, JSON Schema draft 2020-12, pytest 8.4, PowerShell 7.

## Global Constraints

- Write only within the declared `008-github-mcp-provider` owned paths.
- Do not modify Discover, remote commissioning, main runtime settings/configuration, main server composition, policy, middleware, Desktop Commander, or quarantine.
- Do not store or print credential values.
- Use the official provider; do not reimplement GitHub APIs or tool contracts.
- Treat provider network access as an approved connector boundary outside Desktop Commander Work.
- Keep all configuration in JSON.
- Use failing focused tests before implementation and preserve red/green evidence in `tasks.md`.

---

### Task 1: Provider settings and portable schema

**Files:**
- Create: `settings/providers/github-mcp.provider.json`
- Create: `contracts/providers/github/provider-settings.schema.json`
- Create: `src/kis_mcp/providers/github/settings.py`
- Create: `src/kis_mcp/providers/github/__init__.py`
- Test: `tests/providers/github/test_settings.py`
- Test: `tests/providers/github/test_schema.py`

**Interfaces:**
- Produces: `GitHubProviderSettings`, `load_github_provider_settings(repository_root: Path | None = None) -> GitHubProviderSettings`
- Produces properties: `provider_id`, `source_revision`, `executable`, `token_env`, `toolsets`, `approved_repositories`, `unscoped_tools`, `launch_args()`

- [x] Write failing tests for exact keys, official source, 40-character revision, executable beneath `C:\Projects`, non-secret token environment name, non-empty toolsets, normalized unique repositories, and unknown-key rejection.
- [x] Run `python -m pytest tests/providers/github/test_settings.py tests/providers/github/test_schema.py -q`; expect import/config failures.
- [x] Implement immutable settings parsing and schema.
- [x] Rerun focused tests; expect pass.

### Task 2: Repository identity and scope middleware

**Files:**
- Create: `src/kis_mcp/providers/github/scope.py`
- Test: `tests/providers/github/test_scope.py`

**Interfaces:**
- Produces: `normalize_repository(value: str) -> str`
- Produces: `GitHubRepositoryScope(approved_repositories: Sequence[str], unscoped_tools: Sequence[str])`
- Produces: `authorize(tool_name: str, arguments: Mapping[str, Any]) -> None`
- Produces: `GitHubRepositoryScopeMiddleware(Middleware)`

- [x] Write failing normalization tests for `owner/repo`, `.git`, GitHub HTTPS/API/SSH URLs, case normalization, malformed values, and credential-bearing URLs.
- [x] Write failing authorization tests for `owner`+`repo`, `repository`, `repo`, `repo_full_name`, repository URLs, lists, conflicting targets, qualified searches, unqualified searches, approved identity tools, and unknown unscoped tools.
- [x] Run focused scope tests; expect missing implementation failures.
- [x] Implement recursive explicit-target extraction and corrective `GITHUB_REPOSITORY_SCOPE` errors without modifying tool listings.
- [x] Rerun focused tests; expect pass.

### Task 3: Provider registry, launch construction, server, and health

**Files:**
- Create: `src/kis_mcp/provider_registry.py`
- Create: `src/kis_mcp/providers/github/server.py`
- Create: `src/kis_mcp/providers/github/__main__.py`
- Test: `tests/providers/github/test_registry.py`
- Test: `tests/providers/github/test_server.py`
- Test: `tests/providers/github/test_architecture.py`

**Interfaces:**
- Produces: `ProviderDescriptor`, `ProviderRegistry.register()`, `ProviderRegistry.get()`, `ProviderRegistry.list()`
- Produces: `GitHubProviderHealth`
- Produces: `github_provider_environment(settings, environ=None) -> dict[str, str]`
- Produces: `build_github_provider_server(settings=None, *, environ=None, validate_executable=True) -> FastMCP`
- Produces: `register_github_provider(registry, settings=None) -> ProviderDescriptor`

- [x] Write failing registry tests for unique IDs, immutable descriptors, deterministic listing, and duplicate rejection.
- [x] Write failing launch tests proving exact official `stdio` arguments, token forwarding without logging, no inherited arbitrary environment, executable validation, health redaction, middleware installation, and registry registration.
- [x] Write failing architecture tests prohibiting imports from Discover, policy, quarantine, Desktop Commander, main middleware, and remote runtime.
- [x] Run focused registry/server tests; expect missing implementation failures.
- [x] Implement the minimal registry and provider server using `StdioTransport`, `ProxyClient`, and `create_proxy`.
- [x] Rerun focused tests; expect pass.

### Task 4: Operator bootstrap, smoke script, and operational documentation

**Files:**
- Create: `src/kis_mcp/providers/github/smoke.py`
- Create: `scripts/install-github-mcp.ps1`
- Create: `scripts/smoke-github-mcp.ps1`
- Create: `docs/development/github-mcp-provider/README.md`
- Test: `tests/providers/github/test_live_smoke.py`
- Test: `tests/providers/github/test_scripts.py`

**Interfaces:**
- Install parameters: `-SourceBinary`, `-ExpectedSha256`, optional `-Destination`
- Smoke parameters: optional `-RepositoryRoot`, `-RequireLive`

- [x] Write failing script-content tests requiring strict mode, no implicit download, SHA-256 verification, destination beneath `C:\Projects\.kis-mcp\github-mcp`, no token output, and bounded smoke behavior.
- [x] Run focused script tests; expect missing files.
- [x] Implement the scripts and operator documentation, including fine-grained token/App repository scoping and separate ChatGPT MCP endpoint configuration.
- [x] Rerun focused script tests; expect pass.

### Task 5: Review, verification, closeout, and draft PR

**Files:**
- Modify: `.work/changes/008-github-mcp-provider/tasks.md`
- Modify: `.work/changes/008-github-mcp-provider/closeout.md`
- Create: `docs/development/github-mcp-provider/verification.md`

- [x] Run `python -m pytest tests/providers/github -q`.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 validate` and record the pre-existing duplicate-claim blocker if still present.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` and record the same blocker if applicable.
- [x] Run `pwsh -NoProfile -File scripts/verify.ps1`.
- [x] Run `git diff --check`, inspect status/diff, and confirm only owned paths changed.
- [x] Review requirements, secrets, authorization, error handling, upgrade/rollback, and current implementation claims.
- [x] Commit, push `change/008-github-mcp-provider`, and open a draft PR without merging.
