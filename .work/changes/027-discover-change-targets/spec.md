# Change Specification: Discover Change Targets

- **Change ID**: `027-discover-change-targets`
- **Status**: Approved implementation slice
- **Risk Profile**: rigorous

## Outcome

Extend `inspect_change` from a working-tree-only view to bounded local Git target inspection with stable request/response contracts, deterministic path evidence, explicit unknowns, and typed Work verification handoffs.

## Authority and scope

- `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, and `docs/DISCOVER-MODULE-PRODUCT-SPEC.md` govern this change in that order.
- Owned production paths are limited to the change inspection contracts/service and new target-reader modules declared in `scope.json`.
- The slice does not modify `server.py`, `tools.py`, `SPEC.md`, provider code, Work policy, or remote connectors.
- The active `026-commissioning-refresh` change owns shared runtime integration files; this slice remains independently testable and unregistered until a later integration change.

## Requirements

- **REQ-001 — Stable targets:** `InspectChangeRequest` MUST support `working_tree`, `staged`, `commit`, `range`, and `branch` sources using typed target fields. Invalid or ambiguous combinations MUST fail structurally before Git execution.
- **REQ-002 — Safe refs:** caller-supplied refs MUST be bounded, reject option-like or malformed values, and be passed only to fixed direct-argument Git templates with prompts, paging, external diff, text conversion, credential helpers, and network access disabled.
- **REQ-003 — Deterministic inventory:** every supported target MUST normalize added, copied, deleted, modified, renamed, type-changed, unmerged, and unknown path states into deterministic `ChangedFile` records with previous-path evidence where applicable.
- **REQ-004 — Identity:** the response MUST identify source, normalized base/head or commit target, and a stable SHA-256 fingerprint over the normalized target inventory.
- **REQ-005 — Impact evidence:** the response MUST preserve path classifications, affected scopes, impact counts, diagnostics, confidence, and truncation. It MUST add typed verification handoffs derived only from discovered path categories and MUST keep unavailable symbol/dependant evidence explicit as unknowns.
- **REQ-006 — Compatibility:** existing working-tree behavior and JSON identity MUST remain compatible except for additive fields and generalized source values.
- **REQ-007 — Budgets:** Git output, target count, and file count MUST remain bounded by existing Discover settings. Truncation MUST be explicit.
- **REQ-008 — Plane boundary:** the implementation MUST not execute repository code, tests, builds, package managers, hooks, credential helpers, or remote operations.

## Acceptance

1. Given each supported source and a valid local repository, when the reader inspects the target, then deterministic normalized changed paths are returned without shell execution.
2. Given malformed, option-like, or incomplete target fields, when the request is constructed, then a stable structural `ValueError` is raised before Git runs.
3. Given a rename or copy, when target evidence is parsed, then both current and previous paths are preserved.
4. Given changed test, contract, configuration, policy, documentation, or source paths, when the service responds, then categories, impact counts, affected scopes, and bounded verification handoffs are stable.
5. Given Git failure, timeout, unsafe metadata, or output truncation, when inspection completes, then diagnostics, availability, confidence, and unknowns truthfully reflect the degraded result.
6. Given the existing working-tree fixtures, when the updated service runs, then prior classifications and fingerprints remain deterministic.
7. Given the full repository verification suite, when the slice is complete, then all checks pass and the three-rule Work decision set is unchanged.

## Risks and recovery

- Incorrect ref handling could allow unintended Git interpretation. Mitigation: conservative validation, `--end-of-options` where supported, fixed templates, no shell, isolated Git environment, and adversarial tests.
- Schema expansion could break existing callers. Mitigation: preserve schema version 1 and existing fields; add generalized target fields additively.
- Recovery is a normal branch revert; no persistent data or generated state is introduced.

## Out of scope

- Public tool registration changes.
- Remote pull-request or merge-request evidence.
- Semantic symbol/provider integration.
- Bounded dependant graph construction.
- Execution of verification handoffs.
