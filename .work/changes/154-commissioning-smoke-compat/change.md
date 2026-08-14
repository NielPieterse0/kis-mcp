# Change: Commissioning Smoke Compat

- **Change ID**: `154-commissioning-smoke-compat`
- **Risk Profile**: lean

## Outcome

Restore documented shared-runtime GitHub and Supabase commissioning smokes while preserving the current no-argument Context7/Serena smoke.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Preserve the no-argument Context7/Serena smoke.
- Restore positional `github` and `supabase` shared-runtime commissioning through the curated gateway.
- Verify required provider operations through capability discovery and `execute_external_action`; do not invoke mutation operations.

## Implementation and verification

- Implementation notes: restored provider dispatch in `scripts/run-provider-live-smoke.py` and aligned shared-runtime checks with progressive exposure.
- Focused checks: Python compile, 11/11 focused artifact tests, `git diff --check`, and `change-workflow.ps1 check` pass.
- Live acceptance: Context7/Serena no-argument smoke, Supabase `-SharedRuntime`, and GitHub `-RequireLive` all pass.
- Review findings: final NVIDIA code-quality and required API-contract reviews report zero findings.
- Residual risk: none known within this bounded compatibility change; parent commissioning findings are tracked separately by #261 and #262.
- Closeout state: ready for commit, PR CI, merge, and post-merge commissioning.
