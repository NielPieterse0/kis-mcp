# Closeout: Serena Capability Boundary

## Implemented scope

- Added a Serena-owned `public_runtime_tools()` projection that accepts only `get_symbols_overview`, `find_symbol`, and `find_referencing_symbols` from upstream runtime metadata.
- Bound the Serena provider descriptor's runtime-tool probe to that filtered projection, preventing unexpected upstream mutation/admin/shell operations from entering KIS capability augmentation.
- Added adversarial regressions proving forbidden Serena operations cannot enter provider runtime discovery, capability search/catalogue projection, or generic dispatch.
- Preserved the existing read-only/offline Serena server visibility boundary and deterministic Discover semantic fallback.

## Validation evidence

- TDD red: three adversarial tests failed on the previous implementation because mutation-capable Serena runtime metadata entered discovery/search and `serena_delete_memory` was dispatchable.
- Focused provider/capability checks: 20 passed using `C:\Projects\.kis-mcp\python-env\Scripts\python.exe`.
- Broader affected provider/capability suite reached 100% passing; the combined command then reported only that `ruff` is not installed as a module in the locked runtime, not a pytest failure.
- `git diff --check`: passed before the implementation commit.
- Governance scope check: passed with exactly the eight owned change paths.
- First reconciled PR head `d0338700185ce1a8ad9c0c141bc2428aef902ebd`: Canonical Verification run `32328694879` completed successfully; this closeout update is intentionally followed by a final exact-head rerun.

## Review

- `safety-security`: completed on working-tree fingerprint `dadd5d8c8facc0fd800df33c81d080b6d285954c23e2508a111bd8f334745d96`, no findings or unknowns.
- `api-contracts`: completed on the same fingerprint, no findings or unknowns.
- Resolution: no blocking findings required code changes.

## Git and merge

- Branch: `change/214-serena-capability-boundary`
- Worktree: `.work/worktrees/214-serena-capability-boundary`
- Implementation commit: `7246ac4ecb57db6f4001602b2b5f5af845e63999`.
- Pull request: #416 (`Close Serena capability leakage (#408)`).
- Final reconciled head / canonical verification / merge / cleanup are recorded by the governed GitHub and Work Management closeout steps after this repository record is frozen.

## Residual items

- No remaining implementation dependency on #403, #407, or #395. No Serena permission broadening is included.
