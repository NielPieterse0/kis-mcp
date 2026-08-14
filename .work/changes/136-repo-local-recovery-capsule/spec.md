# Change Specification: Repo Local Recovery Capsule

- **Change ID**: `136-repo-local-recovery-capsule`
- **Status**: Approved for implementation by operator request
- **Risk Profile**: rigorous
- **Complexity**: large
- **Risk triggers**: `persistent_state`, `architecture_boundary`, `public_contract`

## Outcome

Add a validated, reconstructible repo-local KIS recovery capsule beneath each registered project's own `.temp\kis` directory. The capsule accelerates recovery and provides worktree-aware checkpoints without replacing repository, Git, checked-in configuration, external-provider truth, or central `C:\Projects\.kis-mcp` state.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`.
- Persistence primitive: reuse `kis_mcp.evidence.EvidenceStore`; do not introduce an independent store.
- Capsule root: `<registered project local_root>\.temp\kis`.
- Worktree separation: one immutable generation namespace per worktree identity.
- `AGENTS.md` remains untouched because active change 125 owns it; this slice stays within the existing permission for explicitly needed repo `.temp` data and keeps authoritative platform state central.

## Requirements

- **REQ-001**: A registered project MUST derive its capsule root from the registry `local_root`, never from ambient working-directory state.
- **REQ-002**: Capsule state MUST be disposable and reconstructible; it MUST NOT authorize projects, providers, repositories, credentials, network access, or destructive actions.
- **REQ-003**: Reuse MUST validate project ID, registered root, worktree identity, Git revision/status, source fingerprint, and settings/provider fingerprints supplied by the caller.
- **REQ-004**: Stale identity MUST be reported as stale and ignored rather than silently reused.
- **REQ-005**: Corrupt current pointers or artifacts MUST be retained as recovery evidence and replaced only by a fresh validated generation.
- **REQ-006**: Parallel worktrees MUST use distinct namespaces so agents cannot overwrite each other's current checkpoint.
- **REQ-007**: The capsule MUST support bounded idempotent operation checkpoints that distinguish started, completed, and conflicting reuse of an idempotency key.

- **REQ-008**: Discover persistence MUST publish a local recovery hint only after a central EvidenceStore generation is valid, and local hints MUST never override central evidence.
- **REQ-009**: Absence of a capsule MUST preserve existing behavior and trigger deterministic reconstruction on the next eligible operation.
- **REQ-010**: Capsule payloads MUST use fixed schemas and hashes; arbitrary caller metadata or secrets MUST NOT be persisted.
- **REQ-011**: Capsule publication MUST keep `.temp\kis` invisible to Git without modifying the repository's tracked ignore policy; KIS owns a capsule-local `.gitignore` containing `*` and fails local publication rather than overwriting an incompatible existing marker.

## Acceptance

1. **Given** a registered repo such as `commodity`, **when** project intelligence is persisted, **then** its own `.temp\kis` contains a bounded recovery generation pointing to the verified central Discover generation.
2. **Given** an unchanged worktree and fingerprints, **when** the recovery capsule is read, **then** it reports current and returns the matching central generation hint.
3. **Given** changed Git/settings/source/worktree identity, **when** the capsule is read, **then** it reports stale and does not authorize reuse.
4. **Given** two worktrees for one registered project, **when** both checkpoint, **then** their namespace/current pointers are independent.
5. **Given** a corrupt capsule pointer or artifact, **when** it is read, **then** corruption is retained and a fresh checkpoint can be published.
6. **Given** a repeated operation idempotency key with the same request fingerprint, **when** the checkpoint is completed, **then** a retry recognizes completion; a different request fingerprint is rejected as a conflict.
7. **Given** no repo-local capsule, **when** existing Discover runs, **then** central persistence and result semantics remain backward compatible.
8. **Given** a registered Git repository that does not already ignore `.temp`, **when** KIS first publishes a capsule, **then** `.temp\kis` remains invisible to `git status` without changing the tracked repository ignore policy.
9. Focused tests, change-scope validation, repository verification, exact-head CI, documentation reconciliation, merge, Work Management `Done`, and cleanup all succeed.

## Risks and recovery

- Risk: local cache becomes a second truth. Mitigation: typed identity-only payloads, explicit central-generation hints, and validation before every reuse.
- Risk: parallel agents race. Mitigation: worktree-derived namespaces and EvidenceStore immutable generations/CAS.
- Risk: corrupt local state blocks tools. Mitigation: retain corrupt pointer as recovery evidence and rebuild; local state is never required for correctness.
- Recovery: delete/quarantine `<repo>\.temp\kis`; all capsule content is reconstructible from authoritative sources and central evidence.

## Out of scope

- Moving Serena, provider credentials, Work Management authority, or central Discover generations into repo-local state.
- Using capsule content to approve GitHub repositories, provider access, policy decisions, or permanent deletion.
- Fixing unrelated registry/Project binding defects or runtime process-health reconciliation.
