# Change Specification: Workflow Provider Hardening

- **Change ID**: `116-workflow-provider-hardening`
- **Status**: Approved for implementation
- **Risk Profile**: standard
- **Work record**: `SPEC-116` / GitHub issue `#156`
- **Operator hold**: implementation may land and clean up, but Work Management must remain open and not `Done` until operator verification.

## Outcome

Harden exact-commit workflow execution and provider runtime stability without weakening exact-head safety or duplicating verification.

## Authority and scope

- Authority: `AGENTS.md` → trust/spec/platform/policy/operations; `.work/changes/116-workflow-provider-hardening/` owns this change.
- Work Management remains a projection, never change authority.
- No policy-rule, credential, production-deploy, or permanent-delete behavior changes.
- Documentation impact is bounded to this change record for 116. The capability/workflow catalogue wording is concurrently owned by active change 118; 116 will not create a conflicting edit there and records the required reconciliation semantics for that owner.

## Requirements

- **REQ-001 — exact committed evidence:** verification selection invoked with `source=commit` must inspect that commit even when the worktree is clean.
- **REQ-002 — worktree import isolation:** verification processes must put `<project>/src` first on `PYTHONPATH` when present, so a shared editable environment cannot import root `main` instead of the selected worktree.
- **REQ-003 — review ergonomics:** omitted reviews keep risk-profile defaults; an explicit empty review list remains valid and must not require a manufactured review.
- **REQ-004 — safe reconciliation:** when the source-base tree equals the verified remote-default tree, review publication may use the exact source tree fast path. When those trees diverge, reconciliation must perform an explicit-base three-way tree merge of the source change onto the verified remote default, preserve remote-only content, fail closed on conflicts, and require exact-head CI on the resulting reconciled tree. Source-base ancestry validation, verified remote-default SHA, exact branch lease, default-branch block, and post-publish head verification remain mandatory.
- **REQ-005 — DBHub idempotency:** generated `dbhub.toml` must not be rewritten when its rendered contents are unchanged.
- **REQ-006 — Serena stability:** child process text/logging must be UTF-8 safe on Windows; a persisted empty central Serena language list may be repaired conservatively from the bounded source paths used for semantic inspection without overwriting a non-empty configured language list.
- **REQ-007 — Docker Hub compatibility:** replace deprecated FastMCP tool-transformation usage with the current visibility transform while retaining fail-closed public tool exposure.
- **REQ-008 — schema friction:** do not widen or rename public operation schemas speculatively. Preserve current `project`/`path` contracts and verify that internal coordinators translate them correctly; any cross-surface alias design remains a separate public-contract change.
- **REQ-009 — platform boundaries:** host classifier blocks that occur before KIS executes are not bypassed. GitHub MCP process-lifetime re-authentication remains intentional and is out of scope.

## Acceptance

1. On a clean repository, selecting verification for a known commit returns commit-derived changed paths instead of `analyze_change requires at least one changed path`.
2. Generated verification command evidence shows the selected worktree `src` path is prepended without changing the parent process environment.
3. Explicit `review_types=[]` executes with no specialist review; omitted reviews still follow `lean/standard/rigorous` defaults.
4. A tree-equivalent base publishes the exact source tree; a divergent base produces the deterministic three-way merged tree on the verified remote-default parent, retains remote-only changes, and publishes nothing when the merge conflicts.
5. Rendering the same DBHub binding twice produces no second config write.
6. Serena receives UTF-8 child environment settings; an exact `languages: []` state is repairable for supported source suffixes and non-empty language config is preserved.
7. DockerHub uses only current FastMCP visibility transforms and exposes only the approved public tools.
8. Focused tests and the final local scope check pass before exact-head CI.
9. Focused tests pass, `change-workflow.ps1 check` passes, and the canonical full `verify.ps1` runs on each corrected exact PR head after a real head-changing fix; successful heads are not redundantly reverified locally.

## Risks and recovery

- Main risk: reconciling a source change onto an independently advanced remote default can silently overwrite unrelated landed work if the source tree is flattened onto the new parent. Mitigation: exact-tree publication only for tree-equivalent bases; otherwise explicit-base three-way `merge-tree`, fail-closed conflicts, review-only publication, exact remote-default expectation, exact lease, visible reconciliation semantics, and exact-head CI before merge.
- Recovery: revert the 116 merge commit; no schema migration, secret rotation, data migration, or policy rollback is required.

## Out of scope

- Host safety-classifier behavior before KIS tool execution.
- GitHub OAuth persistence across KIS process restarts.
- Broad public aliasing of `project` and `path` fields.
- Closing `SPEC-116` / issue #156 or setting Work Management to `Done` before operator verification.
