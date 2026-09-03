# Plan

1. Preserve the existing shared scan-wide mutation ceiling and whole-scan failure semantics.
2. Order bounded discovered candidates newest-first before candidate processing.
3. Update runtime tests to assert newest-first ordering across success, retryable failures, read budgets, and mutation exhaustion.
4. Document newest-first processing in the commissioning runbook.
5. Run focused/full commissioning verification, governance checks, independent review, exact-head CI, and governed landing.
