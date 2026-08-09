# Change Specification: Discover Persistent Memory Closeout

- **Change ID:** `084-discover-persistent-memory-closeout`
- **Status:** Approved for implementation by the operator-supplied slice
- **Risk profile:** Complex / rigorous — persistent generated state, provider commissioning, shared architecture, and recovery behavior

## Outcome

Complete the approved project-memory architecture by adding one shared evidence persistence kernel, durable project-scoped Discover intelligence, on-demand freshness, Context Broker/impact reuse, optional Serena semantic evidence, and full absorption/retirement of held change `040-context7-serena-adapters`.

## Authority and scope

Authority is `AGENTS.md` -> `docs/TRUST-MODEL.md` -> `SPEC.md` -> `docs/PLATFORM-CONCEPT.md` -> `policy/kis-mcp.policy.json` -> `docs/OPERATIONS.md`, plus the operator-supplied closeout scope for this change.

The current clean local `main` at change creation is the implementation base. Held branch `change/040-context7-serena-adapters` is a donor only; its historical composition must not overwrite newer mainline architecture.

Exactly HR-001, HR-002, and HR-003 remain the Work policy. No memory/index rule is added.

## Requirements

- **REQ-001 Shared evidence kernel:** Provide reusable bounded, SHA-256 verified, atomic, conflict-detecting, corruption-aware, versioned evidence persistence with recoverable supersession. Preserve existing `.work/reviews/<review-id>/` behavior through a Work Management adapter.
- **REQ-002 Project identity/isolation:** Persist Discover state only for a registered central `ProjectDefinition`; bind state to stable `project_id`, canonical root, repository/worktree identity, revision/source fingerprint, and configuration/provider fingerprints. Never reuse one project/worktree state as another.
- **REQ-003 Persistent intelligence:** Persist bounded Code Atlas, Symbol Atlas, and Relationship Graph generations beneath `C:\Projects\.kis-mcp`, outside inspected repositories, with provenance, confidence, freshness, classification, truncation, hashes, and generation metadata.
- **REQ-004 Read-through freshness:** Reuse current generations; detect missing/stale/incompatible/corrupt state; recompute only the bounded intelligence generation required by the shared snapshot; atomically publish; retain/recover superseded or failed generations. Cold and warm results must be substantively equivalent.
- **REQ-005 Shared Discover consumption:** `inspect_project`, `get_code_context`, `inspect_change` impact derivation, and `analyze_change` must consume the same project-intelligence service rather than creating workflow-specific indexes.
- **REQ-006 Context Broker:** Keep `get_code_context` as the principal bounded retrieval interface; compose current repository/Git/docs/contracts/verification evidence with persisted atlases and semantic evidence, preserve deterministic ranking/budgets/provenance/freshness/unknowns, and never return a repository dump.
- **REQ-007 Serena provider:** Reconcile valid 040 Serena code into the current Provider runtime. Normalize semantic symbols/references before Discover consumes them. Serena absence, disablement, failure, incompatibility, or partial language capability must degrade explicitly to deterministic local parsers.
- **REQ-008 Serena memory safety:** Prove the complete `delete_memory` artifact set for pinned Serena `1.6.1`, quarantine that complete set without forwarding provider deletion, restore it, restart/reinspect Serena, and deterministically handle regenerated/stale catalogue/index metadata. Serena-managed memory is not KIS project memory.
- **REQ-009 Context7 closeout:** Reconcile pinned Context7 `3.2.5` as an independent approved external documentation provider, validate its contract/readiness/live bounded smoke, preserve failure isolation, and do not integrate Context7 into project-memory persistence.
- **REQ-010 Resolver and composition reconciliation:** Compare 040 command/shell resolver changes with current main; retain only non-superseded corrections and tests. Preserve the thin `server.py`/current gateway composition; integrate providers through current provider composition seams.
- **REQ-011 JSON configuration:** Configure persistence enablement, state root, schema version, byte/file/module/symbol/relationship limits, fingerprint/freshness behavior, provider inclusion, corruption handling, and supersession/recovery through strict JSON-backed Discover settings. Persist no credentials or repository secrets.
- **REQ-012 Public surface/status:** Do not add generic memory CRUD. Existing Discover operations expose useful generation/fingerprint/freshness/provider/fallback/degradation metadata without expanding the memory surface.
- **REQ-013 Verification:** Add focused persistence, isolation, invalidation, corruption, boundedness, Discover reuse/impact, Serena normalization/fallback/safety, Context7 isolation, resolver, and modularity tests; run change governance, architecture tests, full `scripts/verify.ps1`, exact-head review, and live commissioning evidence.
- **REQ-014 Documentation/040 retirement:** Reconcile `SPEC.md`, platform/Discover specs, operations/development docs, 040 artifacts, and this change. After successful integration, record 040 as absorbed/superseded and remove its held worktree/branch only through governed safe cleanup.

