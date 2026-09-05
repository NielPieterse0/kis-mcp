# Change: Once-Through Manual Exit

- **Change ID**: `645-once-through-manual-exit`
- **Risk Profile**: lean

## Outcome

Add a supported pre-merge exit from once-through that preserves gathered evidence and transfers the user to manual PR/exact-head CI closeout without weakening landing gates.

## Scope and acceptance

- Exit is available from any pre-merge once-through state.
- Existing evidence and source state are retained; no evidence is deleted or fabricated.
- Once-through-specific progression stops after exit.
- Manual closeout still requires GitHub PR identity and provider-native exact-head CI before merge.
- No repository-specific or legacy-schema-specific exception is introduced.

## Implementation and verification

- Implementation notes: added durable `manual_closeout` receipt, public `exit_once_through`, lifecycle projection that stops once-through progression, and a pre-merge guard at the exact-head merge boundary. Evidence lineage is retained unchanged.
- Focused checks: full `tests/workflows/once_through` suite passes under the canonical project Python environment; `change-workflow.ps1 check` and `git diff --check` pass.
- Review findings: independent architecture and API-contract reviews returned no blocking findings; idempotent repeated exit coverage was added from review feedback.
- Residual risk: this is the approved interim escape hatch only; generic rewind/checkpoint/evidence-revalidation hardening remains a separate follow-up.
- Closeout state: implementation complete; publication and exact-head GitHub Actions remain.
