# Documentation Reconciliation Tasks

## Lifecycle state

- [x] Understand: authority, source material, active claims, operator audit, and repository workflow inspected.
- [x] Classify: Complex documentation slice because it spans authoritative current-state, architecture, operations, provider, lessons, and historical-status documents.
- [x] Plan: scope, specification, source boundaries, acceptance, recovery, and task plan recorded.
- [x] Implement: complete the audit and owned document edits.
- [ ] Review: reconcile the final document set with sources, style, scope, and active work.
- [ ] Verify: run structural, workflow, repository, and Git checks on the final state.
- [ ] Close: merge the PR and clean the change worktree and local branch.

## Source-to-document map

| Working ID | Source evidence | Target documents | Reader outcome | Verification |
|---|---|---|---|---|
| DOC-001 | Tracked Markdown inventory, link scan, active change claims | This task record and closeout | Complete audit coverage is explicit | Inventory count and scan output |
| DOC-002 | Authority order and current implementation | `README.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md` | Current product and target evolution agree | Cross-document review and repository verification |
| DOC-003 | Public registration and internal implementation | `README.md`, `SPEC.md`, provider and operations docs | Capability exposure and readiness are not overstated | Registration/source inspection and stale-phrase search |
| DOC-004 | Repository develop-docs style guide | All owned reader-facing docs | Documents use direct, atomic, consistent language | Manual style review and Markdown structural scan |
| DOC-005 | Historical change evidence and current provider composition | `docs/development/provider-composition/README.md` | Historical guidance cannot be mistaken for current guidance | Banner/link review |
| DOC-006 | Dirty primary file and active worktree claims | Excluded paths | Parallel work remains intact | Final changed-path audit |
| DOC-007 | Repository workflow and verification scripts | This task record and closeout | Completion claims have current evidence | Exact command output |
| DOC-008 | Git and GitHub delivery state | Change artifacts | PR is merged and worktree cleaned | Exact head, merge commit, and worktree list |

## Audit findings

Baseline: `origin/main` at `931d3bf302c2d875f1c4ede774ebb15a2888b28c`.

- Structural inventory: 227 Markdown files.
- Classification: 13 authority/current-guidance files, 47 local skill documents, 144 historical change records, and 23 development-evidence documents.
- Repository-relative Markdown link targets: 0 missing.
- Initial heading defects: 2. The Skills development-evidence hierarchy was corrected; the remaining defect is in the dirty operator-owned hard-block approval register and is excluded.
- `README.md`: removed inspect-project-only architecture, fixed tool-count history, and documented current public, internal, standalone, and target capability states.
- `SPEC.md`: reconciled current Discover, Skills, Provider, Tools, agent, Control Center, tunnel-configuration, and internal-service claims; recorded the unresolved `stateless_http` executable/configuration contradiction instead of masking it.
- `docs/PLATFORM-CONCEPT.md`: updated the current-baseline relationship and delivery sequence without converting target Govern/workflow capabilities into current claims.
- `docs/PROVIDER-MODULE-PRODUCT-SPEC.md`: replaced obsolete P1-P3 future-state language with the implemented four-provider registry, GitHub/Supabase runtime composition, NVIDIA workflow boundary, commissioning model, and Codex Tools-module exclusion.
- `docs/OPERATIONS.md`: corrected tunnel configuration guidance, public/internal Discover distinctions, and standalone Control Center operations.
- `docs/LESSONS-APPLICABILITY.md`: reclassified deterministic contracts, registries, readiness states, Discover, Provider composition, context/impact internals, and agent capability.
- `docs/development/provider-composition/README.md`: added a historical/superseded banner without rewriting the original slice evidence.
- Excluded active or dirty work: `docs/HARD-BLOCK-APPROVAL-REGISTER.md`, `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`, and `settings/kis-mcp.settings.json`.
- Unsupported checks: external URL availability, resolved Markdown anchors, and inline HTML links.

## Implementation checklist

- [x] Task 1: establish audit baseline and source map.
- [x] Task 2: reconcile primary product and architecture authorities.
- [x] Task 3: reconcile provider, operations, and lessons guidance.
- [x] Task 4: add historical-status protection to provider composition evidence and correct Skills evidence heading hierarchy.
- [ ] Task 5: review and verify the complete documentation set.
- [ ] Task 6: deliver through PR and clean the worktree.
