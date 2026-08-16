# Change Specification: Disposable Windows Execution Foundation

- **Change ID**: `174-disposable-windows-execution-foundation`
- **Status**: Approved for implementation
- **Complexity**: Large
- **Risk triggers**: architecture boundary, deployment, persistent state, security

## Outcome

Establish the provider-neutral execution-backend contract and one disposable Windows Hyper-V proof path for clean KIS verification without changing canonical GitHub Actions routing.

## Authority and scope

- Repository authority: `AGENTS.md` → `docs/TRUST-MODEL.md` → `SPEC.md` → `docs/PLATFORM-CONCEPT.md` → policy/settings.
- Roadmap/work identity: GitHub issue `#324`, Work Management `SPEC-324`.
- Exact path ownership and exclusions: `scope.json`.
- Detailed multi-slice sequence: `roadmap.md`.
- `.github/workflows/**` is intentionally excluded from this first slice.
- `SPEC.md` is now included only for bounded current-product reconciliation. Change 171 released the path when PR `#312` merged; this does not widen change 174 into workflow routing, runner registration, scale-set integration, or other later roadmap slices.

## Requirements

- **REQ-001**: Define immutable provider-neutral execution backend/profile/result contracts without changing existing verification declaration or result semantics.
- **REQ-002**: Keep current local process verification working through the new abstraction.
- **REQ-003**: Define a Windows disposable-executor profile with exact source identity, image/toolchain provenance, bounded lifecycle/evidence receipts, and explicit incomplete/failure outcomes.
- **REQ-004**: Implement one Hyper-V proof path that does not mount mutable host checkout, KIS runtime state, operator profile, or secrets into the guest by default.
- **REQ-005**: Provide an executable supervised Hyper-V proof entry point that can run an existing declared verification and fail closed when live host capability or required evidence is unavailable. Live commissioning and parity/performance measurements are tracked separately in follow-up issue `#330`.
- **REQ-006**: Treat lifecycle/readiness/backend selection as execution semantics only; HR-001/HR-002/HR-003 remain the complete Work policy decision set.
- **REQ-007**: Do not integrate GitHub runner registration, `actions/scaleset`, canonical workflow migration, or `import-isolate` behavior in this slice.

## Acceptance

1. Existing local verification tests pass unchanged or with contract-preserving adapter updates.
2. A disposable guest request binds exact project/source/image/profile identities before execution.
3. Successful guest evidence includes source identity, image/toolchain provenance, duration, exit/result state, and bounded diagnostics.
4. Timeout, startup failure, stale/mismatched identity, or missing evidence cannot return `passed`.
5. Focused unit/integration tests cover backend selection, lifecycle failures, source mismatch, evidence bounds, and cleanup semantics.
6. The supervised Hyper-V proof entry point is executable, binds exact source/provenance, refuses unsupported hosts or incomplete evidence, isolates guest networking before execution, and uses recoverable retirement semantics. Live host commissioning is follow-up issue `#330`, not a merge-blocking acceptance criterion for this implementation slice.
7. Architecture and safety/security reviews have no unresolved blocking findings.
8. `scripts/change-workflow.ps1 check`, `git diff --check`, focused verification, and applicable repository verification pass on the final slice state.

## Risks and recovery

- Hyper-V availability or nested virtualization may differ by Windows edition/host configuration; expose readiness rather than assuming support.
- Guest lifecycle operations can strand disks/VM state; use deterministic names, bounded state roots, and recoverable cleanup/quarantine semantics.
- Environment parity can drift from hosted CI; pin image/toolchain identity and do not migrate canonical CI until a later parity slice proves equivalence.
- Recovery for this slice is removal/disablement of the new execution profile while retaining the existing local-process verification backend.

## Out of scope

- GitHub Actions workflow routing changes.
- GitHub runner/App registration or scale-set operation.
- `import-isolate` repository changes or Docker containment changes.
- Replacing existing exact-head Actions landing authority.
