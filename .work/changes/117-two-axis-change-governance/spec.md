# Change Specification: Two-Axis Change Governance

- **Change ID**: `117-two-axis-change-governance`
- **Status**: Approved for implementation
- **Bootstrap classification**: this in-flight migration remains a schema-v3 `standard` record; schema v4 applies to changes created after 117 lands
- **Target complexity**: `medium`
- **Target risk triggers**: `external_action`, `persistent_state`, `public_contract`
- **Work record**: `SPEC-117` / GitHub issue `#157`
- **Operator hold**: repository implementation may land and clean up, but Work Management must remain open and not `Done` until operator verification.

## Outcome

Replace the ordinal `risk_profile` model with independent workload complexity and additive objective risk triggers, while retaining historical change-record compatibility and keeping Work Management as projection rather than authority.

## Authority and scope

- Authority: `AGENTS.md` → trust/spec/platform/policy/operations; this change owns the paths in `scope.json`.
- Pure supervised runtime/operator actions that do not modify version-controlled repository authority do not require a Git change solely for process compliance.
- Governed repository changes continue to use the existing branch/worktree/PR path.
- The three hard rules remain exactly HR-001, HR-002, and HR-003.
- `.agents/skills/develop-code/**` and `.agents/skills/develop-docs/**` are explicitly excluded for operator-owned follow-up.
- Change 116 owns `change_execution/**`; that final integration is dependency-blocked until 116 releases the path.
## Requirements

- **REQ-001 — repository-change trigger:** Git governance applies when tracked repository content is created, modified, moved, or otherwise changed; operational-only supervised actions remain outside Git governance unless they modify repository authority.
- **REQ-002 — independent complexity:** new governed changes record exactly one of `small`, `medium`, or `large`; risk must never raise complexity by itself.
- **REQ-003 — additive risk triggers:** new governed changes record zero or more of `security`, `secrets`, `sensitive_data`, `money`, `persistent_state`, `migration`, `external_action`, `deployment`, `destructive`, `public_contract`, `architecture_boundary`.
- **REQ-004 — schema compatibility:** new changes use schema version 4 with `complexity`, `risk_triggers`, and base evidence; historical schema versions 1–3 remain readable under their existing semantics.
- **REQ-005 — lifecycle sizing:** `small` uses the compact record (`scope.json` + `change.md`); `medium` and `large` use `scope.json`, `spec.md`, `plan.md`, `tasks.md`, and `closeout.md`, independent of risk triggers.
- **REQ-006 — Work Management projection:** specification/repository work may expose `Complexity` and `Risk Triggers` without replacing Record Type, Priority, Severity, Status, or other existing fields; the local change record remains authoritative.
- **REQ-007 — normalized work contract:** `WorkRecord` and project-management parsing carry optional complexity and canonical ordered risk triggers so portfolio/project projections can represent the same classification.
- **REQ-008 — authoritative guidance:** `AGENTS.md` documents the two-axis model, operational-only exception, schema compatibility, and new CLI syntax.
- **REQ-009 — execution integration:** after change 116 releases its exclusive claim, change execution uses complexity for base verification breadth and risk triggers only for applicable additive reviews/checks. `small` defaults to 6 selected verifications; `medium` and `large` default to 20. `medium`/`large` retain one base `code-quality` review. Risk-derived specialist reviews are narrow: `security|secrets|sensitive_data` add `safety-security`, `public_contract` adds `api-contracts`, and `architecture_boundary` adds `architecture`; all risk triggers are also supplied as verification-selection terms. Explicit review types may add reviews but must not suppress classification-derived controls.

## Acceptance

1. Creating a `small` change with `secrets` still creates only the compact lifecycle record.
2. Creating a `medium` or `large` change creates the full lifecycle record even with no risk triggers.
3. Schema-v3 `lean|standard|rigorous` records remain valid and cleanup-compatible; new records contain no `risk_profile`.
4. Invalid or duplicate stored risk triggers are rejected deterministically; newly created triggers serialize in canonical order.
5. Work Management manifest contains exactly 20 fields and 12 views, adding `Complexity` and `Risk Triggers`.
6. Work records round-trip optional complexity/risk triggers without changing unrelated lifecycle semantics.
7. Runtime change execution and completion expose `complexity` plus `risk_triggers`, emit no new `risk_profile`, and apply only the base/risk controls defined in REQ-009.
8. No implementation or documentation under either excluded skill path changes.
9. Focused tests and change-scope checks pass; the canonical full verifier runs once on the exact PR head.
## Risks and recovery

- `persistent_state`: the authoritative local change-record schema changes. Mitigation: introduce schema v4 while retaining schema v1–3 parsers and tests.
- `public_contract`: CLI arguments and normalized Work Management JSON gain/replace classification fields. Mitigation: fail explicitly on retired new-write syntax while preserving historical stored records.
- `external_action`: commissioning adds GitHub Project fields and updates the SPEC-117 projection. Mitigation: bounded Project operations, deterministic preview/apply, and operator-held final status.
- Recovery: revert the 117 merge; no data migration, credential rotation, hard-rule change, or irreversible deletion is required.

## Out of scope

- Editing `develop-code` or `develop-docs` skill classification content.
- Adding Direct/Planned/Gated as a second authoritative classification.
- Adding low/medium/high risk levels.
- Adding a fourth KIS policy restriction or permission gate.
- Making GitHub Projects authoritative for change creation or execution.
- Closing issue #157 / SPEC-117 or setting it `Done` before operator verification.
