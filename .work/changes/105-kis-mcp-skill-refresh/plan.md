# kis-mcp Skill Refresh Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Make the KIS operating skill faster to use and current with the latest implemented workflow slices without creating new authority.

**Architecture:** Keep task routing and mandatory safety/status boundaries in `SKILL.md`; keep detailed schemas, provider/workflow behavior, project routing, and operator procedures in the existing focused references. Use canonical docs and merged/verified change evidence as source truth, and require live runtime discovery for deployment-sensitive behavior.

**Tech Stack:** Markdown, repository change workflow, Git, canonical PowerShell verifier.

## Global constraints

- Stay inside `scope.json`; do not overlap active change 106 runtime/canonical-document ownership.
- Do not add runtime tools, settings, dependencies, credentials, or policy rules.
- Prefer current live schemas over copied parameter lists where runtime drift is possible.
- Keep `SKILL.md` under 500 lines and preserve one-level relative references.

### Task 1 — Reconcile current capability evidence

- [x] Read repository authorities and the requested MCP/skill guidance.
- [x] Reconcile changes 093/096/097/098/099/100/101/103, locally merged Slice 6 change 104, and the active Slice 7 change 106 contract.
- [x] Confirm Slice 7 targets exact verified-commit-to-reviewable-PR coordination and remains in progress until live-advertised.

### Task 2 — Refresh the user workflow

- [x] Add a concise intent-to-tool fast path.
- [x] Add the current change-analysis, verification-selection/execution, review, agnix, and closeout workflow guidance.
- [x] Remove stale transition/pending wording from focused references while preserving live-runtime checks.

### Task 3 — Review, verify, and close

- [x] Review the final skill against the task-first outcome and authority boundary.
- [x] Run `scripts/change-workflow.ps1 check` and `git diff --check`.
- [x] Run focused structural checks for frontmatter and relative references.
- [x] Run canonical `pwsh -NoProfile -File scripts/verify.ps1` on the final skill state.
- [x] Reconcile closeout evidence for the final verified commit; local merge/cleanup is evidenced by Git/worktree state.
