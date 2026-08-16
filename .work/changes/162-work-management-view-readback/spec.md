# Change Specification: Work Management View Readback

- **Change ID**: `162-work-management-view-readback`
- **Status**: Approved by operator instruction to continue #270 commissioning
- **Complexity**: `medium`
- **Risk Triggers**: `external_action`, `migration`, `public_contract`

## Outcome

Repair live GitHub Project saved-view verification so #270 cannot report ready until all 12 canonical views both store the declared semantics and return records consistent with their saved filters.

## Authority and scope

- Authorities: `AGENTS.md`, `SPEC.md`, `.work/programmes/work-management/target-spec.md`, `settings/work-management/github-project-schema.json`, GitHub issue #270, and current GitHub Project API contracts.
- Preserve the registered Project, view identities, item identities, and additive/no-delete commissioning boundary.
- Do not touch `SPEC.md` while active change 159 owns it.
- Production scope is the registered-Project semantic reader/commissioner plus focused regressions.

## Requirements

- **REQ-001**: Every observed canonical view MUST retain its live Project view number in addition to node identity, name, layout, and stored semantic configuration.
- **REQ-002**: Stored filter/configuration equality alone MUST NOT establish live acceptance for a canonical filtered view.
- **REQ-003**: The bounded client MUST query GitHub's saved-view item endpoint for the exact observed view number and treat that result as behavioral evidence that the saved filter is active.
- **REQ-004**: Behavioral verification MUST request only the manifest-referenced fields required to evaluate the declared filter and MUST remain fixed-shape and bounded.
- **REQ-005**: A returned item that contradicts a declared supported filter MUST make that view unready and MUST prevent commissioner success.
- **REQ-006**: A filtered view whose behavioral result cannot be observed completely MUST be unverified, never ready by assumption.
- **REQ-007**: Existing-view layout, filter, and visible-field drift MUST be repaired in place through GitHub's documented `updateProjectV2View` input. Existing sort, group, or vertical-group drift MUST fail explicitly because those dimensions are not exposed by the current update input. The commissioner MUST NOT delete/recreate an existing view.
- **REQ-008**: Missing views MAY be created with complete manifest semantics through GitHub's documented Project Views create API. After any supported mutation, verification MUST independently re-read stored semantics and behavioral view items before returning `ready=true`.
- **REQ-009**: `01 Inbox` acceptance MUST prove the saved view returns no non-Inbox item; current independent Project query evidence shows zero Inbox records.
- **REQ-010**: Legacy `Todo` / `In Progress` records remain a separate data-reconciliation step; they MUST NOT be silently admitted to canonical view acceptance.

## Acceptance

1. A regression reproduces the false-green case: stored `status:Inbox` plus a saved-view item carrying another Status cannot return ready.
2. View identity includes the GitHub view number required by the saved-view-items API.
3. Behavioral verification reads at most one 100-item page, marks any `rel="next"` response unverified, rejects malformed/blank evidence, and evaluates only the supported canonical filter grammar.
4. Existing layout/filter/visible-field drift is repaired in place through documented GitHub view-update semantics; sort/group/vertical-group drift remains explicit and unready; missing-view creation remains bounded and non-destructive.
5. Fresh live commissioning reports ready only after all 12 stored semantics and behavioral probes pass.
6. Live `01 Inbox` returns no non-Inbox items; representative `03 Delivery Board`, `08 Holds and Deferred`, and `12 Completed` are behaviorally consistent with their declared filters.
7. #270 remains open until exact-head CI, merge, fresh-runtime commissioning, legacy-state reconciliation, and final operator acceptance are complete.

## Risks and recovery

- GitHub saved-view item pagination could exceed the bounded evidence budget; fail unverified rather than truncate to ready.
- Some view filters may use dimensions not exposed by Project field values; support only the canonical manifest grammar and fail explicitly on an unevaluable qualifier.
- Recovery is idempotent rerun against the checked-in manifest; no destructive Project operation is added.

## Out of scope

- Native/custom Project automation, intake mutation, or review-import mutation.
- Removing legacy Status options.
- Native GitHub dependency relationships replacing `Blocked By`.
- Rewriting unrelated Project records without evidence-backed reconciliation.
