# Change: Promotion Conditional Candidate Identity

- **Change ID**: `618-promotion-conditional-candidate-identity`
- **Risk Profile**: lean

## Outcome

Make PromotionReady candidate identity conditional on declared live-candidate obligation.

## Scope and acceptance

- Typed obligations remain authoritative: candidate identity/live proof is required only when `live_candidate_verification` is declared or required for an MCP surface.
- Non-candidate promotion resolves the existing governed Change ID/worktree from Work authority; it does not launch a runtime solely to carry source-path identity.
- MCP/live-candidate flows retain exact candidate owner, source binding, runtime identity, and live-evidence checks.
- No new lifecycle state, gate, checkpoint, or parallel promotion workflow is introduced.

## Implementation and verification

- Implementation notes: made `PromotionReadyHandoff`, derivation, and convergence conditional on the live-candidate obligation; non-candidate source authority comes from the exact Project Change ID plus governed worktree scope.
- Focused checks: `tests/workflows/once_through/test_once_through.py` passed 41 tests through the managed KIS interpreter; governed scope check passed; `git diff --check` is clean. A worktree-local `uv` environment was blocked by Windows Application Control and was not used as verification authority.
- Review findings: NVIDIA code-review invocation returned upstream 502; bounded manual exact-diff fallback found no blocker and confirmed MCP paths remain fail-closed.
- Residual risk: exact-head GitHub Actions remains the canonical full repository verification gate.
- Closeout state: implementation complete; awaiting commit, exact-head Actions, merge, Work reconciliation, and cleanup.
