# Change Specification: Work Management View Filter Invariant

- **Change ID**: `166-work-management-view-filter-invariant`
- **Status**: Approved by operator instruction to finish the previously incomplete #270 commissioning scope
- **Complexity**: `medium`
- **Risk Triggers**: `external_action`, `migration`, `public_contract`

## Outcome

Make the canonical 12-view manifest itself satisfy REQ-007, then recommission the live Project from that corrected authority.

## Authority and scope

- Authorities: `AGENTS.md`, `.work/programmes/work-management/target-spec.md`, change 157 REQ-001..REQ-009, issue #270, and `settings/work-management/github-project-schema.json`.
- Change 159 retains exclusive ownership of `SPEC.md`; this change must not touch it.
- Preserve Project items, fields, view identities, and the no-delete/recreate boundary.

## Requirements

- **REQ-001**: Every canonical view filter MUST contain an explicit `status:` qualifier.
- **REQ-002**: Every status named by a canonical view MUST be one of the current canonical `Status` options; legacy `Todo` / `In Progress` MUST therefore be impossible to surface through a canonical filter.
- **REQ-003**: Purpose-specific views retain their narrower lifecycle intent; broad views may enumerate all canonical statuses.
- **REQ-004**: Manifest loading MUST fail closed when REQ-001 or REQ-002 is violated.
- **REQ-005**: Existing semantic/behavioral readback MUST verify the corrected filter against live saved-view items before readiness can return true.
- **REQ-006**: Programme metadata MUST stop claiming #270 is reopened once final live acceptance succeeds.
## Acceptance

1. All 12 manifest filters parse with exactly one canonical `status:` constraint.
2. `Todo` and `In Progress` are absent from every canonical view filter and cannot be admitted indirectly by a missing status qualifier.
3. `01 Inbox` remains `Status=Inbox`; `02`/`03` remain active-flow only; `05 Specification Slices` begins at `Proposed`; `08` remains On Hold/Deferred; `12` remains Done.
4. Fresh schema status before recommissioning reports filter drift where the live Project still carries the old filters.
5. Bounded commissioning updates the existing views in place and a fresh behavioral read returns zero missing, mismatched, or unverified views plus an empty plan.
6. Representative live behavior for `01`, `03`, `08`, and `12` is consistent with the corrected manifest.
7. #270/#142 evidence and Work Management programme metadata reflect the final corrected acceptance before closeout.

## Risks and recovery

- Risk: tightening broad filters may reveal records still stored in unmanaged legacy lifecycle states.
- Recovery: preserve those items and reconcile them separately from evidence; rerunning the commissioner restores view metadata from the checked-in manifest.
- No Project/view deletion or item rewrite is authorized by this change.

## Out of scope

- Removing legacy Status options from the Project schema.
- Blindly remapping ambiguous legacy backlog items.
- `SPEC.md` reconciliation owned by active change 159.
- Native/custom GitHub Project automations.