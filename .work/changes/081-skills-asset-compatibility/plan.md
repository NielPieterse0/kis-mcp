# Skills Asset Compatibility Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Restore Skills catalogue compatibility with approved packaged skill assets without permitting arbitrary extensionless files.

**Architecture:** Extend the existing JSON-governed Skills validation contract rather than adding implicit heuristics. Keep source-reader enforcement narrow, add explicit metadata for every observed skill, and verify through focused catalogue/capability/Gateway tests before the canonical repository verifier.

**Tech Stack:** Python, JSON/JSON Schema, pytest, PowerShell repository workflows, Git/GitHub.

## Global constraints

- Stay inside `scope.json` and preserve clean change 040.
- Do not alter HR-001/HR-002/HR-003 or add a fourth policy rule.
- Do not infer capabilities for unknown Skills.
- Exact filenames are case-sensitive and fail closed.
- No force-push, destructive reset, or permanent-delete path.

### Task 1 — Reproduce and bound the compatibility gap (`R1`, `R2`, `R3`)

**Files:** `settings/skills.settings.json`, `contracts/skills/settings.schema.json`, `src/kis_mcp/skills/config.py`, `src/kis_mcp/skills/source.py`, Skills tests.

- [x] Identify observed asset suffixes, extensionless `LICENSE`, and size envelope from the approved shared root.
- [x] Add regression coverage for exact allowed extensionless filename behavior.
- [x] Implement explicit JSON/schema/config support and bounded size changes.
- [x] Confirm exact configured extensionless text filenames work for reads and replacement validation.
- [x] Confirm unknown extensionless files remain rejected.

### Task 2 — Restore capability composition (`R4`, `R5`)

**Files:** `settings/capabilities.settings.json`, capability tests.

- [x] Add explicit category/capability/activation/effect/workflow metadata for the 12 newly installed Skills.
- [x] Replace composition-count assumptions with the settings-derived catalogue contract where appropriate.
- [x] Re-run the capability and Gateway composition regressions.

### Task 3 — Review, verify, and land (`R1`–`R5`)

- [x] Reconcile spec, plan, implementation, tests, and diff; resolve blocking review findings.
- [x] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [x] Run focused Skills/capability/Gateway tests on the final worktree state.
- [x] Run `pwsh -NoProfile -File scripts/verify.ps1` on the final worktree state.
- [ ] Stage and commit only owned paths; push branch and open/update PR.
- [ ] Gate the exact head with Work Management and review evidence.
- [ ] Land only the verified exact head through the repository-approved PR path.
- [ ] Close metadata, run governed cleanup from clean primary `main`, and re-run canonical verification.
- [ ] Confirm final worktree inventory is primary `main` plus preserved clean 040 only.
