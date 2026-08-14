# Change: Project Owner Type Autodetect

- **Change ID**: `141-project-owner-type-autodetect`
- **Risk Profile**: lean

## Outcome

Align GitHub Project authorization with the advertised owner_type auto-detection contract while preserving registered-project scope.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Record the observable acceptance criteria for this bounded change here.

## Implementation and verification

- Implementation notes: when `owner_type` is omitted, authorize only if the registered owner/project number maps to exactly one approved owner type; preserve explicit validation and reject ambiguous registrations.
- Focused checks: red test reproduced the omission failure; `tests/providers/github/test_scope.py` passes 21/21; the complete `tests/providers/github` slice passes; `git diff --check` and `change-workflow.ps1 check` pass.
- Review findings: NVIDIA safety/security and Codex API-contract review backends both failed independently. Manual exact-diff review found no blocking authorization or contract issue: inference is derived only from approved Project identities and ambiguity remains fail-closed.
- Residual risk: live runtime verification requires a refreshed KIS runtime containing this change; the currently running runtime still reflects the pre-change source revision.
- Closeout state: implementation verified locally; pending commit, exact-head CI, live refreshed-runtime smoke, merge, and board/issue reconciliation.
