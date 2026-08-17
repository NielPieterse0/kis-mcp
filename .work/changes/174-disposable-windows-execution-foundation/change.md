# Change: Disposable Windows Execution Foundation

- **Change ID**: `174-disposable-windows-execution-foundation`
- **Risk Profile**: large; architecture boundary, deployment, persistent state, security
- **Roadmap owner**: GitHub issue `#324` / Work Management `SPEC-324`

## Outcome

Establish a provider-neutral execution-backend contract plus one disposable Windows Hyper-V proof path for clean KIS verification, without changing canonical GitHub Actions routing in this slice.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Preserve existing verification selection/result semantics and current local-process execution as a supported backend.
- Define bounded runner profiles, readiness, image/toolchain provenance, lifecycle state, evidence receipts, and fail-closed incomplete execution semantics.
- Implement and deterministically verify one disposable Windows execution path that receives an exact source revision, avoids mutable host KIS/dev state, executes a declared verification through the proof harness, returns bounded evidence, and retires guest state recoverably. Live Hyper-V commissioning is tracked separately in follow-up issue `#330`.
- Do not migrate `.github/workflows/**`, install a persistent runner on the physical development host, or integrate `import-isolate` in this first slice.
- Runner/backend selection must remain execution eligibility/configuration and must not create a fourth Work hard rule.
- Keep GitHub MCP and provider-native Actions evidence as the GitHub authority/landing plane.

## Implementation and verification

- Detailed programme sequence: `roadmap.md`.
- First implementation gate: contract + Hyper-V proof + focused tests + architecture/security review.
- Canonical CI migration is a later phase after parity is demonstrated.
