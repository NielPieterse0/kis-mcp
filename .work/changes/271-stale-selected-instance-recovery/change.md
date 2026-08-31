# Change: Stale Selected-Instance Recovery

- **Change ID**: `271-stale-selected-instance-recovery`
- **Risk Profile**: small deployment fix

## Outcome

Permit recovery to reclaim a stale process that is unambiguously the selected `kis_mcp.remote_runtime --instance development`, even when its Python executable is noncanonical.

## Acceptance

- Selected-instance identity is distinct from canonical launch provenance.
- Preflight may reclaim only an exact selected-instance runtime identity.
- Unrelated or ambiguous port owners remain blocked.
- Focused tests, exact-head CI, and live `kis-dev` recovery pass.
- `kis-op` runtime availability remains untouched.