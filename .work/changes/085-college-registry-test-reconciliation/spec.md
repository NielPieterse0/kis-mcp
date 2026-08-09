# Change Specification: College Registry Test Reconciliation

- **Change ID**: `085-college-registry-test-reconciliation`
- **Status**: Active
- **Risk Profile**: lean

## Outcome

Reconcile stale checked-in registry expectations with the already-merged `college` project registration.

## Requirements

- Update only stale test expectations.
- Preserve the registered `college`, `gpt-os`, and `kis-mcp` bindings.
- Do not change registry implementation or settings.

## Acceptance

1. The two previously failing registry tests pass.
2. The focused project-registry test files pass.
3. Scope check and canonical verification pass.
