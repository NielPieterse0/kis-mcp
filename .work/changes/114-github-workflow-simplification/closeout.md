# Closeout: Github Workflow Simplification

## Implemented scope

- Implemented schema-v3 local authority, risk-scaled change execution, exact-head CI gating, merge-commit-only landing, deterministic PR metadata, bounded registered-repository settings, safe Project read/batch-update exposure, dependency automation, and reconciled authority/runbook/skill documentation.
- Preserved schema-v1/v2 compatibility, exact Git publication/reconciliation/merge/cleanup invariants, the three hard rules, and the existing 18-field / 12-view Work Management target.

## Validation evidence

- Focused checks: major integration set `155/155`; final stale-contract corrections `5/5`.
- Repository verification: `pwsh -NoProfile -File scripts/verify.ps1` exited `0`; full pytest suite green with 2 expected skips, Python syntax `277` files, configuration/dependencies/change-governance/verification all green.
- Diff scope check: `pwsh -NoProfile -File scripts/change-workflow.ps1 check` exited `0`.

## Review

- Findings: one explicit Codex review attempt failed with `AGENT_BACKEND_FAILED:CodexCliError`; no retry/fallback was used. Direct whole-diff review identified a missing provider-native exact-head CI observation in normal closeout orchestration.
- Resolutions: closeout workflows now require GitHub PR + Actions evidence for the exact head before merge and do not repeat local verification after PR publication; affected tests are green. The first exact-head CI run also exposed one DBHub readiness test that depended on the developer workstation's College database path; the test now constructs its claimed ready local binding hermetically, with production readiness logic unchanged.

## Git and merge

- Branch: `change/114-github-workflow-simplification`
- Worktree: `.work/worktrees/114-github-workflow-simplification`
- Landing: schema-v3 treats the merged Git/GitHub state as final authority; exact commit/PR/merge/cleanup facts are derived after landing without a second metadata-only PR.

## Residual items

- Work Management simplification/rich Project follow-up remains separately tracked in GitHub issue `#142`.
- GitHub MCP provider upgrade remains separately tracked in GitHub issue `#148`.
