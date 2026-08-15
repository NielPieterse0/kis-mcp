# Change Specification: Command Plane Live Commissioning Fixes

- **Change ID**: `155-command-plane-live-commissioning-fixes`
- **Status**: Approved for implementation
- **Risk Profile**: standard
- **Development level**: Medium

## Outcome

Make the commissioned Work Management command plane executable live by preserving empty GitHub Project field values as `null` and provisioning the required `Blocked By` dependency field.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `SPEC.md`, `docs/OPERATIONS.md`, command-plane settings, Project schema manifest, live Project #1 evidence from issue #142 commissioning.
- Owned implementation: GitHub Projects adapter normalization and the repository-owned Project schema manifest.
- Owned tests: adapter regression, command-plane/schema contract, commissioner regression if required.
- Documentation: `SPEC.md` and `docs/OPERATIONS.md` only where the schema count/semantics change.
- Excluded: lifecycle redesign, new provider surfaces, arbitrary GraphQL, deletion, unrelated Project item edits.

## Requirements

- **REQ-001**: A Project field-value entry with metadata but no actual value MUST normalize to `None`, not its field name or metadata.
- **REQ-002**: Direct value shapes such as `number`, `text`, `date`, `title`, or iteration title MUST remain supported.
- **REQ-003**: The canonical Project schema MUST provision `Blocked By` as text so queue admission can distinguish observed empty dependency state from unavailable evidence.
- **REQ-004**: Existing Project field/view identities and values MUST be preserved; commissioning remains create-only for the missing field.
- **REQ-005**: Live queue/claim transitions MUST be re-tested after merge on a fresh runtime before #142 can close.

## Acceptance

1. Empty `Execution Owner`, `Verification`, `Review Trigger`, and `Authority Revision` values are observed as `None` rather than their field names.
2. `Blocked By` appears in schema status as a ready text field after bounded commissioning.
3. `project_management_next_work` no longer reports a false `already_claimed:Execution Owner` or `dependency_evidence_unavailable` solely because of these defects.
4. Claim/release/hold/defer/transition/complete command paths can be live-smoked without duplicating the Project item.
5. The Project schema is documented as 25 fields and 12 named views.

## Risks and recovery

- Risk: a provider field-value shape without nested `value` could be accidentally dropped. Regression coverage preserves supported direct scalar keys.
- Risk: schema migration mutates the shared Project. The commissioner is additive/create-only and re-reads before success.
- Recovery: revert the code/config change; the added Project text field is harmless if retained because KIS exposes no schema deletion path.

## Out of scope

- Converting `Blocked By` to a native GitHub dependency relationship.
- Changing command-plane ranking, lifecycle transitions, or authority directions.
- Rewriting historical change 152 lifecycle records.
