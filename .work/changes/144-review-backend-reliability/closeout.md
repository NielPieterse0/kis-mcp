# Closeout: Review Backend Reliability

## Implemented scope

- Typed/redacted NVIDIA HTTP, timeout, and transport failures.
- Explicit UTF-8 strict Codex process I/O with typed encoding failures.
- JSON-configured per-backend retry budget with allowlisted transient retry classes.
- Bounded attempt history and exact-diff manual fallback after automated backend exhaustion.
- Change execution accepts only reviewer `status=completed` as review success.

## Validation evidence

- Focused checks: changed-module `py_compile` passed; focused pytest set passed after preloading `kis_mcp.capabilities` to avoid the repository's existing import-order circularity during isolated collection; retry-budget settings/schema regression coverage passed.
- Repository verification: delegated to exact-head PR CI per repository authority.
- Diff scope check: `scripts/change-workflow.ps1 check` passed; `git diff --check` passed.

## Review

- Automated code-quality review: `kis-dev` timed out; `kis-op` NVIDIA returned `status=failed` / `AGENT_BACKEND_FAILED:NvidiaNimError`.
- Automated API-contract review: `kis-dev` timed out; `kis-op` Codex returned `status=failed` / `AGENT_BACKEND_FAILED:CodexCliError`.
- Manual exact-diff fallback finding: Codex used `errors="replace"`, which could conceal invalid UTF-8 rather than produce the required typed encoding failure.
- Resolution: changed Codex subprocess text boundary to `errors="strict"` and updated regression expectations. No automated review pass is claimed.

## Git and merge

- Branch: `change/144-review-backend-reliability`
- Worktree: `.work/worktrees/144-review-backend-reliability`
- Commit: implementation and contract commits are present on the branch; the exact final head is verified during registered publication.
- Pull request: pending registered publication.
- Merge and cleanup: pending and outside the current verification/review/PR lane.

## Residual items

- Branch was reconciled cleanly onto current local `main`; exact-head PR CI remains the canonical repository-wide verification gate.
- Current repository has an import-order circularity visible when focused tests import `kis_mcp.tools` before `kis_mcp.capabilities`; that defect is outside this change's owned paths and is not absorbed here.
- The code-review settings schema already omits the pre-existing NVIDIA `benchmark` block; this change does not expand into that unrelated schema drift.
