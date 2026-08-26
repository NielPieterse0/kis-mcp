# Closeout: Resource Link Large Results

## Implemented scope

- Oversized capability-dispatch results may return a bounded summary plus an MCP `ResourceLink` to exact canonical JSON.
- Each offload uses an opaque random per-dispatch grant, records origin operation plus independent payload SHA-256, and never deduplicates read authority across dispatches.
- Result publication/read/maintenance is synchronized; TTL/entry/byte bounds are configured, reads never delete state, and expired active entries use the existing recoverable quarantine service during later store maintenance.
- Resource persistence is optional enrichment: storage failure, over-size, or capacity exhaustion preserves the prior `RESULT_BUDGET_EXCEEDED` summary contract.
- Legacy four-field `result_budget` settings remain valid and receive stable resource defaults.

## Validation evidence

- Focused checks: Ruff clean; 38 focused capability/settings/gateway tests passed after final contract remediation.
- Repository verification: canonical full verification remains owned by exact-head GitHub Actions after publication.
- Diff scope check: `git diff --check` and `scripts/change-workflow.ps1 check` passed.

## Review

- Architecture: fallback Codex exact-diff review found three boundary issues; all were remediated. Re-review at fingerprint `0d8f2898...` returned zero findings.
- API contracts: first review found persistence-failure and legacy-settings compatibility gaps; both were remediated and covered by focused tests. Automated re-review routes then hit output/deadline limits, so exact-diff fallback confirmed the two specific contracts.
- Test quality: earlier substantive review findings were remediated; final automated rerun timed out, with exact-diff fallback confirming coverage for the newly added compatibility cases.

## Git and merge

- Branch: `change/245-resource-link-large-results`
- Worktree: `.work/worktrees/245-resource-link-large-results`
- Commit:
- Pull request or merge:
- Cleanup:

## Residual items

-
