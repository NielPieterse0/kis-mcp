# Documentation Reconciliation Tasks

## Lifecycle state

- [x] Understand: authority, source material, active claims, operator audit, and repository workflow inspected.
- [x] Classify: Complex documentation slice because it spans authoritative current-state, architecture, operations, provider, lessons, and historical-status documents.
- [x] Plan: scope, specification, source boundaries, acceptance, recovery, and task plan recorded.
- [x] Implement: complete the repository-wide audit and owned document edits.
- [x] Review: reconcile the document set with implementation, merged concurrent work, writing style, scope, and active claims.
- [x] Verify: structural audit, workflow validation, scope check, Git whitespace check, and full repository verification passed on the delivery state.
- [ ] Close: push, review and merge the PR, then clean the `039` worktree and local branch.

## Source-to-document map

| Working ID | Source evidence | Target documents | Reader outcome | Verification |
|---|---|---|---|---|
| DOC-001 | Tracked Markdown inventory, link scan, active change claims | This task record and closeout | Complete audit coverage is explicit | Inventory count and audit output |
| DOC-002 | Authority order and current implementation | `README.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md` | Current product and target evolution agree | Cross-document review and repository verification |
| DOC-003 | Public registration, internal implementation, managed bootstrap, and commissioning state | Product, provider, lessons, and operations documents | Capability exposure and readiness are not overstated | Source inspection and stale-phrase search |
| DOC-004 | Repository develop-docs style guide | Current authority documents and owned evidence | Documents use direct language and stable heading hierarchy | Authority-style audit |
| DOC-005 | Historical change evidence and current provider composition | Provider-composition and Skills development evidence | Historical guidance cannot be mistaken for current guidance | Banner and heading review |
| DOC-006 | Active Discover, Secrets, and Context7/Serena claims | Excluded paths | Parallel work remains intact | Final changed-path audit |
| DOC-007 | Repository workflow and verification scripts | This task record and closeout | Completion claims have current evidence | Exact command output |
| DOC-008 | Git and GitHub delivery state | Change artifacts | PR is merged and worktree cleaned | Exact head, merge commit, and worktree list |

## Audit baseline and coverage

- Initial base: `931d3bf302c2d875f1c4ede774ebb15a2888b28c`.
- Concurrent main integrated: `f13e1f57082d7df7482efb3b3b07c711a9da27e7`, including AgentSys/agnix bootstrap and its cleanup closeout.
- Final structural inventory: 233 Markdown files.
- Classification: 13 authority/current-guidance files, 47 local skill documents, 148 historical change-record documents, and 25 development-evidence documents.
- Repository-relative Markdown links: 0 missing targets.
- Single-H1 audit: one defect remains in `docs/HARD-BLOCK-APPROVAL-REGISTER.md`, which is owned by active change `040-context7-serena-adapters` and excluded from this slice.
- Current-authority style audit: 0 heading-level jumps and 0 missing blank lines after headings outside the excluded register defect.
- Audit limits: external URL availability, resolved Markdown anchors, and inline HTML links were not checked.

## Material reconciliations

- `README.md`: replaced inspect-project-only and fixed-tool-count history with current public, internal, standalone, managed-tooling, and target states.
- `SPEC.md`: reconciled Discover, Skills, Provider, Tools, agent, Control Center, AgentSys/agnix bootstrap, tunnel configuration, and internal-service claims; retained the unresolved `stateless_http` executable/configuration contradiction as a separate defect.
- `docs/PLATFORM-CONCEPT.md`: aligned the current-baseline relationship and delivery sequence without presenting Govern or future workflow composition as implemented.
- `docs/PROVIDER-MODULE-PRODUCT-SPEC.md`: replaced obsolete P1-P3 future language with the implemented four-provider registry, GitHub/Supabase runtime composition, NVIDIA workflow boundary, commissioning model, and Codex Tools-module exclusion.
- `docs/OPERATIONS.md`: corrected generated-state layout, tunnel configuration guidance, public/internal Discover distinctions, standalone Control Center operations, and supervised AgentSys/agnix installation and recovery.
- `docs/LESSONS-APPLICABILITY.md`: reclassified deterministic contracts, registries, readiness states, Discover, Provider composition, context/impact internals, managed bootstrap, and agent capability.
- `docs/development/provider-composition/README.md`: added a historical/superseded banner without rewriting original slice evidence.
- `docs/development/skills-module/README.md`: normalized heading hierarchy without changing recorded smoke or modularity evidence.

## Residual exclusions and decisions

- `docs/DISCOVER-MODULE-PRODUCT-SPEC.md` remains owned by active change `037-discover-final-integration` and was not edited.
- `settings/kis-mcp.settings.json` remains owned by active change `031-application-secrets` and was not edited.
- `docs/HARD-BLOCK-APPROVAL-REGISTER.md` remains owned by active change `040-context7-serena-adapters`; its four-H1 hierarchy and empty operator decisions are delegated to that workstream.
- The `stateless_http` settings/runtime contradiction requires a separate executable/configuration slice with tests.
- An executable semantic documentation-drift gate remains a separate code slice.

## Implementation checklist

- [x] Task 1: establish audit baseline and source map.
- [x] Task 2: reconcile primary product and architecture authorities.
- [x] Task 3: reconcile provider, operations, bootstrap, and lessons guidance.
- [x] Task 4: protect historical evidence and normalize owned document structure.
- [x] Task 5: run final review and verification on the delivery state.
- [ ] Task 6: deliver through PR and clean the worktree.
