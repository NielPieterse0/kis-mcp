# Change: Serena Exact Verification Test Isolation

- **Change ID**: `183-serena-exact-verification-test-isolation`
- **Risk Profile**: lean

## Outcome

Isolate the Serena normalization unit test from durable provider project state so repeated exact-head verification workspaces cannot collide through the shared workspace folder name.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- The Serena normalization unit test must not write to the durable provider project-data root.
- Existing same-folder-name collision protection must remain covered and unchanged.

## Implementation and verification

- Implementation notes: The normalization test now derives `install_root` and `project_data_root` from `tmp_path`; production Serena settings and collision behavior are unchanged.
- Focused checks: Exact-head canonical verification for PR #345 reproduced the stale `workspace` collision; the isolated normalization test plus the existing collision-protection regression pass together after the fix.
- Review findings: Pending final diff review.
- Residual risk: None identified beyond the normal full-repository verification gate.
- Closeout state: Active; prerequisite landing required before retrying PR #345.
