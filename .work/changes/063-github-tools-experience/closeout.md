# Closeout: GitHub Tools Experience

## Programme status

Active. Batch 1 is merged and reconciled. Batches 2 and 3 remain on the same governed worktree, with a verification/merge/reconciliation interval between them.

## Implemented scope

### Batch 1 — self-describing progressive discovery

- Runtime-discovered MCP tools preserve their authoritative input schema through provider namespacing and capability augmentation.
- `OperationDescriptor` stores JSON-compatible invocation schema without provider-specific coupling.
- Exact `describe_capability` operation/capability requests return the matching operation rather than expanding the provider contribution; the result includes input schema, readiness, eligibility, owner/domain/category, and the correct generic execution surface.
- `search_capabilities` uses deterministic exact/name/capability/text relevance ranking rather than catalogue order.
- Search contribution/operation capability lists are bounded to eight entries while retaining total capability count and explicit match score.
- No GitHub OAuth, repository routing, Project settings, policy, or direct-exposure boundary changed.

### Batch 2 — GitHub semantic composition and recommendation contract

- Added a small provider-owned semantic vocabulary for GitHub Actions reads/triggers, pull-request create/merge, and pull-request review write operations. The upstream runtime snapshot remains the authoritative source for whether each operation actually exists.
- Capability availability is now operation-aware: a mapped capability is available only when at least one operation providing it is enabled; provider-wide capabilities with no operation mapping remain available when the contribution is operational.
- Workflow recommendation now follows change 047's hard eligibility contract: candidates with missing capabilities are filtered before scoring/return rather than exposed as recommendations.
- Existing GitHub Projects read/write semantic mappings remain unchanged and continue to route through the bounded Project adapter.
- No GitHub OAuth, PAT, repository-selection, Project settings, policy, direct-exposure, or upstream tool-catalogue behavior changed.

### Batch 3 — bounded long-tail provider results

- Added JSON-governed generic execution result budgets: 100,000 serialized characters, ten preview items, 4,000 preview string characters, and four preview levels.
- Generic execution preserves the original FastMCP result unchanged when structured output is within budget.
- Oversized structured output is replaced only after the underlying operation executes with a deterministic `RESULT_BUDGET_EXCEEDED` envelope containing original size, configured budget, operation name, and a bounded preview.
- Result budgeting is applied after the existing effect, approval, readiness, eligibility, and recursion guards; no authorization path was changed or bypassed.
- Capability settings loader and JSON Schema now validate the result-budget contract as configuration rather than hard-coded runtime policy.

## Validation evidence

