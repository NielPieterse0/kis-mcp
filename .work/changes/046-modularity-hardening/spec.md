# Change Specification: Modularity Hardening

- **Change ID**: `046-modularity-hardening`
- **Status**: Approved
- **Risk Profile**: rigorous
- **Development level**: Complex

## Outcome

Close the current, directly evidenced modularity boundary violations that can be changed without overlapping active worktrees. Preserve runtime behavior while correcting dependency direction, isolating Control Center storage knowledge behind read-only adapters, removing provider-to-application smoke dependencies, and retiring the stale root provider registry alias.

## Authority and scope

Authoritative sources, in order:

1. `AGENTS.md`
2. `docs/TRUST-MODEL.md`
3. `SPEC.md`
4. `docs/PLATFORM-CONCEPT.md`
5. `policy/kis-mcp.policy.json`
6. The operator-approved modularity assessment supplied for this slice

The exact owned and excluded paths are declared in `scope.json`. This change must not edit `src/kis_mcp/server.py`, `src/kis_mcp/tools/__init__.py`, `settings/kis-mcp.settings.json`, or `src/kis_mcp/discover/**`.

Current evidence on `main` at `cd19e86`:

- NVIDIA provider and Codex tool modules import settings from `workflows.code_review.settings`, reversing the required dependency direction.
- `providers.platform` imports both `NvidiaSettings` and the workflow settings loader.
- NVIDIA capability metadata names the workflow-specific `review_change_with_agent` tool.
- `control_center.snapshot` directly interprets runtime, policy, provider, quarantine, and Git storage/command layouts.
- GitHub and Supabase provider smoke modules import `kis_mcp.server.build_server`.
- `src/kis_mcp/provider_registry.py` remains a five-line compatibility alias with no production consumers.
- The generic Tools foundation is present on current `main`; the assessment's missing-029 finding is closed.
- `src/kis_mcp/server.py` is exclusively owned by active change `040-context7-serena-adapters`; code-review composition extraction is therefore deferred to a coordinated post-040 slice.

## Requirements

### R1 — Provider and tool settings ownership

- `providers/nvidia/settings.py` owns `NvidiaSettings`, NVIDIA-specific validation, mapping conversion, and a deterministic disabled default.
- `tools/codex_cli/settings.py` owns `CodexSettings`, Codex-specific validation, repository-bounded script resolution, and a deterministic disabled default.
- NVIDIA provider/client modules and Codex adapter/tool modules import only their module-owned settings.
- `providers.platform` must not import `workflows.code_review`.

### R2 — Workflow composition direction

- `workflows/code_review/settings.py` owns only workflow selection, budgets, the aggregate `AgentSettings`, and loading of the single workflow JSON document.
- The workflow loader composes provider-owned and tool-owned settings and converts module-specific validation failures to `AgentSettingsError`.
- Existing checked-in settings behavior and safe-disabled fallback behavior remain unchanged.

### R3 — Provider-native capability declaration

- NVIDIA continues to declare `llm.inference.nvidia-nim` with external-network effects.
- NVIDIA capability metadata must not claim ownership of the workflow-specific `review_change_with_agent` tool.

### R4 — Stable Control Center read seams

- Add focused read-only adapters named `RuntimeStatusReader`, `PolicyStatusReader`, `ProviderStatusReader`, `QuarantineStatusReader`, and `GitStatusReader` under `control_center`.
- `ControlCenterSnapshotService` orchestrates these adapters and no longer parses those raw documents or quarantine directories itself.
- Runtime, policy, and provider JSON readers require integer `schema_version == 1` before interpreting fields.
- Quarantine metadata requires the current quarantine schema version and validates the bounded fields needed by the dashboard.
- Invalid, missing, oversized, or unavailable evidence degrades only the affected dashboard section and produces existing-style diagnostics.
- Existing bounded limits, Git environment isolation, and unknown-state behavior remain intact.

### R5 — Provider-local smoke independence

- GitHub and Supabase provider smoke modules accept an application server or server factory from the caller and do not import `kis_mcp.server`.
- Application-level construction moves to one script under `scripts/` used by both provider smoke PowerShell entry points.
- Existing OAuth/PAT conflict checks, project scope checks, mount checks, commissioning behavior, and JSON report shapes remain unchanged.

### R6 — Retire stale compatibility alias

- Remove `src/kis_mcp/provider_registry.py`.
- Tests and internal imports use `kis_mcp.providers` directly.
- Add a regression check proving no tracked Python source imports the retired root module.

### R7 — Boundary regression tests

Add architecture tests that fail when:

- provider or tool packages import the code-review workflow;
- provider smoke modules import the application server;
- the retired root provider registry module returns;
- Control Center snapshot code directly reads the canonical runtime, policy, provider, or quarantine JSON layouts.

## Acceptance

1. **Given** the NVIDIA provider and Codex tool packages, **when** imports are inspected, **then** neither package imports `kis_mcp.workflows.code_review`.
2. **Given** platform provider composition with no explicit NVIDIA settings, **when** the registry is built, **then** NVIDIA uses its provider-owned disabled default without loading workflow configuration.
3. **Given** valid code-review agent JSON, **when** settings are loaded, **then** the aggregate values match the existing behavior and module-specific settings types come from their owning packages.
4. **Given** malformed module-specific settings, **when** the workflow document is loaded, **then** the caller receives `AgentSettingsError` with bounded diagnostics.
5. **Given** Control Center evidence documents without or with unsupported schema versions, **when** a snapshot is collected, **then** only the affected section becomes unavailable or invalid and a specific diagnostic is emitted.
6. **Given** valid Control Center evidence, **when** a snapshot is collected, **then** existing runtime, policy, provider, Git, quarantine, and limit assertions remain true.
7. **Given** provider live-smoke code, **when** imports are inspected, **then** GitHub and Supabase provider packages do not import `kis_mcp.server`; the application script supplies the server.
8. **Given** the repository source tree, **when** architecture tests run, **then** the stale root provider registry alias is absent and no internal source imports it.
9. The change-governance check, focused tests, and `scripts/verify.ps1` pass on the final branch state.

## Risks and recovery

- **Risk:** Moving settings types can break imports or optional startup behavior. **Mitigation:** test old aggregate loading, disabled defaults, explicit platform composition, and import boundaries before implementation.
- **Risk:** Control Center adapter extraction can change degraded-state diagnostics or bounded counts. **Mitigation:** preserve contract objects and existing assertions, then add schema-drift tests.
- **Risk:** Smoke entry-point changes can break supervised commissioning scripts. **Mitigation:** preserve PowerShell output fields and add static script plus injected-server tests.
- **Risk:** Removing the alias can break an unobserved consumer. **Mitigation:** repository-wide search and architecture test; recovery is a one-file re-export restoration from Git history.
- **Recovery:** revert the change commit or PR merge. No data migration, policy change, credential change, or persistent-state mutation is introduced.

## Out of scope and deferred

- Editing `server.py` or extracting code-review/Discover registration while change `040` owns that file.
- Big-bang root-package migration or Desktop Commander package consolidation.
- Big-bang Discover reorganization; Discover remains an incremental feature-slice migration.
- Changing HR-001, HR-002, HR-003, provider exposure, network policy, authentication, secrets, installation, or runtime settings files.
- Adding a dynamic plugin framework or new dependencies.
