# Change Specification: Operations Document Routing

- **Change ID**: `167-operations-document-routing`
- **Status**: Approved
- **Documentation level**: Complex — restructures a canonical operator authority across multiple files.
- **Governance complexity**: `medium`
- **Risk trigger**: `architecture_boundary`

## Outcome

Reduce default operator-document context by turning `docs/OPERATIONS.md` into a concise canonical index with scoped runbooks while preserving all operator guidance, tested invariants, and authority.

## Authority and scope

- Repository workflow/routing: `AGENTS.md`.
- Operator procedure source: current `docs/OPERATIONS.md` at base `03c677d0f59d6da504a12912dce073db42116db5`.
- Executable facts remain owned by current settings, scripts, contracts, source, and tests.
- Owned paths: `AGENTS.md`, `docs/OPERATIONS.md`, `docs/operations/**`, and this change record.
- No source, tests, policy, settings, `SPEC.md`, trust semantics, or module specs may change.
- Related programme: documentation/context burden investigation #283; this slice does not close that broader investigation.

## Requirements

- **REQ-001**: `docs/OPERATIONS.md` remains the canonical operator entry point and states that linked `docs/operations/**` runbooks are subordinate parts of the same operator-documentation domain.
- **REQ-002**: Split detailed procedures by operator task so a reader can load one relevant runbook instead of the full legacy document.
- **REQ-003**: Preserve every substantive operator procedure and recovery instruction from the base Operations document. Do not preserve duplicated current architecture, public-contract detail, machine-owned values, volatile inventories, historical status, or commissioning results when a higher or executable owner already exists; route those claims to that owner instead.
- **REQ-004**: Keep root fast paths and compatibility text required by existing repository tests, including change-workflow commands and dual-instance startup invariants.
- **REQ-005**: Update `AGENTS.md` routing/ownership references to recognize the scoped runbook subtree without changing authority precedence or the three hard rules.
- **REQ-006**: All repository-relative links in the new runbooks resolve to tracked targets.
- **REQ-007**: Root `docs/OPERATIONS.md` should be materially smaller than the 84,138-byte baseline and optimized for task routing rather than exhaustive reading.

## Acceptance

1. Existing focused repository/document tests pass unchanged.
2. `scripts/change-workflow.ps1 check` reports only declared paths.
3. A link check reports no broken relative Markdown links in `docs/OPERATIONS.md` or `docs/operations/*.md`.
4. A procedure-preservation audit accounts for all legacy H2/H3 operator headings, script references, executable command lines, and troubleshooting error identifiers. Any omission must be explicitly classified as non-operator implementation detail or replaced by a safer/current equivalent and reviewed as such.
5. Documentation and architecture reviews report no blocking authority, omission, or routing findings.

## Risks and recovery

- Risk: moving prose can silently drop operational detail or break relative links.
- Mitigation: split from the exact base text by section, preserve section bodies verbatim where practical, and run a section/link audit.
- Recovery: the change is documentation-only and can be reverted as one commit/PR; original content remains in Git history.

## Out of scope

- Product behavior, policy semantics, settings, scripts, source, tests, commissioning, module specs, `SPEC.md`, and target architecture.