# Command Plane Live Commissioning Fixes Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Restore live Work Management queue/claim execution discovered during #142 commissioning.

**Architecture:** Keep the provider-neutral command plane unchanged. Correct GitHub Projects normalization at the adapter boundary, add its already-required dependency field to the repository-owned schema manifest, then commission additively through the existing bounded registered-GitHub operation.

**Tech Stack:** Python, pytest, JSON manifest, PowerShell governance/verification, GitHub Projects through KIS.

## Global constraints

- Stay inside `scope.json`.
- Preserve provider result shapes that carry direct scalar values.
- Do not add arbitrary GitHub/GraphQL authority or destructive schema behavior.
- Preserve existing Project item identity and field values.
- Do not close #142 until post-merge live command-plane smoke passes.

### Task 1: Lock the regressions

- [x] Add an adapter test proving metadata-only empty fields normalize to `None`.
- [x] Add a command-plane/schema test requiring `Blocked By` as text.
- [x] Run both tests and capture the expected red state.

### Task 2: Implement the smallest fix

- [x] Separate direct provider value keys from field metadata in `_field_values`.
- [x] Add `Blocked By` to the canonical Project schema manifest.
- [x] Update authoritative implementation/operations documentation from 24 to 25 fields.

### Task 3: Verify and review

- [x] Run focused adapter, schema, command-service, queue, and commissioner tests.
- [x] Run `git diff --check` and governed scope check.
- [x] Run canonical repository verification on the current worktree before publication as required by change workflow.
- [x] Run risk-triggered code-quality, architecture/API-contract, and safety/security review on the implementation diff.

### Task 4: Land and commission

- [ ] Commit the exact reviewed tree and prepare a reviewable PR through KIS.
- [ ] Require provider-native exact-head CI and Work Management merge readiness.
- [ ] Merge, refresh `main`, restart one runtime, and run bounded Project schema commissioning.
- [ ] Verify schema status/plan and the live queue/claim/release/hold/defer/transition/complete paths.
- [ ] Record issue #142 evidence, close only when acceptance passes, and clean the merged worktree.
