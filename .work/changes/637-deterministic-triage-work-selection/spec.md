# Change Specification: Deterministic Triage Work Selection

- **Change ID**: `637-deterministic-triage-work-selection`
- **Status**: Implemented; publication pending
- **Complexity**: Large
- **Risk triggers**: external_action, public_contract

## Outcome

Implement issue #543 only: deterministic Triage progression plus canonical tiered Work selection from the landed #542 Work contracts.

## Authority and scope

- Repository authority: `AGENTS.md` and canonical Work Management contracts.
- Work authority: GitHub issue #543, consolidating #386/#443/#444 under programme #489.
- Dependency: landed #542 / change `631-work-admission-conformance`.
- Owned and excluded paths: `scope.json`.
- Active #625 adapter/tool paths and downstream #544/#545/#547/#546 remain excluded.

## Requirements

- Ready selection MUST rank `defect > material_finding > unfinished > new` before existing intra-tier ranking.
- Priority, Effort, creation order, and stable identity MUST rank only within the winning tier.
- Selection results MUST expose deterministic tier evidence.
- Triage MUST validate canonical Ready metadata and required issue sections.
- Incomplete Triage remains attention-only with exact machine-readable reasons and stable input fingerprinting.
- Eligible Triage MUST progress only through declared `Triage -> Approved -> Ready` edges.
- Apply MUST be resumable after a partial `Approved` transition and bind provider idempotency to the evaluated fingerprint.
- Public Triage progression MUST mount without modifying the active #625-owned legacy Work tool bundle.

## Acceptance

1. Mixed queues deterministically select defects before findings, unfinished work, and new work.
2. Existing ranking remains deterministic within a tier and higher-tier ineligible work remains excluded normally.
3. Triage produces stable fingerprints, exact attention reasons, and no-op behavior for unchanged incomplete inputs.
4. Valid Triage progresses to Ready through declared command-plane edges; a failure after Approved can be retried safely.
5. Ready admission rejects missing required issue sections and preserves claim/dependency guards.
6. Focused tests, scope check, repository verification, fixed-commit review, CI, merge, and Work closeout pass.

## Risks and recovery

- External Project mutations remain apply-gated and idempotency-keyed.
- Partial progression is recoverable from Approved using the same operation key and fingerprint-bound subkey.
- Ambiguous/incomplete inputs fail closed in Triage with machine-readable attention evidence.

## Out of scope

- #625 live record adapters and legacy project-management tool bundle.
- #544/#545/#547/#546 downstream programme slices.
- Once-through automation and unrelated MCP 2026 work.
