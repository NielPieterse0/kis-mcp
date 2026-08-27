# Change Specification: Provider Project State Identity

- **Change ID**: `255-provider-project-state-identity`
- **Status**: Implemented
- **Risk Profile**: persistent-state migration

## Outcome
Route correctness-sensitive provider/project integration evidence through the canonical KIS state ownership contract while preserving globally safe provider authority and retaining legacy state for recovery.

## Authority and scope
- Repository authority: `AGENTS.md`.
- State authority: `contracts/state/state-ownership.contract.json` via `StateNamespaceResolver`.
- Work authority: GitHub issue #556 under #548/#491.
- Owned consumers: provider commissioning evidence, DBHub generated runtime configuration, and Serena project-data identity.
- Runtime receipt state was completed separately by Change 254 / #555.

## State inventory
- DBHub commissioning evidence: `durable-evidence`, keyed by KIS project/source identity.
- DBHub generated TOML: `reconstructible-cache`, keyed by database project plus KIS source identity.
- Serena project-data identity: `reconstructible-cache`, keyed by registered project plus source identity; provider-generated cache remains provider-managed.
- Docker Hub commissioning: global provider installation/auth/tool identity; explicit global exemption.
- DBHub/Serena installations, Serena global config/cache/log/temp/language-server/global-memory, shared auth/vault, registry/config authority, and quarantine: explicit global exemptions and unchanged.
## Requirements
- **REQ-001**: Reuse the existing canonical state ownership/identity resolver; no provider-specific namespace model may become authority.
- **REQ-002**: DBHub commissioning evidence and generated runtime configuration must not be reusable across linked KIS sources.
- **REQ-003**: Exact legacy DBHub commissioning evidence may be copied into canonical ownership only when its full identity validates; legacy evidence remains retained.
- **REQ-004**: Serena may retain its upstream folder-template cache layout, but KIS must bind reuse to canonical registered project/source identity.
- **REQ-005**: Exact legacy Serena root markers may establish canonical identity; unmarked, malformed, mismatched, or ambiguous provider cache is retained but rejected.
- **REQ-006**: Global provider installations, caches, configuration, reusable authentication, registry authority, and quarantine remain unchanged.
- **REQ-007**: Provider readiness remains deterministic after restart and legacy recovery.

## Acceptance
1. Main and governed worktree DBHub commissioning roots resolve to distinct canonical durable-evidence namespaces.
2. DBHub generated TOML resolves to canonical reconstructible-cache ownership and remains idempotent.
3. Docker Hub commissioning stays on the intentionally global provider evidence root.
4. Serena writes a canonical project/source identity marker before using provider project cache, recovers exact legacy identity, and rejects ambiguous or mismatched legacy state without deletion.
5. Cross-source/provider tests, governed verification, specialist review, exact-head CI, and live commissioning pass before #556 completes.

## Risks and recovery
- Risk: legacy evidence could be mistaken for current source evidence. Mitigation: exact identity validation before copying or reuse.
- Risk: Serena's upstream `$projectFolderName` cache layout can collide. Mitigation: canonical source marker plus retained local collision marker; ambiguity fails closed.
- Risk: global provider state could be needlessly fragmented. Mitigation: explicit exemptions for installations/auth/config/global caches and Docker Hub commissioning.
- Recovery: revert Change 255. Legacy state is never permanently deleted; canonical provider evidence/cache can be reconstructed or retained for diagnosis.

## Out of scope
- Runtime-instance receipts/checkpoints completed by #555.
- Shared authentication/vault migration.
- Changes to the canonical state ownership contract itself.
