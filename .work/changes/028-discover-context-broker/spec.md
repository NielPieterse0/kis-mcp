# Change Specification: Discover Context Broker

- **Change ID**: `028-discover-context-broker`
- **Status**: Approved implementation slice
- **Risk Profile**: rigorous

## Outcome

Add a deterministic, task-scoped Context Broker that returns the smallest sufficient local code-evidence bundle under explicit file, character, symbol, and relationship budgets without traversing or flattening the repository outside existing Discover authority boundaries.

## Authority and scope

- `AGENTS.md`, `docs/TRUST-MODEL.md`, `SPEC.md`, and `docs/DISCOVER-MODULE-PRODUCT-SPEC.md` govern this change in that order.
- This slice owns only the new context contracts, ranking, broker, schemas, tests, and its governance directory declared in `scope.json`.
- It reuses `ReadAuthority`, `RepositoryScanner`, `PythonProjectIndexer`, and `GitReader`; it does not create competing identity, traversal, Git-process, or budget implementations.
- Public FastMCP registration and shared runtime composition remain deferred because active change `026-commissioning-refresh` owns shared integration files.

## Requirements

- **REQ-001 — Explicit request:** `GetCodeContextRequest` MUST require a project path, non-empty task, and explicit positive budget containing `max_chars`, `max_files`, `max_symbols`, and `max_relationships`.
- **REQ-002 — Configured maxima:** request budgets MUST be narrowed against configured Discover maxima. Requests above configured maxima or below the minimum valid contract MUST fail structurally before repository reads.
- **REQ-003 — Existing authority:** project identity, traversal, exclusions, safe file reads, Git execution, and Python parsing MUST use the existing hardened Discover components.
- **REQ-004 — Deterministic ranking:** task terms, file scores, symbol scores, relationship scores, tie-breaking, and substantive output ordering MUST be deterministic for identical repository state, task, configuration, and budgets.
- **REQ-005 — Smallest sufficient bundle:** the broker MUST rank repository-relative paths from metadata first, read only selected top-ranked files, return bounded excerpts rather than full-file dumps, and stop when the explicit budget is exhausted.
- **REQ-006 — Evidence types:** the response MUST include applicable files, modules, symbols, relationships, instructions, tests, contracts, local Git state, providers, provenance, unknowns, confidence, omissions, and truncation reasons using a stable schema-versioned contract.
- **REQ-007 — Relevance:** task terms MUST influence ranking across paths, Python modules, symbols, imports, calls, inheritance, tests, instructions, contracts, configuration, and local Git context. Conventional category boosts MUST remain explicit and deterministic.
- **REQ-008 — Relationships:** relationships MUST be included only when connected to retained files, modules, or symbols and MUST declare type, source, target, location, provenance, confidence, and relevance score.
- **REQ-009 — Output budget:** serialized output MUST not exceed `max_chars`. Compaction MUST preserve project/request identity, unknowns, truncation reasons, confidence, and omission counters. If the minimum valid response cannot fit, the operation MUST fail explicitly.
- **REQ-010 — Honest degradation:** unsupported languages, missing Git, parse failures, unreadable selected files, and budget omissions MUST produce bounded diagnostics or unknowns without invalidating independent evidence.
- **REQ-011 — No execution:** the broker MUST NOT import repository code, execute repository code, spawn processes directly, use the network, mutate files or Git state, run tests/builds/package managers, or accept executable paths, arguments, environment maps, credentials, URLs, or endpoints.
- **REQ-012 — Compatibility:** Work policy and the exact HR-001/HR-002/HR-003 decision set MUST remain unchanged.

## Acceptance

1. Given a repository and a task naming a file, module, symbol, test, contract, or instruction concept, when the broker runs, then directly relevant evidence ranks before unrelated evidence with stable ordering.
2. Given a Python repository, when relevant symbols and relationships exist, then the response includes bounded AST-confirmed symbols and connected import/call/inheritance relationships.
3. Given small budgets, when the result is compacted, then the response remains schema-valid, reports omitted counts and truncation reasons, and never exceeds `max_chars`.
4. Given identical repository state, request, settings, and budgets, when the broker runs repeatedly, then the substantive JSON and fingerprint are identical.
5. Given an unsupported or partially parsed repository, when the broker runs, then safe local file evidence remains available and unavailable semantic capability is reported explicitly.
6. Given selected files, when excerpts are read, then only safe repository-relative paths are read through `ReadAuthority`, excerpts are line-bounded, and full files are not returned unless the file itself fits the bounded excerpt.
7. Given the architecture test suite, when the slice is complete, then subprocess, traversal, network, and Work boundaries remain intact.
8. Given the full locked verification suite, when the slice is complete, then all checks pass and no shared integration file is modified.

## Risks and recovery

- Ranking may overfit filenames and miss semantically relevant evidence. Mitigation: combine path tokens, module/symbol metadata, deterministic category boosts, connected relationships, Git state, and explicit unknowns; add quality fixtures.
- Character compaction may invalidate references. Mitigation: build the response from retained objects only, recalculate omission counters, and validate the final serialized contract.
- Reading candidate content too early could become a repository dump. Mitigation: rank from metadata first and read only the bounded selected file set.
- Recovery is a normal branch revert; no generated index, persistent cache, repository mutation, or external provider state is introduced.

## Out of scope

- Public tool registration or server composition.
- Persistent semantic indexes, vector search, embeddings, or background indexing.
- Remote GitHub/GitLab evidence.
- Serena, LSP, SCIP, Ctags, Sourcegraph, or other external semantic providers.
- Execution of verification handoffs.
- Cross-repository context.
