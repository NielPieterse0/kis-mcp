# Roadmap: Disposable Windows Execution

## Goal

Create one reusable KIS execution substrate for clean Windows verification and isolated workload execution. It should reduce CI quota dependence, slow-network setup cost, environment contamination, and parallel-agent contention without weakening current verification or merge gates.

## Architectural shape

```text
KIS workflows / verification
        |
ExecutionBackend + runner profile
        |
Disposable Windows executor (Hyper-V)
        |-------------------------------|
        |                               |
clean local verification         GitHub Actions runner
                                        |
                                  actions/scaleset
```

`import-isolate` reuses the same outer Windows executor later while retaining Docker as its inner containment layer.

## Phase 1 — execution contract

- Generalize the existing verification `Runner` seam into explicit execution backends/profiles.
- Preserve existing verification declaration, selection, fingerprint, and result contracts.
- Keep `local-process` as a supported backend.
- Add bounded readiness, lifecycle, image/toolchain provenance, duration, and evidence receipt contracts.
- Fail incomplete/timeout/lifecycle errors closed for verification evidence without converting them into HR policy decisions.

## Phase 2 — disposable Windows proof

- Implement a Hyper-V-backed disposable Windows executor using a versioned golden image.
- Inject only exact source/configuration inputs required by the selected verification.
- Do not mount the physical development checkout, KIS state root, user profile, or application vault into the guest.
- Extract bounded logs/results/provenance before guest reset or destruction.

## Phase 3 — fast clean verification

- Promote the Phase 2 Hyper-V proof executor into the reusable `windows-clean` verification profile; this phase productizes the same executor rather than introducing a second implementation.
- Pre-bake Python, PowerShell, Git, uv, pinned tooling, and safe dependency caches.
- Prefer offline execution after exact source transfer; use small Git deltas or a local object seed where practical.
- Support bounded parallel guests so concurrent slices do not share mutable verification state.
- Benchmark startup, setup, verification duration, and transferred bytes against the existing local/hosted path.

## Phase 4 — GitHub Actions runner

- Run the official OSS `actions/runner` inside the disposable guest.
- Register repository-scoped ephemeral runners under a dedicated KIS label/profile.
- Preserve native GitHub check runs, exact-head SHA identity, annotations, logs, required checks, and merge-readiness evidence.
- Do not install the canonical runner directly on the physical KIS development host.

## Phase 5 — `actions/scaleset`

- Pin an exact reviewed `actions/scaleset` revision behind a narrow adapter.
- Prefer repository-bounded GitHub App credentials for scale-set orchestration.
- Translate demand/JIT runner configuration into Hyper-V guest lifecycle requests.
- Support scale-to-zero, bounded concurrency, drain, cleanup, and explicit failure/quarantine evidence.
- Keep low-level scale-set mechanics behind KIS workflows rather than exposing a large public tool surface.

## Phase 6 — canonical CI migration

- Prove parity between hosted `windows-latest` and the new ephemeral Windows runner before changing canonical routing.
- Move `Canonical Verification` to the approved ephemeral label only after parity and failure-mode tests pass.
- Keep GitHub-hosted Windows as an optional fallback profile when quota/cost policy permits it.
- Preserve provider-native exact-head Actions success as the authoritative landing gate.

## Phase 7 — shared execution uses

- Reuse the substrate for provider upgrade/commissioning clean rooms and dependency-update validation.
- Reproduce CI failures from image revision + source SHA + verification identity instead of relying on workstation state.
- Use separate guests for parallel-agent verification where host capacity allows.
- Add high-risk `import-isolate` profiles that run its existing Docker/Defender workflow inside a disposable Windows VM.
- Keep Docker as the inner purpose-specific containment layer; Hyper-V protects the physical host and supplies whole-environment disposal.

## Quality and safety invariants

- No reduction in current verification, review, Work Management, or merge gates.
- GitHub MCP remains the GitHub control/authority plane; runner orchestration remains an execution-plane implementation.
- Exact source identity and runner/image provenance must be present in successful verification evidence.
- Guest execution must not inherit mutable host credentials, KIS runtime state, or development checkout state.
- Runner readiness/profile selection must not authorize Work effects or create a fourth hard rule.
- VM lifecycle failure, stale image identity, source mismatch, or missing evidence must never be reported as a passing verification.
- Additional autoscaling complexity is justified only after the simpler disposable executor proves measurable reliability or speed benefits.

## Slice sequence

1. `174-disposable-windows-execution-foundation`: execution contracts + implemented/tested Hyper-V proof path.
2. `#330`: supervised live Hyper-V commissioning, contract-parity proof, and startup/setup/verification/network measurements.
3. Follow-up: clean local Windows verification profile and measured low-bandwidth/cache optimization.
4. Follow-up: official `actions/runner` ephemeral guest integration.
5. Follow-up: pinned `actions/scaleset` adapter and bounded autoscaling.
6. Follow-up: canonical workflow migration after parity evidence.
7. Follow-up: reusable commissioning/dependency/CI-reproduction profiles.
8. Follow-up in the owning repository: `import-isolate` outer-VM containment integration and nested-virtualization commissioning.
