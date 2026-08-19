# Change: Closing Keyword Commissioning

- **Change ID**: `204-closing-keyword-commissioning`
- **Risk Profile**: lean

## Outcome

Commission the landed GitHub issue-closing guard with one fresh governed merge and prove the source issue remains open after landing.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- This is a commissioning-only governed merge after Change 203 landed; do not modify product source or tests.
- Publish and merge this change through the registered exact-head path using only ordinary non-closing references to #364 and #379.
- Require canonical GitHub Actions success on the exact PR head before merge.
- After landing, re-read GitHub issue #364 and prove it remains open; also prove #379 remains open until the wider Change 194 obligation is commissioned.

## Implementation and verification

- Implementation notes: commissioning evidence is the governed Change 204 metadata merge itself; no product behavior is changed.
- Focused checks: governed scope check and diff hygiene only; canonical full verification is owned by the PR-triggered GitHub Actions run.
- Review findings: no specialist review is configured for this small metadata-only commissioning change.
- Residual risk: GitHub repository-level auto-close settings remain optional defense in depth; the registered merge guard is the primary delivered control.
- Closeout state: pending exact-head PR verification, merge, and post-merge issue-state proof.
