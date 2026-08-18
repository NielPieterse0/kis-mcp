# Change Specification: Governed Acquisition Envelope

- **Change ID**: `191-governed-acquisition-envelope`
- **Parent**: Change 186 / issue #356
- **Work item**: issue #361
- **Historical source**: Change 175 commit `141bbe8`

## Outcome

Restore the generic acquisition authorization envelope so registered acquisitions bind authorization to the exact approved profile identity and content hash, fail closed on mismatch, and expose no implicit mutation authority.

## Requirements

- Acquisition settings/schema define explicit registered profiles and authorization identity.
- Runtime loads and validates profiles deterministically.
- Authorization binds to profile ID plus exact profile hash; stale or mismatched approval cannot execute.
- Service and public dispatch preserve existing Work/policy boundaries and fail closed on malformed/unregistered inputs.
- Product documentation reflects the implemented registered acquisition contract.

## Acceptance

Focused acquisition and dispatch tests pass; Ruff and scope check pass; required public-contract/code-quality reviews and GitHub Actions pass on one frozen head.