- TDD RED: focused runner produced exactly four expected failures: runtime tool schema dropped, operation schema absent, exact-description test could not construct schema-bearing operation, and generic Git matching outranked the requested merge operation.
- TDD GREEN: the same focused slice passed 14 tests.
- Expanded focused slice: all `tests/capabilities`, provider runtime/platform composition, and capability architecture boundary checks passed: 52 tests.
- Governance: `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed for the declared 063 scope.
- Whitespace: `git diff --check` passed.
- Canonical verifier: `pwsh -NoProfile -File .\scripts\verify.ps1` passed repository line endings, configuration, canonical interpreter/dependencies, 212-file Python syntax validation, change governance, full pytest (exit 0; two skips), and the exact three-rule verification.
- Temporary focused runner was moved to recoverable quarantine before commit and is not part of the product change.
- Batch 2 TDD RED: four intended failures isolated missing GitHub semantic descriptors, ineligible-workflow filtering, and operation-aware capability availability; one earlier test-runner path error and one fixture enum typo were corrected and are not counted as product failures.
- Batch 2 GREEN: focused contract slice passed 26 tests; expanded capability/GitHub/Projects/provider/workflow/architecture slice passed 146 tests.
- Batch 2 governance passed after changing the change baseline from the stale shared local `main` to current `origin/main`; this excluded already-merged change 062 files without claiming them.
- Batch 2 `git diff --check` passed.
- Batch 2 canonical verifier completed through the supervised Work process with exit code 0 in 178.44s: dependency audit, 212-file Python syntax check, governance, full pytest with two skips, and exact three-rule verification all passed. Two prior fixed-command invocations exceeded the wrapper's 240-second response ceiling and are not counted as verification results.
- Batch 2 temporary focused and verifier runners were moved to recoverable quarantine before commit and are not product files.
- First exact-head CI attempt for Batch 2: Work Management run `31197813411` on `4a26db0f0d086abe707d3be8c468a2b16344e77b` failed only at global `Validate governance claims`: the clean runner still saw concurrent change 062 as active while its local worktree was absent (`ACTIVE_CHANGE_WORKTREE_MISSING`). Focused P5 and canonical verification were skipped in that run.
- The failure was traced to a stale PR base snapshot, not 063 code or scope. A fresh fetch showed `origin/main` already had change 062 closed and its branch deleted. Current `origin/main` was merged into the 063 branch without editing or claiming any 062 file, and local 063 governance passed again.
- Tooling audit note: both `mcp-tool-1.github_get_workflow_run` and `mcp-tool-1.github_get_workflow_job_logs` reject modern GitHub run/job IDs above signed 32-bit range. The connected GitHub job/log readers accept the same current IDs and were used to diagnose CI. This defect appears outside the kis-mcp source paths searched for change 063.
- Batch 3 TDD RED isolated exactly two intended failures: missing `result_budget` settings and absence of oversized generic-result truncation. A small-result preservation test remained green throughout.
- Batch 3 focused GREEN: capability settings/execution slice passed 16 tests; expanded `tests/capabilities` passed 39 tests.
- Batch 3 configuration evidence: both `settings/capabilities.settings.json` and `contracts/capabilities/settings.schema.json` validate as JSON; governed scope check and `git diff --check` pass.
- The temporary Batch 3 focused runner was moved to recoverable quarantine and is not part of the product change.
- Integrated regression audit passed across capabilities, GitHub provider/Projects, workflows, Work Management, remote runtime, and repository-scope tests after reconciling current `main`.
- User-style capability queries correctly surfaced GitHub pull-request, Actions, and Projects operations with semantic capability aliases; exact Project description retained its authoritative MCP input schema and generic execution surface.
- The same audit exposed one workflow vocabulary defect: `pull-request-safe-closeout` required nonexistent `validation.execute` while the runtime contribution is `verification.execute`. A RED regression reproduced the mismatch; the platform descriptor now uses `verification.execute`, and the focused regression passes.

## Review

- Findings-first manual diff review found no policy, provider-auth, routing, approval, or GitHub-specific semantic knowledge leaking into the generic Batch 1 capability implementation.
- Requested automated `codex` review could not run because that backend is not configured (`AGENT_BACKEND_UNKNOWN`). The configured fallback review backend was also unavailable (`AGENT_BACKEND_UNAVAILABLE`). No automated-agent review pass is claimed.

## Git and merge

- Branch: `change/063-github-tools-experience`
- Worktree: `.work/worktrees/063-github-tools-experience`
- Baseline: local `main` plus an isolated merge of current `origin/main`; the primary checkout was not modified.
- Batch 1 commit: `879af23a0e9b1ba33b92fca9ddc307e7fb96fa2a` (`feat: improve progressive capability discovery`).
- Batch 1 pull request: #78, merged without override.
- Exact-head GitHub Actions: Work Management run `31194665659` on `879af23a0e9b1ba33b92fca9ddc307e7fb96fa2a`; focused P5 and canonical repository verification both concluded `success`.
- Batch 1 merge commit: `551665ec730b308c597c2c06cf58249b042ad06f`.
- After merge, `origin/main` was fetched and reconciled into this same worktree without conflicts; concurrent change 062 arrived only in its declared Discover paths.
- Audit note: the separate `mcp-tool-1.github_get_workflow_run` reader rejected the modern 31-billion GitHub run ID because its public input validator is capped at signed 32-bit integer range. Listing runs and the connected GitHub job reader handled the same run successfully; this appears outside the kis-mcp source paths searched in change 063.
- Batches 2–3 will continue in this same governed worktree after each merge is fetched/reconciled.
- Final cleanup remains last.

## Residual items

- Batch 2: GitHub semantic workflow capability mapping and 047 hard eligibility filtering for recommendations.
- Batch 3: deterministic bounded long-tail provider result handling and GitHub Projects/user-audit regression pass.
- Final disposition of the attached audit findings will be recorded after the last merged batch.
