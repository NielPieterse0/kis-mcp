# 023 Discover Change Service Specification

## Status

Approved bounded implementation slice. Development level: Medium because it adds multiple new contract, service, schema, and test surfaces, but it does not alter public registration, policy, settings, providers, or persistent state.

## Outcome

Add an internal working-tree `inspect_change` service that consumes the merged bounded `LocalChangeInventory` seam and returns a deterministic provider-neutral projection for later public registration.

## Requirements

- **R1** — Accept only a non-empty project path and the fixed source `working_tree`; reject unsupported source values structurally before invoking Git.
- **R2** — Obtain change evidence exclusively through an injected local-change reader exposing `inspect_local_changes(project_path)`; this slice must not add subprocess or network use.
- **R3** — Preserve every retained local change path, previous path, staged status, worktree status, and untracked state.
- **R4** — Produce a deterministic change fingerprint from the canonical serialized retained inventory, excluding time-sensitive metadata.
- **R5** — Classify paths deterministically into one or more conventional categories: `source`, `test`, `contract`, `documentation`, `configuration`, `policy`, or `other`.
- **R6** — Return deterministic affected scopes derived from top-level repository path segments, using `.` for repository-root files.
- **R7** — Return explicit changed-test, contract, documentation, configuration, and policy path lists without claiming dependant or symbol analysis.
- **R8** — Preserve inventory diagnostics and truncation, and surface first-class unknowns for unavailable relationship, symbol, and verification mapping evidence.
- **R9** — Set overall confidence to `low` when repository evidence is unavailable, `medium` when evidence is truncated or diagnostics exist, otherwise `high` for the bounded observed projection.
- **R10** — Serialize an exact schema-version-1 response with fixed tool identity `inspect_change` and source `working_tree`, validated against a checked-in Draft 2020-12 JSON Schema.
- **R11** — Keep public tool registration, refs/ranges/commits, diff content, semantic providers, dependant mapping, verification handoffs, and remote forge evidence out of scope.

## Acceptance evidence

- Contract tests prove request validation, exact serialization, deterministic fingerprinting, stable ordering, classification, scope derivation, confidence, unknowns, diagnostics, and truncation behavior.
- The serialized representative response validates against the checked-in schema.
- A real temporary Git repository proves the service composes with the existing `GitReader.inspect_local_changes()` implementation.
- Architecture checks confirm no new Discover subprocess import and no public registration change.
- Focused tests, affected Discover tests, scope checks, whitespace checks, and the serialized full verification pass on the final branch head.

## Recovery

The slice is additive and creates no persistent state or configuration. Reverting its commit removes the internal contracts, service, schema, tests, and lifecycle artifacts.
