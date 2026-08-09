# Discover Persistent Memory Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use test-driven implementation task-by-task; review the current diff after each architectural boundary and use fresh verification before completion.

**Goal:** Complete shared evidence persistence, durable Discover project intelligence, optional Serena semantics, and 040 retirement without regressing current gateway modularity.

**Architecture:** Add a provider-neutral `kis_mcp.evidence` kernel and a Discover `ProjectIntelligenceService` that resolves the central project registry, computes one normalized snapshot, and persists versioned generations beneath the configured KIS state root. Existing Discover workflows read through that service. Context7 and Serena are reconciled into current Provider runtime; Serena contributes only normalized semantic evidence to Discover and deterministic local analyzers remain authoritative fallbacks.

**Tech stack:** Python 3.13 runtime, stdlib AST/JSON/hashlib/pathlib/tempfile, FastMCP, existing Provider runtime, PowerShell installers/verification, pytest.

## Global constraints

- Work only in `.work/worktrees/084-discover-persistent-memory-closeout` and declared `scope.json` paths.
- Preserve exactly HR-001, HR-002, and HR-003; do not add memory policy.
- Generated Discover state stays beneath `C:\Projects\.kis-mcp` and outside inspected repositories.
- Registered `project_id` is the project identity; no second project catalogue.
- Repository/Git/docs/contracts remain authority; persisted intelligence is derived evidence and cannot override fresher source state.
- No generic memory CRUD, vector database, mandatory embeddings, or mandatory background indexer.
- 040 is a donor only; preserve newer mainline composition and selectively reconcile code/tests.
- Do not touch 083-owned startup lifecycle/test paths.

---

### Task 1: Shared evidence persistence kernel

**Requirements:** REQ-001, REQ-003, REQ-004

**Files:** create `src/kis_mcp/evidence/contracts.py`, `store.py`, `__init__.py`; modify `src/kis_mcp/work_management/evidence.py`; test `tests/evidence/test_store.py` and existing Work Management evidence tests.

**Interfaces:** produce `EvidenceArtifact`, `EvidenceManifest`, `EvidenceGeneration`, `EvidenceStore.write_generation(...)`, `EvidenceStore.read_generation(...)`, and a `ReviewEvidenceStore` compatibility adapter retaining current method signatures.

- [ ] Add failing tests for SHA-256 manifests, atomic publication, expected-hash conflicts, interrupted staging retention, corrupt artifact detection, byte bounds, and recoverable supersession.
- [ ] Confirm the new tests fail because the shared kernel does not exist.
- [ ] Implement the minimal shared store using same-directory staged writes plus atomic replacement; never permanently delete superseded/corrupt state.
- [ ] Refactor Work Management review persistence onto the shared primitive without changing `.work/reviews/<review-id>/` paths, dispositions, or public signatures.
- [ ] Run `pytest tests/evidence tests/work_management -q` and record pass evidence.
---

### Task 2: Project-memory settings, identity, and fingerprints

**Requirements:** REQ-002, REQ-004, REQ-011

**Files:** modify `src/kis_mcp/discover/settings.py`, `settings/kis-mcp.settings.json`; create `src/kis_mcp/discover/intelligence_contracts.py`, `intelligence_identity.py`; test `tests/discover/test_intelligence_identity.py` and settings tests.

**Interfaces:** produce `DiscoverMemorySettings`, `ProjectIntelligenceIdentity`, and `resolve_project_intelligence_identity(project, registry, git/source evidence, settings, semantic_provider)`. Identity contains stable project ID, canonical root, worktree/repository fingerprint, Git revision/dirty source fingerprint, Discover settings/schema/parser/provider fingerprints.

- [ ] Add failing strict-settings tests for enablement, state root, schema version, max stored bytes/files/modules/symbols/relationships, fingerprint behavior, provider inclusion, corruption handling, and supersession behavior.
- [ ] Add failing project/worktree/revision/dirty/settings/provider invalidation tests against the central project registry.
- [ ] Implement strict JSON-backed memory settings and deterministic fingerprint helpers; reject unregistered roots for persistent reuse.
- [ ] Verify one registered project can never resolve another project's generation and worktrees do not masquerade as canonical-root current state.
- [ ] Run focused identity/settings tests.

---

### Task 3: Normalized persistent project intelligence

**Requirements:** REQ-003, REQ-004, REQ-007

