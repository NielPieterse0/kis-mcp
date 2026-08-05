# Change Specification: Documentation Reconciliation

- **Change ID**: `039-documentation-reconciliation`
- **Status**: Approved for implementation by the operator request on 2026-08-05
- **Risk Profile**: rigorous

## Outcome

Audit every tracked Markdown document, compare current-state claims with the repository implementation and higher-authority documents, and reconcile the owned documentation so it is current, internally consistent, concise, machine-readable, and explicit about current, internal, target, and historical states.

## Authority and scope

- Authoritative sources, in order: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, and `docs/OPERATIONS.md`.
- Source evidence: current `origin/main` implementation, tests, settings, recent merged change records, and the operator-provided documentation audit.
- Owned paths: the paths declared in `scope.json`.
- Excluded active conflicts: the dirty operator approval register, the active Discover final-integration specification, canonical settings owned by the secrets slice, executable code, tests, contracts, scripts, and policy.
- Historical `.work/changes/**` records remain immutable evidence except for this change record.
- The slice does not convert target-state plans into current implementation claims.

## Requirements

- **DOC-001 — Complete audit:** Inspect all tracked Markdown files and record coverage, material drift, active conflicts, and verification limits.
- **DOC-002 — Authority coherence:** Resolve contradictions in owned current-state authorities using the repository authority order.
- **DOC-003 — Capability states:** Distinguish public runtime capability, internal implementation, configured-but-authentication-required state, target state, and historical evidence.
- **DOC-004 — Style coherence:** Apply the repository develop-docs style contract: operative content first, atomic claims, stable terminology, minimal duplication, and explicit defaults and exceptions.
- **DOC-005 — Historical integrity:** Add a clear superseded or historical banner where an owned development document is being misread as current guidance; do not rewrite historical implementation evidence.
- **DOC-006 — Conflict preservation:** Do not edit or absorb active work owned by another workstream or uncommitted operator changes.
- **DOC-007 — Verification:** Run documentation link/structure checks available in the repository, change-workflow validation, full repository verification, diff review, and Git whitespace checks on the final branch.
- **DOC-008 — Delivery:** Commit, push, open a pull request, review the exact head, merge only when checks are current and the PR is cleanly mergeable, then clean this worktree and branch using the repository workflow.

## Acceptance

1. **Given** the tracked Markdown set, **when** the audit completes, **then** every file is either reviewed directly, classified as historical evidence, or covered by a deterministic structural scan.
2. **Given** the owned current-state documents, **when** a reader compares them, **then** product architecture, implemented capabilities, provider readiness, operational setup, and target evolution use consistent terminology and do not contradict each other.
3. **Given** public and internal Discover/provider/agent capabilities, **when** documentation describes status, **then** it identifies the correct exposure level without overstating implementation.
4. **Given** historical development records, **when** a record contains obsolete current-tense guidance, **then** it is labeled historical or superseded without rewriting the original evidence.
5. **Given** active external changes, **when** the branch is complete, **then** no excluded file is modified.
6. **Given** the final exact head, **when** repository and GitHub checks complete, **then** the PR is merged and the `039-documentation-reconciliation` worktree and local branch are removed without force.

## Risks and recovery

- **Risk:** Documentation can overstate internal code as a public tool. **Control:** use a public/internal/target matrix and verify registration paths.
- **Risk:** Another active branch owns related content. **Control:** exclude the owned file and record the residual reconciliation explicitly.
- **Risk:** Broad style edits create noise or historical distortion. **Control:** edit only material drift and repeated terminology; preserve historical records.
- **Risk:** A claim changes after the audit because another PR merges. **Control:** rebase or merge current `origin/main`, rerun the audit and verification, and review the final diff before merge.
- **Recovery:** Revert the merge commit or restore individual Markdown files from the pre-merge commit. No irreversible filesystem action is required.

## Out of scope

- Resolving the `stateless_http` executable/configuration contradiction.
- Editing, approving, revising, or rejecting entries in `docs/HARD-BLOCK-APPROVAL-REGISTER.md` while active change `040-context7-serena-adapters` owns that file.
- Editing `docs/DISCOVER-MODULE-PRODUCT-SPEC.md` while change `037-discover-final-integration` owns and modifies it.
- Updating `settings/kis-mcp.settings.json` while the active secrets workstream owns it.
- Adding an executable documentation-drift checker; that requires a separate `develop-code` slice.
