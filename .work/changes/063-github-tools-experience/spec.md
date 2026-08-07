# Change Specification: GitHub Tools Experience

- **Change ID**: `063-github-tools-experience`
- **Status**: Approved
- **Risk Profile**: rigorous

## Outcome

Improve the GitHub and GitHub Projects tool experience without expanding the direct tool surface or weakening provider, repository, Project, approval, or three-rule boundaries.

## Authority and scope

- Authority: `AGENTS.md`, `docs/TRUST-MODEL.md`, `docs/OPERATIONS.md`, `SPEC.md`, changes 045/047/057/061, the operator-approved improvement programme, and the attached user audits.
- Owned implementation is limited to the exact paths in `scope.json`.
- Active change 058 owns GitHub Project commissioning settings and remains untouched.
- Active change 062 owns Discover Git evidence and explicitly excludes capability implementation.
- No policy file or provider/work-management settings change is permitted.

## Requirements

- **REQ-001 — Runtime schema preservation:** Runtime-discovered provider tools must retain their authoritative MCP input schema, and normalized operation descriptions must expose a bounded copy after explicit discovery.
- **REQ-002 — Exact bounded description:** `describe_capability` must prefer an exact contribution, operation, or workflow match and must not expand an entire provider catalogue when one exact operation was requested.
- **REQ-003 — Ranked compact search:** `search_capabilities` must rank exact ID/name/capability matches ahead of prefix, domain, description, and generic capability matches while returning compact bounded records.
- **REQ-004 — GitHub semantic capabilities:** The GitHub provider may declare a small reviewed semantic map for workflow-critical operations such as pull-request review, pull-request merge/create, Actions reads, and GitHub Projects. It must not hard-code or duplicate the complete upstream GitHub catalogue.
- **REQ-005 — Recommendation contract:** `recommend_workflow` must return only workflows whose required capabilities are currently available. Ineligible candidates may remain visible through catalogue/description evidence but are not recommendations.
- **REQ-006 — Result budgeting:** Generic long-tail dispatch must prevent unbounded provider responses from defeating progressive exposure. Compaction/truncation must be deterministic, explicit, preserve useful top-level evidence, and never authorize or mutate an operation.
- **REQ-007 — Projects boundary:** Existing repository-bound GitHub Projects routing, bounded pagination, idempotency, revision preflight, and supported create/update behavior remain intact. No unrestricted Project GraphQL or delete surface is introduced.
- **REQ-008 — Runtime/auth invariants:** The one-client-per-runtime GitHub OAuth lifecycle from 057/061, PAT exclusion, current readiness, repository routing, direct exposure bounds, and upstream runtime discovery remain unchanged.
- **REQ-009 — Modularity:** GitHub-specific semantic knowledge stays in the GitHub provider domain; generic capability contracts remain provider-neutral.

## Acceptance

1. A runtime tool snapshot carrying an MCP `inputSchema` retains that schema through provider projection and capability augmentation.
2. Exact description of a GitHub long-tail operation returns one compact operation record with invocation schema rather than the provider's complete operation set.
3. Exact operation/name searches outrank generic `repository.git` matches and bounded searches do not become dominated by unrelated GitHub tools.
4. When runtime GitHub merge/review operations are present, their normalized semantic capabilities satisfy the GitHub-specific prerequisites of the safe PR-closeout workflow.
5. Workflows with any missing required capability are absent from `recommend_workflow` results.
6. Oversized GitHub list/search results dispatched through the long-tail control surface are deterministically bounded with explicit truncation evidence; small results preserve their existing behavior.
7. GitHub Projects inventory/reconciliation tests remain green and capability discovery identifies Project read/write operations accurately.
8. Focused tests, architecture checks, governed scope check, `git diff --check`, canonical verification, and exact-head Windows CI pass for every landed PR batch.

## Risks and recovery

- Risk: schema metadata could substantially increase catalogue payload size. Mitigation: store only normalized JSON-compatible schemas and expose them on exact description, not every compact search record.
- Risk: semantic aliases could become a shadow GitHub catalogue. Mitigation: limit mappings to reviewed workflow/domain semantics; long-tail existence still comes only from the runtime snapshot.
- Risk: generic result compaction could hide required evidence. Mitigation: apply only above a hard budget, preserve explicit truncation metadata, and test both compacted and untouched results.
- Risk: repeated PRs from one worktree could drift from `main`. Mitigation: fetch/reconcile after every merge before starting the next batch, preserve exact-head evidence, and keep the governed claim active until the final batch.
- Recovery: revert the relevant PR batch. No permanent deletion, policy migration, credential migration, or provider reauthentication design change is part of this programme.

## Out of scope

- Full hard-coded GitHub MCP tool catalogue.
- New GitHub OAuth scopes, PAT support, credential storage, or cross-runtime token persistence.
- Changes to active GitHub Project commissioning settings owned by change 058.
- Changes to Discover owned by change 062.
- New policy rules, force operations, permanent deletion, unrestricted GitHub Projects mutation, or direct exposure of the full GitHub long tail.