**Files:** create `src/kis_mcp/discover/intelligence.py`, `intelligence_store.py`, `semantic.py`; reuse current scanner/Python index/analyzer contracts; test `tests/discover/test_project_intelligence.py`.

**Interfaces:** produce `ProjectIntelligenceSnapshot`, normalized `AtlasModule`, `AtlasSymbol`, `AtlasRelationship`, and `ProjectIntelligenceService.get(project) -> ProjectIntelligenceSnapshot`. The service owns cold build, warm reuse, stale/corrupt refresh, bounded persistence, provenance, freshness, truncation, and generation metadata.

- [ ] Add failing cold-create/warm-reuse/cold-warm-equivalence tests plus bounded module/symbol/relationship truncation tests.
- [ ] Add failing stale/corrupt/hash-conflict/interrupted-publication/recoverable-supersession tests.
- [ ] Implement one normalized snapshot from current repository scan, Python AST, static JavaScript/TypeScript analyzer output, verification relationships, and optional normalized semantic evidence.
- [ ] Persist one versioned generation per resolved project/worktree identity under the configured central state root.
- [ ] Prove stale persisted evidence is never labeled current when source/config/provider fingerprints differ.
- [ ] Run the full project-intelligence focused suite.
---

### Task 4: Discover read-through integration

**Requirements:** REQ-005, REQ-006, REQ-012

**Files:** modify `src/kis_mcp/discover/service.py`, `context_broker.py`, `impact_graph.py`, `platform.py`, and related contracts; test existing/new `tests/discover/test_inspect_project.py`, context, impact, and analyze-change suites.

**Interfaces:** `InspectProjectService`, `ContextBrokerService`, and `ImpactGraphService` receive a shared `ProjectIntelligenceService` instance. Existing public tool arguments remain compatible; responses add bounded persistence/semantic status only where contracts permit.

- [ ] Add failing tests proving `inspect_project` refreshes/persists, Context Broker warm-reads the same generation, and impact/analyze reuse normalized symbols/relationships for affected tests.
- [ ] Add failing tests for provenance/freshness/fallback/truncation metadata and explicit stale/semantic degradation.
- [ ] Refactor services to consume shared intelligence while still reading current file excerpts and current Git evidence at request time where freshness matters.
- [ ] Preserve deterministic ranking and explicit caller budgets; no workflow may create a private duplicate index.
- [ ] Run Discover context, impact, inspect, change, and contract suites.

---

### Task 5: Reconcile 040 resolver and modular composition

**Requirements:** REQ-010, REQ-014

**Files:** compare donor `src/kis_mcp/command_intent.py`, `shell_parser.py`, donor tests, and historical Tools composition against current main; modify only still-missing current files/tests.

**Interfaces:** retain current thin `server.py` unchanged unless a proven façade-only adjustment is required. Provider mounting stays in `providers/platform.py` + `gateway/composition.py`.

- [ ] Diff each 040 resolver hunk against current main and write regression tests only for behavior still absent.
- [ ] Confirm any retained regression fails on the new branch before applying the minimal correction.
- [ ] Apply non-superseded resolver fixes without changing unknown-command or URL-as-data semantics.
- [ ] Explicitly reject transplanting 040's historical `server.py` and `tools/platform.py` composition when current equivalents supersede them.
- [ ] Run resolver and architecture/modularity tests.

---

### Task 6: Context7 provider closeout

**Requirements:** REQ-009, REQ-010, REQ-013

**Files:** create `src/kis_mcp/providers/context7/**`, `settings/providers/context7.provider.json`, `contracts/providers/context7/**`; reconcile `scripts/install-context7.ps1`, provider runtime settings, docs, and tests.

**Interfaces:** produce `register_context7_provider(registry)` with a fixed pinned descriptor for `@upstash/context7-mcp@3.2.5`, approved external connector boundary, exact two read operations, readiness probe, bounded MCP builder, and no project-memory coupling.

- [ ] Port only still-valid pinned contract/settings/install/readiness behavior from 040 and add provider-runtime registration/failure-isolation tests.
- [ ] Confirm arbitrary endpoints/provider passthrough remain absent and outputs/readiness redact credentials.
- [ ] Integrate Context7 into approved provider runtime settings under a fixed namespace without making it a deterministic Discover dependency.
- [ ] Run Context7 provider and runtime-isolation tests.
---

### Task 7: Serena provider and semantic normalization

**Requirements:** REQ-007, REQ-010, REQ-013

