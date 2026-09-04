# Change Specification: Historical Scope Compatibility

- **Change ID**: `640-historical-scope-compatibility`
- **Status**: Active
- **Complexity**: medium

## Outcome

Allow current KIS change-governance reads to consume historical schema-v4 scope records created under earlier KIS contracts without weakening strict creation or checking of current schema-v4 scopes.

## Requirements

- Current `ChangeClaim.from_mapping` remains strict by default.
- Current `check` resolves only the active `change/<id>` scope and parses it strictly.
- Historical file loading may project earlier schema-v4 omissions into a read-compatible in-memory claim.
- Compatibility projections never rewrite repository scope files.
- Missing historical path ownership projects only to that change's own `.work/changes/<id>/**` record.
- Noncanonical historical dependency tokens do not gain modern coordination authority.
- Missing historical Work record IDs derive from the source issue number; missing documentation impact becomes `not_assessed`.
- Unknown historical risk labels remain evidence labels only; current risk-trigger creation remains closed to configured values.

## Acceptance

1. Historical commodity schema-v4 variants load without blocking unrelated current change checks.
2. A malformed current schema-v4 scope is still rejected by current-change `check`.
3. Commodity #289 passes the modified KIS `check` at its exact current source.
4. Existing change-governance tests remain green.

## Out of scope

- Rewriting historical repository records.
- Automatically closing or deleting old branches/worktrees.
- Weakening current change creation, scope ownership, or merge/cleanup rules.
