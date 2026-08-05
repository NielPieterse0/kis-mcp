# Change Specification: Tools Foundation

- **Change ID**: `029-tools-code-tooling`
- **Status**: Approved for implementation
- **Risk Profile**: standard
- **Development level**: Medium

## Outcome

Create the provider-neutral `kis_mcp.tools` foundation required by later tool adapters. This slice contains no Context7, Serena, Codex, installer, provider, gateway, network, credential, or policy behavior.

## Authority and coordination

- Repository authority remains `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, and `docs/PLATFORM-CONCEPT.md`.
- The operator directed 029 to own the generic Tools framework and directed `035-llm-capability` to depend on it.
- `src/kis_mcp/tools/codex_cli/**` and `tests/tools/codex_cli/**` are explicitly excluded and owned by 035 after this change merges.
- Context7 and Serena adapters are deferred to separate approval-backed changes. Their restrictions are not decided here.

## Architecture

The module mirrors the established provider-neutral registry pattern without coupling Tools to Providers:

- `contracts.py` defines immutable versioned tool identity, capability, descriptor, readiness, kind, boundary, and state contracts.
- `registry.py` provides deterministic registration and lookup.
- `catalogue.py` projects immutable metadata without constructing tools.
- `health.py` contains readiness probe failures and aggregates deterministic health.
- `service.py` exposes a thin facade for catalogue, capability lookup, health, and explicit construction.
- `__init__.py` exports the public module contract.

## Requirements

- **REQ-001**: Public contracts use schema version `1`, immutable dataclasses, lower-case kebab-case tool IDs, typed enums, deterministic ordering, and JSON-safe serialization.
- **REQ-002**: Duplicate tool IDs and duplicate capability IDs fail structurally.
- **REQ-003**: Catalogue and health operations never construct a tool.
- **REQ-004**: Disabled tools are not readiness-probed.
- **REQ-005**: Probe exceptions, malformed results, and identity mismatches become redacted unavailable readiness results.
- **REQ-006**: `ToolService.build(tool_id)` is the only generic operation that invokes a descriptor builder.
- **REQ-007**: The module adds no settings, installation, network operation, runtime auto-start, credential behavior, public MCP tool, or policy rule.
- **REQ-008**: The implementation remains independent of provider internals and does not import `kis_mcp.providers`.

## Acceptance criteria

1. Tool descriptors and readiness serialize deterministically to JSON-safe dictionaries.
2. Registry listing is stable by tool ID and rejects duplicate identities.
3. Catalogue capability lookup performs no construction.
4. Health aggregation reports ready, degraded, disabled, and unavailable states while containing failures.
5. Service construction is explicit and delegates only to the selected descriptor builder.
6. Focused tests, architecture checks, change-workflow checks, and full repository verification pass.
7. The change merges before 035 resumes Codex integration.

## Exclusions

- Context7 and Serena implementation or restriction decisions.
- Codex CLI files or tests.
- NVIDIA providers, agent workflows, gateway integration, settings, contracts, scripts, and documentation.
- Changes to `SPEC.md`, `docs/OPERATIONS.md`, policy, quarantine, or Desktop Commander.

## Recovery

The slice is isolated in its worktree. Recovery is branch reversion or ordinary Git rollback; no external state, installation, credential, or migration is created.