**Files:** create `src/kis_mcp/providers/serena/**`, `settings/providers/serena.provider.json`, `contracts/providers/serena/**`; reconcile `scripts/install-serena.ps1`; modify provider platform/runtime settings and Discover semantic adapter tests.

**Interfaces:** produce `register_serena_provider(registry)` for pinned `serena-agent==1.6.1` and `SerenaSemanticAdapter` implementing the provider-neutral Discover semantic port. Provider-specific MCP schemas stop at the adapter boundary.

- [ ] Port valid 040 settings/readiness/effect mapping/install contracts and add failing provider-runtime registration/isolation tests.
- [ ] Add failing normalization tests for symbols/references, unsupported language, partial capability, provider failure, and zero Serena-schema leakage into persisted contracts.
- [ ] Implement the Provider-runtime descriptor/builder and normalized read adapter; Provider runtime owns lifecycle and provider-managed state roots.
- [ ] Wire optional Serena semantic evidence into `ProjectIntelligenceService`; fallback to deterministic local analyzers with explicit degradation.
- [ ] Run Serena provider/normalization/fallback suites.

---

### Task 8: HR3-07 complete-artifact quarantine and restoration

**Requirements:** REQ-008, REQ-013

**Files:** reconcile Serena memory/effects modules, `docs/HARD-BLOCK-APPROVAL-REGISTER.md`, quarantine-focused tests, and live commissioning helper/evidence.

**Interfaces:** produce exact `resolve_serena_memory_artifacts(memory_name, settings)` and quarantine interception that calls existing `QuarantineService.quarantine_many(...)` for the complete proven set and never forwards successful quarantine as provider `delete_memory`.

- [ ] Inspect pinned installed Serena `1.6.1` implementation and contract to establish the complete affected file/metadata/catalogue/index set.
- [ ] Add failing tests for complete set, wildcard/traversal/alias/outside-root rejection, partial quarantine rollback, no provider-delete forwarding, restore, stale/regenerated metadata, and reinspection consistency.
- [ ] Implement only the evidence-proven artifact resolver/quarantine interception; preserve provider behavior when the safety condition cannot be proven by leaving that operation inactive/degraded.
- [ ] Execute bounded restoration/restart/reinspect proof against the pinned local installation and preserve evidence beneath the KIS state root.
- [ ] Run HR1-07/HR2-06/HR3-07 focused tests.

---

### Task 9: Live commissioning and documentation reconciliation

**Requirements:** REQ-009, REQ-013, REQ-014

**Files:** create/reconcile bounded smoke helper; update `SPEC.md`, `docs/PLATFORM-CONCEPT.md`, `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`, `docs/OPERATIONS.md`, `docs/development/tools/context7-serena.md`, 040 artifacts, and this change closeout.

**Interfaces:** live evidence must record pinned identity, startup, tools discovered, required read operations, normalized semantic result, failure isolation, managed-state containment, Context7 smoke, and any unavailable prerequisite without exposing secrets.

- [ ] Run local provider readiness and bounded live MCP contract discovery for Context7 and Serena using pinned installed artifacts only.
- [ ] Capture Serena semantic read evidence and Context7 read smoke while keeping Context7 outside project-memory composition.
- [ ] Update authority documents only after verified behavior exists; mark Discover D3 persistence/Serena portions implemented and shared EvidenceStore complete when proven.
- [ ] Mark 040 as `absorbed and superseded by 084` in its historical artifacts while preserving acquisition/install/recovery evidence.
- [ ] Run documentation/schema/search checks for stale staged/held claims.

---

### Task 10: Review, verify, integrate, and retire 040

**Requirements:** REQ-013, REQ-014

**Files:** all claimed paths; update `tasks.md` and `closeout.md` with exact evidence.

- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check` from the 084 worktree.
- [ ] Run focused suites, architecture/modularity tests, then full `pwsh -NoProfile -File scripts/verify.ps1` serially.
- [ ] Inspect the full diff against the approved spec and run exact working-tree review; fix blocking findings and rerun affected verification.
- [ ] Commit the exact verified head and attempt the repository's normal approved PR/merge workflow without bypassing HR-002 or other provider boundaries.
- [ ] After successful integration, verify current `main`, mark this change closed, then run governed cleanup for 084 and the absorbed 040 worktree/branches without force or permanent deletion.
- [ ] If external PR/merge authority is unavailable in this runtime, stop short of claiming completion and record the exact remaining integration/cleanup dependency.