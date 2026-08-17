# Verification and Governed Changes

> Operator runbook subordinate to [Operations](../OPERATIONS.md). Repository workflow and documentation routing remain in [AGENTS.md](../../AGENTS.md).

## Parallel change worktrees

[`AGENTS.md`](../../AGENTS.md) owns governed-change semantics, scope claims, complexity/risk classification, verification authority, merge requirements, and cleanup rules. This runbook keeps only the operator command sequence.

From a clean primary `main`, create the bounded change:

```powershell
pwsh -File .\scripts\change-workflow.ps1 new 002-example-change `
    --outcome "Implement one bounded result" `
    --complexity small `
    --risk-trigger secrets `
    --owned "src/example/**" `
    --owned "tests/test_example.py" `
    --exclude "policy/**"
```

Inspect or validate registered claims:

```powershell
pwsh -File .\scripts\change-workflow.ps1 list
pwsh -File .\scripts\change-workflow.ps1 validate
```

Before publication, run from the change worktree:

```powershell
pwsh -File .\scripts\change-workflow.ps1 check
```

After verified merge, return to clean primary `main` and run:

```powershell
pwsh -File .\scripts\change-workflow.ps1 cleanup 002-example-change
```

Use [`AGENTS.md`](../../AGENTS.md) rather than this runbook when deciding whether a change is governed, how paths may be claimed, what evidence is authoritative, or whether cleanup/merge is permitted.

The speculative GitHub Actions-backed landing queue is dormant and is not a canonical delivery path. Its implementation and smoke script remain for bounded diagnostics only; do not use them to satisfy merge readiness.

## Verify

During development, run only the focused/affected checks needed for the current change. Before publication, complete the governed scope check. After the pull request is published/reconciled, run the canonical full repository verification locally through KIS against the exact current pull-request head and retain its concrete evidence reference for Work Management merge readiness.

Run the canonical verifier from that exact-head checkout/worktree:

```powershell
pwsh -File .\scripts\verify.ps1
```

`scripts/verify.ps1` and `scripts/verify.py` own the current executable verification sequence, dependency/runtime requirements, and checks. Do not maintain a parallel checklist or pinned dependency inventory in this runbook.

Verification is evidence, not an additional permission rule, and deterministic repository verification does not replace explicit live provider commissioning when live evidence is required.
