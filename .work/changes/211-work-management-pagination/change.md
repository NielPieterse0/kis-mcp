# Change: Work Management Pagination

- **Change ID**: `211-work-management-pagination`
- **Risk Profile**: lean

## Outcome

Make default public Work Management reads traverse GitHub Project pagination deterministically up to a bounded hard limit, preserving exact-target semantics and reporting truncation only when the hard bound is exhausted.

## Scope and acceptance

- Default broad Work Management inventory/current/board/next-work reads use a bounded 1000-item ceiling instead of the provider-page-sized 100-item default.
- GitHub Project item pagination preserves a valid resume cursor when the hard bound is reached and probes repository-filtered pages deterministically before reporting truncation.
- Exact-target command reads remain independently bounded and fail closed when their exact-target scan is incomplete.
- Truncation is reported only when additional matching Project items exist or the bounded page scan cannot prove completion.

## Implementation and verification

- Implementation notes: raised broad service/tool defaults to 1000; corrected adapter page-size/cursor handling at the item limit without weakening repository filtering.
- Focused checks: adapter regression suite 15/15 passed; Ruff passed on all affected source/test files.
- Review findings: code-quality specialist review completed with no findings; test-quality and API-contract specialist backends failed and required manual exact-diff fallback. Manual review found no response-shape, mutation-authority, exact-target, repository-filter, or cursor-boundary regression.
- Residual risk: direct standalone collection of two project-management workflow test modules currently encounters the repository's pre-existing import-cycle behavior; canonical governed verification remains required. The adapter remains bounded at 20 pages x 50 items = 1000, matching the new broad-read ceiling.
- Closeout state: implementation and focused verification complete; canonical verification/publication pending.
