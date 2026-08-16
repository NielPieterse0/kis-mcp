# Closeout: Work Management View Readback

## Implemented scope

- Retain each canonical Project view number and use it for saved-view item readback.
- Require complete behavioral evidence for filtered canonical views before semantic readiness can be true.
- Reject contradictory, malformed, blank, duplicate-required-field, provider-failed, or incomplete pagination evidence as unready/unverified.
- Follow GitHub saved-view `after` cursors explicitly at 100 items per page within a fixed 10-page / 1000-item budget; reject malformed links, cursor cycles, and budget exhaustion; do not use unbounded pagination.
- Repair documented existing-view layout, filter, and visible-field drift in place; refuse unsupported sort/group/vertical-group drift and retain the no-delete/recreate boundary.
- Reapply a structurally matching filter once when behavioral readback contradicts it, then require a fresh structural and behavioral re-read before success.
- Keep #270 open until the final landed runtime proves all 12 canonical views behaviorally ready.

## Delivery history

- PR #293 merged the initial behavioral saved-view readback and fail-closed readiness implementation as merge commit `e238067169a272e3cb3c6284264653557ba7306b`.
- PR #295 merged the exact-evidence hardening on the authoritative `change/162-work-management-view-readback` branch as merge commit `2def20627a2d54e7ab08ddc2f74c477440c888a7`.
- Fresh post-merge commissioning on `2def206…` removed false contradictions but still reported seven canonical views unverified. `12 Completed` was confirmed to exceed the first 100 saved-view items; the remaining failures required explicit diagnostic reason codes rather than speculative mutation.
- The final pagination/diagnostic tranche was developed under the same Lane A scope. Focused pagination tests were observed red before implementation and green after implementation; the full provider file and affected Work Management tests were green in the interrupted same-lane session before publication reconstruction.

## Validation evidence

- Earlier implementation tranche: focused/composition checks and broad affected verification passed before PR #293/#295 publication; their exact-head Canonical Verification runs passed before merge.
- Final pagination regressions: explicit cursor-follow and cursor-cycle cases were red before implementation and green after implementation in the same change worktree.
- Final provider regression file: green after updating diagnostic expectations in the same change worktree.
- Final affected provider + Work Management test set: green in the same change worktree before interruption.
- Exact reconstructed GitHub head CI: pending.
- Final live 12-view commissioning: pending merge and runtime restart/rebind.

## Review

- The pre-pagination implementation and evidence-hardening tranches received exact-source code-quality and API-contract reviews with no blocking/high/medium findings before PR #295.
- The pagination/diagnostic tranche changes only bounded saved-view read pagination and fail-closed evidence diagnostics. It still requires final exact-head review/CI before landing.
- GitHub's current Project REST contract uses cursor pagination for saved-view items and exposes single-select field values as structured option objects; the implementation remains aligned with that contract.

## Git and merge

- Branch: `change/162-work-management-view-readback`.
- Worktree authority: `.work/worktrees/162-work-management-view-readback`.
- Prior landed head: `e3b26af2940f03aac8f29d185b1e53fe6176e4e4` via PR #295.
- Current pagination/diagnostic publication head: pending final branch commit after this evidence reconciliation.
- Cleanup: pending verified final merge and live recommissioning.

## Residual acceptance gates

- Pass exact-head CI and final review for the pagination/diagnostic tranche.
- Merge only the frozen reviewed head.
- Restart/rebind `kis-dev` to the landed revision and rerun all 12 saved-view semantic/behavioral checks.
- If any view remains unverified, use the new bounded reason code to fix only the proven contract gap; do not mutate a view on incomplete evidence.
- Reconcile only evidence-backed legacy `Todo` / `In Progress` records without blind status mapping.
- Close #270 and return the Work Management programme to completed only after the live Project passes final acceptance.
