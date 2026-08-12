# Change Specification: Reviewable PR Coordinator

- **Change ID**: `106-reviewable-pr-coordinator`
- **Status**: Approved by operator continuation request
- **Development level**: Medium — bounded process/external orchestration with no policy change
- **Risk Profile**: rigorous

## Outcome

Coordinate one exact registered-repository source commit from verification through tree-equivalent remote-default reconciliation and creation of a reviewable pull request, then stop before merge or cleanup.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, and `docs/OPERATIONS.md`.
- This is Slice 7: top-level verified-change-to-PR coordination only.
- Reuse `execute_change_workflow`, `kis_github_reconcile_registered_commit`, registered repository routing, and the existing exact-ref GitHub boundary; do not duplicate verification selectors, runners, reviewers, credential handling, or branch closeout.
- Owned paths are exactly those in `scope.json`; active change 105 owns only `.agents/skills/kis-mcp/**` and does not overlap.
- `policy/**` is excluded; no new hard rule, provider, credential source, arbitrary command, or free-form nested operation authority.

## Requirements

- **REQ-001 — Immutable input:** accept one registered project ID, full local source-commit SHA, full local source-base SHA, non-default review branch, exact expected remote branch SHA/absence, exact expected remote-default SHA, PR title/body, bounded verification/review options, and explicit approval.
- **REQ-002 — Verify first:** execute the existing `execute_change_workflow` against the exact source commit before any external mutation and continue only when its result status is `passed`.
- **REQ-003 — Exact reconciliation:** pass the verified source commit and source base to `kis_github_reconcile_registered_commit`; preserve the exact source tree while rooting the generated review-branch commit on the verified remote-default parent with the existing exact-ref/lease semantics.
- **REQ-004 — Exact PR creation:** add one approval-gated registered-GitHub PR-create primitive that validates the registered repository, remote default branch/base SHA, reconciled review-branch exact head SHA, open-PR absence, and post-create PR head/base/state.
- **REQ-005 — Fixed orchestration:** nested operation names are fixed by implementation; callers cannot supply arbitrary commands, tool names, remote URLs, repositories, merge methods, or policy overrides.
- **REQ-006 — Safe stop:** success means an open, non-draft reviewable PR exists at the exact reconciled head; the result preserves both the verified source-commit SHA and generated reconciled head SHA, and the coordinator must not merge the PR, delete the branch, clean the worktree, or mutate the default branch.
- **REQ-007 — Failure semantics:** verification failure/incompleteness prevents all external mutation; reconciliation failure prevents PR creation; structural/provider errors are returned without claiming completion.
- **REQ-008 — Discoverability:** expose the coordinator as one bounded local tool/workflow and expose registered PR creation only as a discoverable approval-gated virtual GitHub operation; do not expand the direct profile.
- **REQ-009 — Documentation:** update only current canonical product/operations owners for the new coordination boundary.

## Acceptance

1. Given an exact source commit and source base whose existing change workflow passes, an absent/expected review branch, matching remote-default SHA, and approval, the coordinator reconciles the exact verified source tree onto that remote-default parent and creates an open PR whose head is exactly the generated reconciled SHA.
2. A failed or incomplete change-execution result causes zero external reconciliation or PR-create calls.
3. A stale expected target branch, stale default SHA, default-branch target, duplicate open PR, mismatched PR head/base, missing approval, invalid source/base SHA, or source-base/tree mismatch fails closed.
4. The coordinator public schema contains no command, nested tool name, repository URL, merge/delete/cleanup flag, force flag, or policy parameter.
5. The coordinator invokes only `execute_change_workflow` and `execute_external_action`, with the latter restricted internally to fixed registered reconciliation and PR-create operations.
6. Existing exact merge/delete operations and `pull-request-safe-closeout` remain unchanged and separate.
7. Focused tests, scope validation, diff validation, canonical repository verification, and bounded review attempts pass or are recorded accurately on the final state.

## Risks and recovery

- Risk: top-level orchestration could become a second authority layer. Mitigation: fixed nested operation names, registered project resolution, original FastMCP middleware/schema re-entry, explicit approval, and no caller-controlled command/tool selection.
- Risk: verification evidence could refer to a different source. Mitigation: force `source="commit"` with the exact supplied commit and reject any non-passed aggregate before external mutation.
- Risk: a PR could be created for a stale or wrong branch. Mitigation: exact remote default/head checks before creation and exact PR head/base/state verification afterward.
- Recovery: revert Slice 7. Any already-created PR/branch remains visible and recoverable; merge/delete/cleanup are separate explicit operations and are never executed by this coordinator.

## Out of scope

- Automatic PR merge, branch deletion, worktree cleanup, default-branch mutation, auto-merge, reviewer approval, or release/deployment actions.
- Arbitrary Git/GitHub commands, arbitrary provider operations, new credentials, new Work policy rules, or permanent deletion.
- Changes to the concurrently owned KIS operator skill under `.agents/skills/kis-mcp/**`.
