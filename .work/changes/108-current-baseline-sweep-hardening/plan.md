# Current Baseline Sweep Hardening Implementation Plan

1. Reconcile authority, local/GitHub state, operator approvals, and current-vs-target claims.
2. Reproduce and fix live regressions with tests first.
3. Add stable KIS runtime identity/transport fingerprints and bounded call correlation.
4. Harden nested project resolution and explicit project identity.
5. Validate and repair Control Center content, commissioning evidence, and responsive UI.
6. Reconcile stale current documentation without rewriting historical evidence.
7. Run changed-area tests, seven-slice/P5 live smokes, canonical verification, review, exact GitHub PR/merge, and governed cleanup.

Constraints: preserve the central stateless two-instance design, exact HR-001/002/003 policy, no secrets/payload telemetry, no unrelated authority expansion.