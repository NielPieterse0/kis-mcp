# Change: File Materialization Permission

- **Change ID**: `647-file-materialization-permission`
- **Risk Profile**: lean

## Outcome

Expose file materialization as explicit host-owned permission metadata without granting authorization or changing Work policy.

## Scope and acceptance

- Declare `file_materialization` on MCP metadata for `read_file` and `read_multiple_files` only.
- State that authorization is host-owned, default-denied, and persistence is host-managed.
- Do not add a KIS permission store, self-grant path, or fourth Work hard rule.
- Document the boundary as a non-hard control.

## Implementation and verification

- Implementation notes: added a FastMCP list-tools transform that preserves existing metadata and adds one reverse-DNS KIS declaration to file-returning read tools.
- Focused checks: `scripts/test.ps1 -q tests/test_file_materialization.py` passed 3/3 with the locked KIS Python environment.
- Review findings: API-contract re-review returned zero findings after replacing fallback in-place metadata mutation with copy-on-write behavior.
- Residual risk: a host must understand the declared metadata before it can offer a persistent per-server permission; KIS does not control that UI behavior.
- Closeout state: implementation, focused verification, governance check, and review complete; publication pending.
