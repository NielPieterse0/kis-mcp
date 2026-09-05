# Non-Hard Controls and Resolver Boundaries

## Purpose

This document records implementation behavior that is intentionally excluded from `docs/HARD-BLOCK-APPROVAL-REGISTER.md` because it is not an active HR-001, HR-002, or HR-003 hard-block decision.

It is descriptive engineering and operations documentation. It does not create policy and does not require item-by-item hard-block approval.

## Resolver and coverage behavior

### Known command contracts

Only supported command contracts are parsed for exact effects. Unknown executables are not blocked by category. New mappings require a concrete violating combination and conformance tests.

### Shell segmentation

Unquoted command separators are evaluated by component action. Quoted separators remain literal text.

### Nested parser depth

Nested shell payloads are resolved to a bounded depth. Exceeding the depth does not itself produce a block.

### Unknown provider tools

An unknown provider tool produces no invented effects and remains allowed unless a future concrete contract proves one of the three prohibited outcomes.

## Structural and unsupported-surface errors

These errors are not HR decisions:

- `INVALID_INVOCATION_PATH` — an exact path required for safe transformation cannot be resolved.
- `UNSUPPORTED_PROVIDER_TOOL` — a provider-only tool is not part of the exposed Work contract.
- `UNSUPPORTED_PROVIDER_MODE` — a provider-only argument or mode is not part of the exposed Work contract.
- `PROVIDER_CONFIGURATION_INVARIANT` — an attempted configuration change targets a gateway-managed provider field.

## Provider contract shaping

The following provider surfaces are not exposed through Work:

- `give_feedback_to_desktop_commander`;
- `read_file.isUrl`.

They are absent from the public Work contract because the pinned provider implementation makes them external-network-only. Manually constructed calls fail as unsupported provider surface rather than as HR policy decisions.

## Provider control-plane invariants

### `blockedCommands`

Pinned Desktop Commander defaults include a broad command denylist. The installer writes `blockedCommands: []`, startup verifies it remains empty, and the exposed provider configuration contract cannot modify it.

This prevents Desktop Commander from imposing an independent command policy beneath FastMCP. It is a startup/configuration invariant, not a Work hard block.

### `allowedDirectories`

The installer writes `allowedDirectories: []`, startup verifies it remains empty, and the exposed provider configuration contract cannot modify it.

This prevents Desktop Commander from imposing a separate directory allowlist beneath FastMCP. It is a startup/configuration invariant, not a Work hard block.

## Startup containment

The following readiness checks are startup controls rather than invocation hard blocks:

- telemetry must be disabled in launch environment and persisted provider state;
- `DC_FLAG_URL` must be explicitly loopback because the pinned provider otherwise defaults to an external endpoint;
- a local Chrome/Chromium installation or populated local cache is required when the pinned provider would otherwise download Chrome.

These checks prevent verified automatic provider network activity before ordinary invocation enforcement can operate.

## Installation and readiness controls

Offline installation, pinned package identity, exact provider version, local archive verification, locked Python environment, configuration validation, and provider compatibility checks may prevent installation, startup, or completion claims. They do not deny ordinary Work invocations under a fourth policy rule.

## File materialization permission declaration

KIS marks `read_file` and `read_multiple_files` in MCP tool metadata as operations that may materialize server-returned files. The declaration identifies the `file_materialization` effect and explicitly records that authorization is owned by the host, is not granted by default, and any persistent grant remains host-managed.

This metadata is descriptive permission input for compatible clients. KIS cannot grant, persist, or revoke the host permission itself, and the declaration does not alter Work authorization, existing tool approval, or the HR-001 / HR-002 / HR-003 decision set. Absence or revocation of a host grant therefore remains subject to the client's normal approval behavior.

## Removed or rejected mappings

The following mappings were removed and are not approval items:

- arbitrary URL text anywhere in a command as HR-002;
- package-manager category or missing operand as HR-002;
- generic unknown-command `-o` as HR-001;
- `git reset --hard` as HR-003 permanent deletion;
- `git clean` mapped to the repository root;
- invalid or unresolved write paths mislabeled as HR-001.

## Recovery integrity

Restore refuses to overwrite an existing original path. This protects recovery data and is not an HR hard-block decision against ordinary Work.
