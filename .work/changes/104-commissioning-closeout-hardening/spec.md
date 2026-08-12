# Change Specification: Commissioning Closeout Hardening

- **Change ID**: `104-commissioning-closeout-hardening`
- **Status**: Approved by operator continuation request
- **Development level**: Medium — cross-cutting commissioning reliability with bounded GitHub mutation, no policy change
- **Risk Profile**: rigorous

## Outcome

Harden change commissioning and PR closeout with canonical LF change records and an exact remote-default-rooted publication path for tree-equivalent local history.

## Authority and scope

- Authorities: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, and `docs/OPERATIONS.md`.
- This is Slice 6 from changes 093/099: commissioning and PR-closeout automation only.
- Reuse the existing governed change lifecycle and exact registered-GitHub service; do not add arbitrary Git, shell, repository, credential, or policy authority.
- Owned paths are exactly those in `scope.json`; `policy/**` is excluded and active change 103 paths do not overlap.

## Requirements

- **REQ-001 — LF generation:** `change-workflow.ps1 new` must create all five tracked change artifacts with canonical LF bytes on Windows without weakening `.gitattributes` or `core.safecrlf`.
- **REQ-002 — Tree-equivalent reconciliation:** add one approval-gated registered-GitHub operation that can publish a source change onto the current remote default-branch parent only when the declared local source-base tree exactly equals the expected remote-default tree.
- **REQ-003 — Exact remote state:** require the registered project, expected remote default SHA, expected target-branch SHA/absence, and explicit approval; recheck the remote default after fetch and use an exact ref lease for publication.
- **REQ-004 — Preserve content:** the reconciled commit must use the exact source commit tree and a fixed generated provenance message; caller input must not supply arbitrary commit-tree arguments or command text.
- **REQ-005 — PR branch only:** refuse reconciliation publication directly to the remote default branch; the path exists to create clean review branches, not bypass PR review.
- **REQ-006 — Existing semantics:** keep immutable exact publication, exact-head PR merge, exact remote-branch deletion, credentials, and HR-001/HR-002/HR-003 behavior unchanged.
- **REQ-007 — Exposure:** expose the reconciliation primitive only as a discoverable approval-gated registered-GitHub virtual operation through the existing external dispatcher; do not expand the direct profile.
- **REQ-008 — Documentation:** reconcile current implementation and operator procedure in existing canonical owners only.

## Acceptance

1. A newly created change record contains no CRLF bytes in `scope.json`, `spec.md`, `plan.md`, `tasks.md`, or `closeout.md`.
2. Divergent local/remote commit ancestry can be reconciled only when the source-base tree equals the exact expected remote-default tree.
3. A tree mismatch, stale remote-default SHA, stale target-branch SHA, default-branch target, missing approval, or invalid Git result prevents publication before an unsafe ref update.
4. A successful reconciliation publishes a generated commit whose tree is exactly the source commit tree and whose sole parent is the verified remote-default SHA, then verifies the target ref.
5. Existing registered-GitHub operations and direct-profile bounds remain unchanged except for the additive discoverable operation.
6. Focused tests, scope check, diff check, canonical repository verification, and bounded review attempts run on the final state.

## Risks and recovery

- Risk: a history repair path could become a force-push or content-rewrite primitive. Mitigation: registered target only, exact source tree, exact remote-default equivalence, non-default target branch, exact leases, fixed command shapes, and explicit approval.
- Risk: the remote default branch can move during reconciliation. Mitigation: exact expected SHA before and after fetch; fail rather than rebase implicitly.
- Risk: generated line endings may vary by host defaults. Mitigation: explicit LF file writing in change creation, with byte-level regression coverage.
- Recovery: revert this slice. Published reconciliation branches retain the returned source and generated commit SHAs; remote branch deletion remains a separate explicit exact-head action.

## Out of scope

- Automatic PR creation or merge without explicit connector inputs and approval.
- Rewriting the remote default branch, force-pushing published history, admin bypass, arbitrary `gh`/Git commands, new credentials, or new hard rules.
- Slice 7 top-level completion coordination and active change 103 workflow-descriptor work.
