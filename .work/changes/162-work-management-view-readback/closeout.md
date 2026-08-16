# Closeout: Work Management View Readback

## Implemented scope

- Retain each canonical Project view number and use it for bounded saved-view item readback.
- Require complete behavioral evidence for filtered canonical views before semantic readiness can be true.
- Reject contradictory, malformed, blank, or paginated-beyond-budget behavioral evidence as unready/unverified.
- Repair documented existing-view layout, filter, and visible-field drift in place; refuse unsupported sort/group/vertical-group drift and retain the no-delete/recreate boundary.
- Reapply a structurally matching filter once when behavioral readback contradicts it, then require a fresh structural and behavioral re-read before success.
- Reopen Work Management programme commissioning until #270 is proven live across all 12 canonical views.

## Validation evidence

- Focused/composition checks: 45 passed across schema commissioning, Work Management schema/service, platform composition, and import isolation.
- Broad affected checks: 256 passed across GitHub Project commissioning, Work Management, registered-GitHub exact operations, platform composition, and import isolation.
- Ruff: changed production/test files passed via the installed Ruff executable.
- Python compilation: changed production modules passed `py_compile`.
- Repository verification: pending exact-head GitHub Actions after PR creation.
- Diff scope check: `git diff --check` passed; `scripts/change-workflow.ps1 check` passed with all changed paths inside `scope.json`.

## Review

- Required exact-commit `code-quality` review on `865b778`: completed with zero blocking/high/medium findings.
- Required exact-commit `api-contracts` review on `865b778`: completed with zero blocking/high/medium findings.
- Earlier review findings for blank response acceptance, unbounded pagination, permissive parsing, integer behavior flags, non-canonical view probing, and implicit default-manifest selection were fixed and regression-covered before the exact-commit reviews.
- One earlier NVIDIA filter-tokenization finding was rejected because GitHub Project filter grammar uses whitespace between qualifiers and commas between multiple values of the same qualifier; the implementation follows that contract.

## Git and merge

- Branch: `change/162-work-management-view-readback`
- Worktree: `.work/worktrees/162-work-management-view-readback`
- Reviewed implementation commit: `865b778fa69f8fef508f4b19f42f0508bb10f7e6`.
- Pull request / exact-head Actions / merge: pending.
- Cleanup: pending verified merge and live recommissioning.

## Residual items

- Publish the reviewed implementation plus this evidence reconciliation through the governed PR path.
- Restart/rebind a runtime to the landed revision and rerun all 12 semantic/behavioral saved-view checks.
- Reconcile evidence-backed legacy `Todo` / `In Progress` records without blind status mapping.
- Close #270 and return the programme to completed only after the live Project passes final acceptance.
