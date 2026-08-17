# Change Specification: Local Verification Landing Authority

- **Change ID**: `179-local-verification-landing-authority`
- **Status**: Approved for implementation
- **Complexity**: medium
- **Risk triggers**: `architecture_boundary`, `public_contract`

## Outcome

Replace GitHub Actions as repository landing authority with KIS-owned local exact-head verification plus exact registered GitHub pull-request identity, so governed delivery can continue without GitHub Actions while preserving verification quality and fail-closed merge behavior.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, the existing `prepare_reviewable_pull_request` exact-source/reconciliation contract, `ImplementationTrace`, and the exact-head registered GitHub merge primitive.
- Owned paths: the authority/documentation, workflow descriptors, Work Management merge-readiness logic, focused tests, the minimal `tests/execution` package marker, and the project-management package import-order correction declared in `scope.json`.
- Baseline prerequisites discovered after runtime restart: merged `main` cannot collect the full pytest suite because the bare `tests/execution` directory introduces duplicate top-level test module names, and the project-management package initializer exposes a pre-existing circular import through the merge-queue capability path. This change may repair only those verification blockers without changing execution-provider or merge-queue runtime behavior.
- Excluded paths: `.github/workflows/**`; this slice does not delete or repurpose historical workflow files.
- Dependencies: change 174 is merged on `main` at `b68da37a8269dd7c4e9523a3db0c5b9a279e1f11`.
- Integration owner: none.

## Requirements

- **REQ-001 — Canonical local landing evidence:** A pull request is merge-ready only when a passing local KIS verification record targets the exact current pull-request head and has a concrete evidence reference. Provider-native GitHub Actions evidence is neither required nor sufficient as the canonical landing gate.
- **REQ-002 — Exact-head GitHub identity remains mandatory:** Landing must continue through `kis_github_merge_registered_pull_request` with the explicitly approved pull-request head SHA; no loose branch merge or unchecked remote mutation is introduced.
- **REQ-003 — Verified publication remains bounded:** `prepare_reviewable_pull_request` remains the pre-publication path that verifies the immutable source commit before exact-tree reconciliation and PR creation. Closeout re-verifies the reconciled exact PR head locally before merge rather than assuming commit-SHA equivalence.
- **REQ-004 — Work Management remains provider-neutral:** `VerificationEvidence` retains its existing provider-neutral contract. Merge readiness accepts the canonical local source without adding GitHub-specific structure to the domain model.
- **REQ-005 — Actions-dependent queue paths are retired from canonical delivery:** Workflow descriptors must not recommend the speculative Actions-backed landing queue as the repository completion path while Actions are abandoned. Existing queue implementation/history may remain dormant and out of scope.
- **REQ-006 — Documentation authority is reconciled:** `AGENTS.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, and the verification runbook must describe local KIS exact-head verification as canonical landing evidence and GitHub as the exact PR/merge control plane, not the verification executor.

## Acceptance

1. **Given** an open PR with exact-head passing `source=local` verification and a concrete evidence reference, **When** merge readiness is evaluated, **Then** verification does not block landing.
2. **Given** an open PR with only GitHub Actions verification, stale local verification, failed local verification, or local verification without a reference, **When** merge readiness is evaluated, **Then** landing fails closed.
3. **Given** the platform and Work Management workflow catalogue, **When** completion workflows are inspected, **Then** normal PR closeout requires local exact-head verification and does not require `github_actions_list`/`github_actions_get`.
4. **Given** the repository authority docs, **When** an implementation agent prepares and lands a change, **Then** canonical repository verification is executed locally/KIS on the exact reconciled PR head before the exact-head GitHub merge.
5. Focused tests, full repository verification, change scope check, and diff check pass on the final exact change commit.

## Risks and recovery

- Risk: accepting generic or stale local evidence could weaken the former CI gate. Mitigation: require exact PR-head revision, `passed`, canonical local source, and non-empty evidence reference; preserve the exact-head merge primitive.
- Risk: double verification (source commit before publication and reconciled head before merge) costs time. This is intentional for the unblock slice; later tree-identity receipt reuse may remove the duplicate run only with an explicit typed proof contract.
- Recovery: revert this change to restore the previous Actions-dependent descriptors/readiness rule. No GitHub workflow files, execution-provider state, or remote repository settings are mutated by this slice.

## Out of scope

- Windows VM provider implementation or commissioning (#330 and successor substrate work).
- `.github/workflows/**` deletion or cleanup.
- GitHub runner installation, `actions/scaleset`, or hosted/self-hosted Actions routing.
- Speculative merge-queue redesign for a non-Actions verifier.
- Tree-equivalence receipt optimization between source verification and reconciled PR-head verification.