## Acceptance

1. Cold `inspect_project` creates a valid project-scoped generation; an unchanged warm call reuses it and produces equivalent substantive atlas/graph evidence.
2. Revision, dirty-source, settings/schema, provider-version, project, or worktree identity changes make prior state stale rather than current.
3. Corrupt/hash-conflicting/interrupted generations degrade safely and are recoverable without permanent deletion.
4. Work Management review artifact paths and conflict semantics remain compatible while using the shared persistence primitive.
5. Context Broker and impact analysis demonstrate reuse of the same project-intelligence generation and retain explicit budgets/truncation/provenance/freshness.
6. Serena semantic evidence is normalized, optional, failure-isolated, and never the sole source of repository understanding.
7. Serena `delete_memory` safety evidence proves quarantine, restoration, and post-restoration metadata/catalogue/index consistency with no provider permanent-delete call after quarantine.
8. Context7 and Serena live bounded contract/smoke checks succeed independently, or any unavailable external prerequisite is recorded as an explicit commissioning blocker without weakening deterministic Discover.
9. Current gateway/server modularity is preserved and the complete resolver regression suite passes.
10. All configured generated Discover state resolves beneath `C:\Projects\.kis-mcp` and outside inspected repositories; no secrets are persisted.
11. Required authoritative documentation agrees with verified implementation status.
12. Focused suites, architecture/modularity checks, `change-workflow check`, full `scripts/verify.ps1`, and exact-head review pass before integration is claimed complete.
13. 040 is recorded as absorbed/superseded and has no remaining hold only after the new change is integrated and governed cleanup succeeds.

## Risks and recovery

- **Persistent-state incompatibility:** schema/provider/config fingerprints invalidate generations. Recovery uses a new atomic generation and recoverable supersession; old state is retained/quarantined according to configured handling.
- **Cross-project/worktree contamination:** registry identity and repository/worktree fingerprint are mandatory manifest inputs. Any mismatch forces refresh and is reported stale.
- **Provider instability:** Serena/Context7 lifecycle remains Provider-runtime owned and failure-isolated. Discover always preserves deterministic parser/static fallbacks.
- **Historical 040 regression:** 040 is compared component-by-component. Stale `server.py`, Tools composition, and already-superseded resolver behavior are not transplanted.
- **Verification mutation:** generated state remains beneath `C:\Projects\.kis-mcp`; repository status is inspected after tests. No permanent cleanup is used.
- **Rollback:** the feature can be disabled in strict JSON settings; current repository evidence remains authoritative and existing deterministic Discover behavior remains the fallback.

## Out of scope

Conversational/user memory, autonomous free-form facts, generic remember/recall/forget tools, vector databases, mandatory embeddings, mandatory background indexing, Sourcegraph/SCIP deployment without a proven gap, implicit scans of every `C:\Projects` repository, general remote-forge indexing, Govern implementation, unrelated Work orchestration, and unrelated provider expansion.