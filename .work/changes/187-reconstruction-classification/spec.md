# Change Specification: Reconstruction Classification

- **Change ID**: `187-reconstruction-classification`
- **Status**: Active
- **Complexity**: medium

## Outcome

Classify all post-Actions repository and host residue, freeze the serial reconstruction order, and confirm the restored GitHub-native exact-head lifecycle is already the lean verification authority.

## Authority and scope

- Parent programme: `186-post-actions-reconstruction` on merged `main` at `b71fb129fd28513befe8b1c65232cdce5e61ae6d`.
- Historical evidence: Change 185 inventory, post-boundary Git/PR history, preserved local branches, and current host/runtime inspection.
- Current workflow authority: `AGENTS.md`, `docs/operations/verification-changes.md`, and executable GitHub/KIS workflow contracts.
- Owned paths: `.work/changes/187-reconstruction-classification/**` only.

## Requirements

- **REQ-001**: Account for every substantive post-boundary merged, open, frozen, or abandoned change/branch discovered from `1365d84..3bd1330` plus preserved local refs.
- **REQ-002**: Classify each item as `reimplement`, `harvest-only`, `retire`, `superseded`, or `future` with a concrete source ref and dependency posture.
- **REQ-003**: Record host/runtime residue without destructive cleanup in this slice.
- **REQ-004**: Freeze a serial reconstruction order whose children each start from then-current merged `main`.
- **REQ-005**: Keep GitHub Actions as the single canonical exact-head repository verification gate; do not restore local/VM verification as merge authority.
## Acceptance

1. `recovery-register.md` contains the evidence-linked classification and serial order.
2. Obsolete Hyper-V/VirtualBox/local-runner/local-verifier architecture is explicitly excluded from reconstruction.
3. High-value independent fixes/features have bounded fresh-slice sources and prerequisites.
4. Host inspection distinguishes recoverable KIS runtime residue from installed host software; no system uninstall is performed merely for tidiness.
5. The workflow decision is explicit: finalize/freeze one head, run required specialist reviews and GitHub Actions against that head in parallel, merge once green, then align and clean without a metadata-only reverify loop.

## Risks and recovery

- Misclassification could omit useful work; preserved commits/branches/PRs remain recoverable evidence.
- Host cleanup is deferred to the dedicated retirement slice and must use quarantine for KIS-owned delete-like residue.

## Out of scope

- Reimplementing product behavior.
- Deleting preserved history or stale PR evidence.
- Uninstalling host virtualization software.
- FastMCP 4.x / MCP `2026-07-28` migration.