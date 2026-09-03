# Closeout: Task Durable Completion 502

## Implemented scope

- `prepare_reviewable_pull_request` now requires MCP 2026 Tasks.
- Added explicit synchronous compatibility tool `prepare_reviewable_pull_request_sync` using the same completion coordinator.
- Preserved exact identity, stable operation identity, registered GitHub reconciliation, retry classification, and response-loss recovery semantics.
- Updated `SPEC.md` current task-boundary contract.

## Validation evidence

- Focused completion/MCP task suite: passed.
- Completion-specific reconnect test proves immediate `tasks/get` resolvability, reconnect retrieval, and one task-backed service execution.
- Explicit sync fallback behavioral call passes for a core-only client.
- Changed-file Ruff: passed.
- `git diff --check`: passed.
- Change scope validation/check: passed after adding the exact local-tool inventory regression.
- First exact-head Actions run on `be027d7421c61dc3cc3a100fedada3858a6e687d` failed only because `tests/discover/test_tool_registration.py` had not yet listed the new explicit sync tool; focused reproduction/fix now passes.

## Review

- Code-quality review: zero actionable findings.
- Test-quality review: initial medium gaps were strengthened; re-review left notes only, including explicit sync behavior now covered.
- API-contract review: zero actionable findings; required-task primary and forbidden-task fallback match implementation intent.

## Git and merge

- Branch: `change/628-task-durable-completion-502`
- Worktree: `.work/worktrees/628-task-durable-completion-502`
- Initial commit: `19378ac4804218ddab307729e1a0748552736890`.
- Pull request: #668.
- First exact-head Actions: failed on stale local-tool inventory expectation; corrected before republishing a new exact head.
- Merge / registered-main refresh: pending.
- Post-merge #641 observer acceptance: pending.

## Residual items

- Full canonical verification remains owned by provider-native exact-head GitHub Actions.
- FastMCP task backend remains process-local; KIS durable operation/Work/reconciliation state remains authoritative across server restart.
