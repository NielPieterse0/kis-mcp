# Work Management Documentation Completion Implementation Plan

**Goal:** Finish the approved Work Management/documentation lifecycle and commission its GitHub Project operational projection without changing module-document authoring.

**Architecture:** Keep provider-neutral lifecycle/traceability in `work_management`; add a strict desired Project-schema model and drift report; adapt only the official GitHub Projects MCP read/write methods; expose task-level schema and documentation-lifecycle operations; preserve explicit reconciliation for remote state.

**Tech Stack:** Python 3.13 locked environment, FastMCP 3.4.4, official GitHub MCP Projects tools, pytest, repository PowerShell workflow wrappers.

## Global constraints

- Stay inside `scope.json`; expand scope only after conflict validation.
- Tests precede behavior changes.
- Repository evidence is engineering authority; Project state is an operational projection.
- No direct GitHub network/GraphQL fallback, delete/archive implementation, or new Work rule.
- Generated module documentation is explicitly deferred to Slice 2.

### Task 1: Project schema contract and live drift

- Add strict JSON schema manifest for the approved 18 fields and 12 views.
- Add provider-neutral schema contracts and deterministic drift comparison.
- Extend the GitHub adapter with bounded `list_project_fields` schema observation.
- Add service/tool/CLI status output and tests.
- Prove current Project #1 drift against live provider evidence.

### Task 2: Documentation-aware intake and delivery gates

- Add `documentation_impact` to `CaptureWorkItem` and capture workflow serialization.
- Expose `evaluate_merge_readiness` through a bounded task-level tool.- Expose due/completion documentation milestone orchestration using existing traceability functions.
- Test required/advisory/off behavior and `Documentation -> Done` gating.

### Task 3: Reconciliation and CI integration

- Add desired lifecycle/documentation fields to the schema projection contract.
- Extend fixed-shape CLI/CI with schema-drift and documentation-readiness checks.
- Keep every Project write explicit, idempotent, preflighted, and conflict-aware.
- Do not enable custom automation that lacks live proof.

### Task 4: Commission Project #1

- Read Project #1 metadata/fields before mutation.
- Apply only schema changes supported by the approved official GitHub MCP surface.
- Re-read and record exact live state after supported mutations.
- Record generic field/view provisioning as unsupported when the provider exposes no bounded method; do not bypass the connector boundary.

### Task 5: Documentation and delivery

- Reconcile target spec, roadmap/programme state, commissioning guide, `SPEC.md`, platform/operations docs, README, and KIS skill guidance.
- Run focused tests, scope/diff checks, specialist review, and canonical verification.
- Commit immutable candidate, publish exact-tree PR, merge exact approved head, reconcile lifecycle records, delete remote review branch recoverably, and run safe worktree cleanup.
