# Change Specification: Documentation Authority Refresh

- **Change ID**: `094-documentation-authority-refresh`
- **Status**: Approved
- **Risk Profile**: rigorous

## Outcome

Refresh current authoritative documentation around one governed fact / one canonical owner, remove current authority duplication and contradictions, and prevent KIS text-write line-ending drift by honoring each Git worktree's effective attributes without rewriting historical records or changing policy.

## Authority and scope

- Authoritative sources: `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `policy/kis-mcp.policy.json`, `docs/OPERATIONS.md`, plus the operator-supplied documentation audit for this slice.
- Owned paths: `AGENTS.md`, `README.md`, `docs/TRUST-MODEL.md`, `docs/PLATFORM-CONCEPT.md`, `docs/OPERATIONS.md`, `src/kis_mcp/line_endings.py`, `src/kis_mcp/middleware.py`, `src/kis_mcp/gateway/composition.py`, `tests/test_line_endings.py`, and this change record.
- Shared paths: none.
- Excluded paths: `SPEC.md`, `docs/development/**`, `docs/STARTUP-HARDENING.md`, `docs/LESSONS-APPLICABILITY.md`.
- Dependencies: none.
- Integration owner: none.
- Parallel-work constraint: active change `093-change-intelligence-enrichment` exclusively owns `SPEC.md` and `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`; this slice must not modify either path.

## Requirements

- **REQ-001**: `AGENTS.md` must define the repository-wide documentation ownership rule: one governed fact has one canonical owner; other documents summarize, specialize within a narrower declared scope, link, or preserve historical evidence.
- **REQ-002**: `AGENTS.md` must route current product state, target state, trust semantics, operator procedures, module contracts, active change records, historical/supporting evidence, reusable skills, and machine-readable facts to their proper owners.
- **REQ-003**: `README.md` must remain a human orientation/index and must defer detailed architecture, policy, configuration, provider lifecycle, work-management behavior, and operations to canonical owners.
- **REQ-004**: `docs/PLATFORM-CONCEPT.md` must not independently redefine repository document ownership; target Govern concepts must consume the repository authority declarations owned by `AGENTS.md`.
- **REQ-005**: `docs/OPERATIONS.md` must be the single canonical operator runbook and must correct the stale statement that the Control Center is not mounted in the primary gateway.
- **REQ-006**: `docs/TRUST-MODEL.md` must explicitly bound itself to trust assumptions and HR-001/002/003 semantics and defer repository workflow, product architecture, and operations to their owners.
- **REQ-007**: Historical `.work/changes/**` and `docs/development/**` records must not be rewritten as part of the refresh.
- **REQ-008**: No target-state claim may be represented as current implementation, and no policy behavior may change.
- **REQ-009**: KIS text mutations through `write_file` and `edit_block` must normalize newline-bearing text to the target Git worktree's effective `eol` attribute before provider forwarding, while leaving binary-designated, non-Git, out-of-boundary, and attribute-unspecified paths unchanged.
- **REQ-010**: The line-ending guard must use Git's effective `text`/`eol` attribute resolution rather than duplicating `.gitattributes` pattern semantics, must preserve explicit CRLF exceptions, and must not create a new policy rule or direct filesystem writer.

## Acceptance

1. **Given** the current authority chain, **When** a reader needs a repository fact, **Then** `AGENTS.md` provides one unambiguous canonical owner and instructs non-owners to reference rather than repeat it.
2. **Given** the human landing page, **When** a reader needs implementation or operational detail, **Then** `README.md` routes to the owning authority instead of restating volatile detail.
3. **Given** target-state governance documentation, **When** document ownership is discussed, **Then** `PLATFORM-CONCEPT.md` references `AGENTS.md` rather than maintaining a competing file-by-file authority table.
4. **Given** current Control Center implementation, **When** an operator reads `docs/OPERATIONS.md`, **Then** the mounted and standalone forms are described consistently with current product documentation.
5. **Given** historical change/supporting evidence, **When** the refresh is complete, **Then** no excluded historical/supporting document is modified.
6. **Given** the final branch, **When** change-scope and canonical repository verification run, **Then** both pass on the reviewed head.
7. **Given** a KIS `write_file` or `edit_block` call containing CRLF/LF text, **When** Git resolves `eol=lf` or `eol=crlf` for the target, **Then** the provider receives canonical text for that attribute; binary-designated paths are not rewritten.

## Risks and recovery

- Risk: over-consolidation could remove useful orientation or accidentally move product truth into the wrong document.
- Mitigation: preserve concise summaries and use links; review each edit against the authority chain and current implementation evidence.
- Risk: parallel work may change `SPEC.md` while this slice is active.
- Mitigation: keep `SPEC.md` excluded and do not modify the active `093` worktree or scope.
- Risk: newline normalization could overreach binary or explicitly CRLF paths.
- Mitigation: query Git's effective `text` and `eol` attributes and skip `text=unset` or unspecified EOL paths; focused tests cover LF, CRLF, binary, and middleware forwarding.
- Recovery: all changes are Git-recoverable; revert the bounded compatibility layer through a normal corrective change rather than weakening `.gitattributes` or `core.safecrlf`.

## Out of scope

- Editing historical `.work/changes/**` records other than this change record.
- Editing `docs/development/**`, `docs/STARTUP-HARDENING.md`, or `docs/LESSONS-APPLICABILITY.md`.
- Modifying `SPEC.md` or the Discover module product spec while change `093` owns those paths.
- Changing source/runtime behavior beyond the bounded Git-attribute line-ending compatibility guard; changing settings, policy JSON, contracts, or commissioning state.
