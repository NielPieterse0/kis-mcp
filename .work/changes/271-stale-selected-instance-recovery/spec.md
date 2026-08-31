# Change Specification: Stale Selected-Instance Recovery

- **Change ID**: `271-stale-selected-instance-recovery`
- **Status**: Active
- **Complexity**: small
- **Risk triggers**: deployment

## Requirements

- **REQ-001**: identify selected runtime ownership from the exact `kis_mcp.remote_runtime --instance <name>` command line independently of Python provenance.
- **REQ-002**: retain canonical interpreter checks for newly launched runtime validation.
- **REQ-003**: preflight may reclaim stale selected-instance processes but must reject unrelated port owners.
- **REQ-004**: live recovery must restart only `kis-dev` onto landed `main`.