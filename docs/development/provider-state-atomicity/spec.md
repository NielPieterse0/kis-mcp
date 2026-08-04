# Change Specification: Provider State Atomicity

- **Change ID**: `006-provider-state-atomicity`
- **Status**: Approved for implementation
- **Development level**: Complex
- **Risk profile**: rigorous

## Outcome

Prevent Desktop Commander `0.2.46` from leaving its configured `config.json` truncated when the stdio provider process is stopped while a background usage-statistics save is in progress.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `settings/kis-mcp.settings.json`, and the reproduced PR #3 commissioning failure.
- Owned paths: `.work/changes/006-provider-state-atomicity/**`, `docs/development/provider-state-atomicity/**`, `src/kis_mcp/provider_lifecycle.py`, `src/kis_mcp/provider_state_atomic.cjs`, and `tests/test_provider_lifecycle.py`.
- Shared path: `src/kis_mcp/server.py`, coordinated through integration owner `005-discover-foundation`.
- Excluded paths: PR #3 commissioning files, Discover implementation files, provider installation contents, runtime settings, policy, and Desktop Commander source.
- Runtime dependency: the pinned local Node.js process already used to start Desktop Commander.

## Root cause

Desktop Commander records usage statistics after tool calls through a non-blocking `fs/promises.writeFile` operation. `writeFile` may truncate the existing state file before all replacement bytes are written. FastMCP and MCP stdio shutdown close stdin and may terminate the Node process before that background write completes, leaving the shared file at zero bytes.

The provider serializes concurrent writes but does not make an individual replacement interruption-safe.

## Requirements

- **REQ-001 — Narrow target**: Atomic replacement MUST apply only to the exact provider state path supplied by `RuntimeConfig.provider_state_file`.
- **REQ-002 — No provider fork**: The authoritative Desktop Commander package and installed provider files MUST remain unchanged.
- **REQ-003 — Preserve behavior**: Provider tools, schemas, policy decisions, configuration values, and ordinary writes MUST remain unchanged.
- **REQ-004 — Atomic replacement**: A targeted provider-state write MUST write complete content to a unique same-directory temporary file before renaming it over the configured state file.
- **REQ-005 — Interruption safety**: If the process exits before rename, the last valid state file MUST remain intact. An incomplete temporary file MAY remain as recoverable generated state.
- **REQ-006 — Launch integration**: The gateway MUST preload the compatibility adapter before the Desktop Commander ESM entry point and MUST provide the configured target through a process environment value.
- **REQ-007 — No new restrictions**: The change MUST NOT add a policy rule, command block, tool restriction, network restriction, approval gate, or hard-coded machine path.
- **REQ-008 — Evidence**: Unit tests MUST cover launch shaping, exact-path targeting, non-target passthrough, and temp-write-then-rename ordering. The PR #3 live commissioning harness MUST pass against this branch without snapshot restoration.

## Design

Add a small Python launch helper that derives the bundled CommonJS preload adapter path, inserts Node's `--require` option before the existing provider entry point, and adds the configured provider state path to the provider environment.

The preload adapter patches only `fs/promises.writeFile`. Non-target writes call the original function unchanged. A target write calls the original function on a unique temporary path in the same directory, then calls the original `rename` to atomically replace the target. The adapter is loaded into the provider process only; it does not alter FastMCP, Python file operations, or Desktop Commander's installed package.

## Acceptance

1. **Given** an existing valid provider state file, **when** the adapter begins a targeted write but the process stops before rename, **then** the existing state file is not truncated or replaced.
2. **Given** a completed targeted write, **when** rename succeeds, **then** the configured state path contains the complete new content.
3. **Given** a write to any other path, **when** Desktop Commander calls `fs/promises.writeFile`, **then** the original write operation receives the original path and arguments.
4. **Given** the current gateway launch configuration, **when** `build_server()` creates the provider transport, **then** Node preloads the bundled adapter and receives `KIS_MCP_PROVIDER_STATE_FILE` from runtime configuration.
5. **Given** PR #3's live commissioning sequence, **when** it runs against this branch, **then** every functional stage passes and provider state remains valid without automatic restoration.
6. **Given** the final diff, **when** scope and policy are reviewed, **then** no provider source, settings, policy, Discover files, or PR #3 commissioning files are changed.

## Risks and recovery

- Risk: Node preload behavior could fail to affect the ESM default import used by Desktop Commander. Mitigation: run the real live commissioning harness against this branch.
- Risk: a failed rename can leave a temporary file. This is recoverable generated state and does not damage the last valid configuration.
- Risk: `src/kis_mcp/server.py` is shared with Discover. Coordination is explicit through `005-discover-foundation`; integration must preserve both changes.
- Recovery: revert the branch commit. The installed Desktop Commander package and existing provider state remain untouched by repository rollback.

## Out of scope

- Reusing a persistent provider process across gateway sessions.
- Modifying or vendoring Desktop Commander.
- Disabling usage statistics or provider configuration persistence.
- Adding a provider service, lock daemon, cleanup daemon, retry system, or new configuration setting.
- Changing PR #3's commissioning harness in this slice.
