# Closeout: VirtualBox Disposable Windows Provider

## Implemented scope

- Added disabled-by-default `windows-virtualbox` execution settings/schema/profile and a `VirtualBoxDisposableExecutionProvider` beneath the existing provider-neutral execution contract.
- Forced VirtualBox global state, per-attempt clone state, credentials, and receipts beneath the KIS state boundary; no host checkout/shared-folder/network exposure is introduced.
- Added exact-template and exact-snapshot safety validation, fresh attempt allocation, exact Git archive injection, Guest Additions execution, bounded evidence, and recoverable quarantine retirement.
- Generalized disposable verification proofing across Hyper-V and VirtualBox without changing verification result semantics.
- Added current/target architecture reconciliation and the scoped VirtualBox commissioning runbook for issue #324.

## Validation evidence

- Focused provider/settings/architecture/proof checks: **29 passed**.
- Broader `tests/execution` + `tests/workflows/verification`: **74 passed**.
- Ruff on touched Python/provider tests: **passed**.
- `pwsh -NoProfile -File scripts/change-workflow.ps1 check`: **passed**.
- `git diff --check`: **passed**.
- Pre-publication `pwsh -NoProfile -File scripts/verify.ps1`: **passed**, exit 0; canonical interpreter/dependencies, syntax, governance, configuration, line endings, and full pytest all green.
- Host prerequisite probe: configured `C:\Program Files\Oracle\VirtualBox\VBoxManage.exe` absent and `VBoxManage` not on PATH.

## Review

- Architecture specialist completed clean on the pre-hardening full diff; later specialist code-quality/safety/test-quality calls either timed out or could not invoke because the evidence pack exceeded reviewer limits, requiring the repository-defined exact-diff manual fallback.
- Manual review findings resolved with red/green regressions: failed clone no longer masks its primary provisioning failure as `cleanup_failed`; current template media outside KIS state is rejected; the exact named snapshot is validated for configuration/storage/shared-folder exposure before clone; receipt-write exceptions return `incomplete` instead of escaping the execution-result contract.
- Final manual code-quality, architecture, safety/security, and test-quality review found no remaining blocking issue after those fixes.

## Git and merge

- Branch: `change/180-virtualbox-disposable-windows-provider`
- Worktree: `.work/worktrees/180-virtualbox-disposable-windows-provider`
- Base: local `main` at `4aae9dd30ad3536a84f5a08f805ae149116773e9`.
- Commit: pending publication.
- Pull request or merge: pending exact-head publication/verification.
- Cleanup: pending verified merge.

## Residual items

- Live VirtualBox proof is intentionally not claimed because this host does not currently have `VBoxManage` installed.
- Commissioning still requires supervised VirtualBox installation, KIS-owned template/snapshot creation, purpose-specific guest credentials, synthetic/repeat/failure/performance proof, and the issue #324 real-work programme across the critical parallel-agent backlog plus a registered tool-user repository.
- Hyper-V/VBS coexistence remains a later commissioning comparison point; this change does not modify Hyper-V, VBS, Memory Integrity, Smart App Control, or Defender.
