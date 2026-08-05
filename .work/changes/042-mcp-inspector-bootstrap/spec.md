# Change Specification: MCP Inspector Bootstrap

- **Change ID**: `042-mcp-inspector-bootstrap`
- **Status**: Approved for implementation
- **Risk Profile**: standard
- **Development level**: Medium

## Outcome

Install `@modelcontextprotocol/inspector@2.0.0` as pinned, recoverable, operator-supervised support tooling and provide a bounded launcher for inspecting either local kis-mcp instance.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, and the upstream Inspector `2.0.0` package contract.
- Owned paths: `settings/bootstrap/mcp-inspector.install.json`, `scripts/install-mcp-inspector.ps1`, `scripts/start-mcp-inspector.ps1`, `tests/bootstrap/test_mcp_inspector_install.py`, `docs/development/tools/mcp-inspector.md`, and `.work/changes/042-mcp-inspector-bootstrap/**`.
- Shared paths: none.
- Excluded paths: gateway registration, `src/kis_mcp/**`, `settings/kis-mcp.settings.json`, `SPEC.md`, `docs/OPERATIONS.md`, provider composition, policy, and active change paths.
- Dependencies: Node.js `>=22.19.0`, npm, the existing local kis-mcp HTTP instance settings, and operator-supervised external package retrieval during bootstrap only.
- Integration owner: none.

## Architecture

MCP Inspector is managed like AgentSys and agnix rather than mounted into the primary gateway. A JSON install contract pins package identity, version, managed paths, launcher entry point, local bind ports, and exposure state. The installer stages the npm package beneath `C:\Projects\.kis-mcp\temp`, verifies its identity and CLI entry point, runs a local help smoke, then activates it by moving any previous installation into recoverable quarantine. The launcher reads the selected kis-mcp instance from `settings/kis-mcp.settings.json`, binds Inspector to loopback, redirects Inspector state, logs, npm cache, and temporary files beneath `C:\Projects\.kis-mcp`, and starts a read-only ad-hoc session against that instance.

The package is not vendored, auto-updated, mounted as an MCP provider, or exposed as a Work tool. Installation network access is the explicit supervised bootstrap boundary already permitted by repository authority; ordinary launch performs no package installation.

## Requirements

- **REQ-001 — Exact dependency identity**: Install only `@modelcontextprotocol/inspector@2.0.0`; reject settings or installed metadata with any other package name or version. Use the published single-package v2 launcher entry point `clients/launcher/build/index.js`.
- **REQ-002 — Runtime prerequisite**: Require Node.js `>=22.19.0` and npm before staging or activation.
- **REQ-003 — Bounded state**: Install root, managed home, npm cache, temp, logs, and quarantine must resolve beneath `C:\Projects`; existing path ancestors must not traverse reparse points.
- **REQ-004 — Recoverable activation**: Install into a unique staging directory, verify package metadata and `--cli --help` smoke before activation, move any previous installation into quarantine, never use permanent deletion, and restore the previous installation if activation fails.
- **REQ-005 — Local launcher**: Accept exactly `operation` or `development`; resolve the target port from `settings/kis-mcp.settings.json`; require the selected instance to be configured; bind Inspector to `127.0.0.1`; use distinct configured Inspector web ports; and launch an ad-hoc streamable-HTTP session for `http://127.0.0.1:<instance-port>/mcp`.
- **REQ-006 — No new gateway or policy surface**: Keep `kis_mcp_exposure.enabled` false, add no public gateway tool, provider, policy decision, command denylist, network resolver, credential behavior, or automatic startup.
- **REQ-007 — Truthful status and operation**: Write bounded installation status with package version, paths, launcher, and activation evidence; provide clear corrective errors for missing prerequisites, missing installation, invalid settings, unavailable instance configuration, and port conflicts surfaced by Inspector.
- **REQ-008 — Verification**: Add structural tests for settings, installer safety and ordering, launcher target resolution and environment containment, then pass focused tests, change-workflow checks, and the full repository verification suite.

## Acceptance

1. **Given** a supported Node/npm environment and no prior install, **when** the installer runs, **then** Inspector `2.0.0` is staged, verified, smoke-tested, and activated beneath `C:\Projects\.kis-mcp\tools\mcp-inspector\2.0.0`.
2. **Given** an existing managed install, **when** replacement succeeds, **then** the prior install is preserved under the configured quarantine root and the new install becomes active without permanent deletion.
3. **Given** invalid package identity, insufficient Node version, a missing launcher, or a failed smoke, **when** installation runs, **then** activation does not replace the current installation.
4. **Given** `-Instance development`, **when** the launcher runs, **then** it reads the development HTTP port from kis-mcp settings, binds Inspector on its configured development Inspector port, and targets the local `/mcp` endpoint.
5. **Given** either launcher or installer execution, **when** paths and environment are resolved, **then** every project-controlled write target remains beneath `C:\Projects`.
6. **Given** repository verification, **when** the change is checked, **then** no source gateway, provider, policy, or unrelated active-change path is modified.

## Risks and recovery

- **Risk — Upstream process-spawning UI**: Inspector can connect to MCP servers and can launch stdio commands when configured by an operator. This slice supplies only an ad-hoc local HTTP target and does not expose Inspector through Work.
- **Risk — External package retrieval**: npm installation uses external network access. It occurs only through the explicit operator-supervised bootstrap command and never during normal gateway execution.
- **Risk — Local port collision**: Inspector exits with its upstream corrective error when the configured local UI port is occupied; no process is terminated automatically.
- **Risk — Replacement failure**: Activation uses move-based quarantine and rollback. Failed staged content remains recoverable beneath the configured temp or quarantine root.
- **Recovery**: Re-run the installer, restore the quarantined previous package manually, or revert the branch/merge. No repository or managed artifact is permanently deleted.

## Out of scope

- Mounting Inspector into the kis-mcp gateway or Tools registry.
- Allowing arbitrary remote server URLs through a public Work operation.
- Vendoring or modifying Inspector source.
- Browser automation, CI screenshot testing, OAuth commissioning, or exposing CLI/TUI wrappers.
- Changing kis-mcp instance ports, tunnel configuration, provider authentication, `SPEC.md`, or `docs/OPERATIONS.md` while change `041-dual-instance-commissioning` owns those paths.
