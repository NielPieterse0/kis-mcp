# Closeout: GitHub Tools Experience

## Programme status

Active. Batch 1 implementation is locally complete and verified; PR/merge evidence is pending. Batches 2 and 3 remain after the Batch 1 merge/reconciliation interval.

## Implemented scope

### Batch 1 — self-describing progressive discovery

- Runtime-discovered MCP tools preserve their authoritative input schema through provider namespacing and capability augmentation.
- `OperationDescriptor` stores JSON-compatible invocation schema without provider-specific coupling.
- Exact `describe_capability` operation/capability requests return the matching operation rather than expanding the provider contribution; the result includes input schema, readiness, eligibility, owner/domain/category, and the correct generic execution surface.
- `search_capabilities` uses deterministic exact/name/capability/text relevance ranking rather than catalogue order.
- Search contribution/operation capability lists are bounded to eight entries while retaining total capability count and explicit match score.
- No GitHub OAuth, repository routing, Project settings, policy, or direct-exposure boundary changed.

## Validation evidence

- TDD RED: focused runner produced exactly four expected failures: runtime tool schema dropped, operation schema absent, exact-description test could not construct schema-bearing operation, and generic Git matching outranked the requested merge operation.
- TDD GREEN: the same focused slice passed 14 tests.
- Expanded focused slice: all `tests/capabilities`, provider runtime/platform composition, and capability architecture boundary checks passed: 52 tests.
- Governance: `pwsh -NoProfile -File .\scripts\change-workflow.ps1 check` passed for the declared 063 scope.
- Whitespace: `git diff --check` passed.
- Canonical verifier: `pwsh -NoProfile -File .\scripts\verify.ps1` passed repository line endings, configuration, canonical interpreter/dependencies, 212-file Python syntax validation, change governance, full pytest (exit 0; two skips), and the exact three-rule verification.
- Temporary focused runner was moved to recoverable quarantine before commit and is not part of the product change.

## Review

- Findings-first manual diff review found no policy, provider-auth, routing, approval, or GitHub-specific semantic knowledge leaking into the generic Batch 1 capability implementation.
- Requested automated `codex` review could not run because that backend is not configured (`AGENT_BACKEND_UNKNOWN`). The configured fallback review backend was also unavailable (`AGENT_BACKEND_UNAVAILABLE`). No automated-agent review pass is claimed.

## Git and merge

- Branch: `change/063-github-tools-experience`
- Worktree: `.work/worktrees/063-github-tools-experience`
- Baseline: local `main` plus an isolated merge of current `origin/main`; the primary checkout was not modified.
- Batch 1 commit: pending.
- Batch 1 pull request / exact-head CI / merge: pending.
- Batches 2–3 will continue in this same governed worktree after each merge is fetched/reconciled.
- Final cleanup remains last.

## Residual items

- Batch 2: GitHub semantic workflow capability mapping and 047 hard eligibility filtering for recommendations.
- Batch 3: deterministic bounded long-tail provider result handling and GitHub Projects/user-audit regression pass.
- Final disposition of the attached audit findings will be recorded after the last merged batch.
