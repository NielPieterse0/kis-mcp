# Change Specification: Discover Foundation and inspect_project

- **Change ID**: `005-discover-foundation`
- **Status**: Approved for implementation
- **Development level**: Complex
- **Risk profile**: New architectural plane, public contract, repository read boundary, and server-composition change; read-only and reversible
- **Base commit**: `946c27b6040bc0f7e03263f2971bf7ab325da473`

## Outcome

Adopt the complete Discover target product specification and implement the first bounded D0/D1 capability:

```text
inspect_project
```

The implementation adapts the mature sdk-tool analysis and project-intelligence architecture, adds dev-intel repository-inspection parity and selected mcp-tool hardening, and remains independent of all donor repositories at runtime.

## Authority and sources

Authority applies in this order:

1. `AGENTS.md`;
2. `docs/TRUST-MODEL.md`;
3. `SPEC.md` for current implementation claims;
4. `docs/PLATFORM-CONCEPT.md`;
5. `docs/DISCOVER-MODULE-PRODUCT-SPEC.md` for complete Discover target behavior;
6. this bounded change specification;
7. donor implementation evidence recorded in `docs/development/discover-foundation/source-harvest.md`.

The operator-supplied Discover module product specification and SDK Platform concept are approved source specifications. They are adapted to the `kis-mcp` identity and three-rule Work boundary in `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`.

## Scope and coordination

### Owned paths

- `src/kis_mcp/discover/**`;
- `tests/discover/**`;
- `contracts/discover/**`;
- `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`;
- `docs/development/discover-foundation/**`;
- `.work/changes/005-discover-foundation/**`.

### Shared paths

The exact shared paths are declared in `scope.json`. Changes to them MUST remain additive and minimal.

`006-provider-state-atomicity` shares `src/kis_mcp/server.py` and identifies this change as integration owner. Discover registration MUST use one narrow function call so the provider-lifecycle change can integrate independently.

`004-live-proxy-commissioning` owns no Discover production path and explicitly excludes `src/kis_mcp/**`, settings, and operational documentation.

### Excluded implementation

This slice MUST NOT modify Desktop Commander resolution, Work middleware, the three-rule policy evaluator, quarantine storage, quarantine integrity, live commissioning support, or provider-state lifecycle implementation.

## Architectural decisions

### AD-001 — sdk-tool is the primary donor

The implementation MUST start from sdk-tool Phase 1 and Phase 2 contracts and dependency direction rather than design a separate clean-room Discover architecture.

Primary pinned donor:

```text
sdk-tool feat/phase2-project-intelligence
fd1e6a7ab3dac31463aaf1340656df41542f446b
```

The implementation MUST preserve these sdk-tool boundaries where applicable:

```text
immutable portable contracts
        ↓
JSON-backed settings and limits
        ↓
provider-neutral ReadAuthority
        ↓
project scanner and pure analyzers
        ↓
service/coordinator normalization
        ↓
thin tool registration seam
        ↓
FastMCP composition root
```

### AD-002 — dev-intel supplies inspect_project parity

The repository scanner, detectors, local Git summary, evidence links, confidence, assumptions, unknowns, and compaction behavior MUST be adapted from the pinned dev-intel implementation rather than independently recreated.

### AD-003 — no sibling runtime dependency

Production code, tests, configuration, and packaging MUST NOT import, install, execute, or locate `sdk-tool`, `dev-intel-tool`, or `mcp-tool` at runtime.

### AD-004 — one public workflow

This slice exposes exactly one new public tool:

```text
inspect_project
```

Internal architecture MAY contain reusable scanner, detector, Git, Python-index, verification-discovery, and budgeting services. It MUST NOT expose sdk-tool compatibility tools such as `analysis_analyze_source`, `analysis_analyze_project`, `project_discover_workflows`, or `analysis_index_python_project` as separate public tools in this slice.

### AD-005 — pure Python structural intelligence is included

The sdk-tool bounded Python project index is pure in-process analysis, not a semantic-provider integration. `inspect_project` MAY include a bounded Python Code Atlas containing modules, symbols, imports, inheritance, calls, cycles, syntax diagnostics, and unresolved relationships.

Serena, language servers, external processes, persistent semantic indexes, embeddings, and remote evidence remain deferred.

### AD-006 — Work policy remains closed

Discover path, read, parse, configuration, and budget failures are structural Discover errors. They MUST NOT use HR-001, HR-002, or HR-003 codes.

Work continues to block or transform only the three prohibited outcomes in `docs/TRUST-MODEL.md`.

## Planned package structure

```text
src/kis_mcp/discover/
├── __init__.py
├── contracts.py
├── errors.py
├── settings.py
├── read_authority.py
├── scanner.py
├── detectors.py
├── git_reader.py
├── python_index.py
├── verification.py
├── budgeting.py
├── service.py
└── tools.py
```

The exact file count MAY reduce when two responsibilities remain demonstrably cohesive. The implementation MUST NOT create a premature domain/application/adapters hierarchy.

## Requirements

### REQ-001 — Complete target roadmap is authoritative

`docs/DISCOVER-MODULE-PRODUCT-SPEC.md` MUST preserve the complete D0–D8 target roadmap, including `inspect_project`, `inspect_change`, `get_code_context`, semantic providers, verification handoffs, provider harvesting, API and contract intelligence, and cross-repository discovery.

This slice implements only D0 and the bounded D1 subset declared here.

### REQ-002 — Immutable versioned public contracts

Add immutable JSON-compatible contracts for at least:

- `ProjectIdentity`;
- `EvidenceSource`;
- `Provenance`;
- `EvidenceItem`;
- `Confidence`;
- `TrustState`;
- `Freshness`;
- `EvidenceBudget`;
- `TruncationState`;
- `ProjectTopology`;
- `ManifestEvidence`;
- `VerificationDeclaration`;
- `GitSummary`;
- `ProjectDiagnostic`;
- `Finding`;
- `Recommendation`;
- `Unknown`;
- `Handoff`;
- `InspectProjectRequest`;
- `InspectProjectResponse`.

The public response MUST use `schema_version=1` and these stable top-level fields:

```text
schema_version
tool
project
repository_atlas
code_atlas
verification
contracts
instructions
git
remote
providers
evidence
findings
recommendations
handoffs
assumptions
unknowns
confidence
truncated
truncation_reasons
```

Add portable JSON schemas beneath `contracts/discover/**` with `additionalProperties: false` for stable envelopes.

### REQ-003 — Strict JSON-backed Discover settings

Add a `discover` settings block to `settings/kis-mcp.settings.json` and parse it strictly through immutable settings contracts.

The three-rule policy JSON MUST remain unchanged.

Required configured limits include:

| Setting | Initial maximum | Donor basis |
|---|---:|---|
| Files inspected | 5,000 | dev-intel default |
| Directories inspected | 1,000 | dev-intel default |
| Aggregate content bytes | 20,000,000 | dev-intel default |
| Bytes from one file | 512,000 | dev-intel and sdk-tool |
| Returned evidence items | 500 | dev-intel default |
| Serialized output characters | 1,000,000 | dev-intel default |
| Traversal depth | 12 | dev-intel default |
| Visited traversal entries | 50,000 | mcp-tool guard |
| Traversal deadline seconds | 30 | mcp-tool guard |
| Git deadline seconds | 5 | dev-intel Git reader |
| Git output bytes | 200,000 | dev-intel default |
| Python AST nodes | 200,000 | sdk-tool analysis limits |
| Python structural records | 2,000 | sdk-tool analysis limits |

A request MAY lower supported budgets but MUST NOT raise them above configured maxima. Invalid limits return a structural error naming the field, accepted range, and correction.

### REQ-004 — Canonical project identity and ReadAuthority

`inspect_project` accepts one local directory path.

The implementation MUST:

- resolve the canonical path;
- require it to equal or remain beneath `C:\Projects`;
- reject missing paths, files, prefix collisions, UNC/device paths, NULs, and escaped roots;
- inspect every path component for symlinks, junctions, and reparse points;
- return repository-relative, forward-slash, case-preserving labels;
- revalidate file identity and size at read time;
- reject multiply linked files where the configured hard-link posture requires it;
- expose inspection, enumeration, and relative bounded-read operations through a provider-neutral `ReadAuthority` protocol.

### REQ-005 — Bounded deterministic scanner

The scanner MUST use no-follow streaming traversal and enforce directory, file, entry, depth, byte, and duration limits.

It MUST exclude generated or control paths by default, including:

- `.git`;
- `.work`;
- `.temp`;
- `.venv` and `venv`;
- `node_modules`;
- Python and tool caches;
- coverage output;
- `build`, `dist`, and equivalent generated output;
- central generated state beneath `C:\Projects\.kis-mcp`.

The scanner MUST report exclusions and omission reasons. It MUST NOT imply complete coverage after truncation or an unsafe-entry skip.

### REQ-006 — Repository and verification detectors

The first implementation MUST detect bounded evidence for:

- languages and file types;
- manifests and lock files;
- package managers and workspaces;
- frameworks and build systems where donor detectors support them;
- likely entry points;
- test, lint, type-check, format, build, package, documentation, policy, and repository-verification declarations;
- CI and automation configuration;
- `AGENTS.md`, README, architecture, operations, security, testing, and governance documents;
- OpenAPI, JSON Schema, GraphQL, Protobuf/gRPC, AsyncAPI, database, and MCP contract artifacts by file evidence;
- generated, vendored, and excluded paths.

Verification candidates MUST use:

```text
authority = discovered_only
execution_available = false
```

Repository command text is evidence and MUST NOT authorize Work execution.

### REQ-007 — Bounded pure Python Code Atlas

For Python repositories, `inspect_project` MAY return a bounded structural Code Atlas adapted from sdk-tool.

The index MUST use `ast.parse()` only and MUST NOT import, compile, evaluate, reflect over, or execute project code.

It SHOULD include:

- modules and packages;
- qualified classes, functions, async functions, and methods;
- imports and internal/external classification;
- inheritance edges;
- bounded call expressions;
- syntax diagnostics;
- duplicate symbols;
- unresolved relative imports;
- internal import cycles;
- explicit limits and truncation.

### REQ-008 — Fixed-template local Git evidence

The Git reader MUST:

- validate normal repository and linked-worktree metadata;
- use fixed direct argument arrays;
- disable prompts, paging, fsmonitor, external diff, and text conversion;
- isolate global and system Git configuration where practical;
- bound duration, stdout, and stderr;
- sanitize remotes by removing credentials, query strings, and fragments;
- avoid hooks, filters, network access, index writes, ref writes, config writes, and worktree mutation.

A non-Git directory remains inspectable and returns an explicit unavailable or non-repository `GitSummary`.

### REQ-009 — Evidence, confidence, unknowns, and compaction

Every material claim MUST link to evidence.

The service MUST return:

- unique evidence IDs;
- source and provenance;
- trust and confidence;
- findings and recommendations with resolvable evidence references;
- assumptions and unknowns;
- explicit truncation reasons and counters;
- deterministic ordering;
- bounded serialized output.

Compaction MUST preserve the public envelope, identity, material findings, retained evidence dependencies, unknowns, truncation, confidence, and handoffs.

Exact evidence capacity MUST not be treated as truncation. Exceeding capacity MUST set truncation and record the applicable reason.

### REQ-010 — Thin composition seam

Add:

```python
register_discover_tools(server, runtime)
```

or a function with equivalent narrow ownership in `src/kis_mcp/discover/tools.py`.

`build_server()` MAY construct the Discover service and call this seam. It MUST NOT contain scanner, detector, Git, Python-index, or budgeting logic.

Existing Desktop Commander and KIS Work tool names and schemas MUST remain unchanged.

### REQ-011 — Plane and dependency boundaries

Discover production modules MUST NOT import:

- `kis_mcp.desktop_commander`;
- `kis_mcp.middleware`;
- `kis_mcp.policy`;
- `kis_mcp.quarantine` or quarantine integrity;
- FastMCP transport internals outside the thin binder;
- network client libraries;
- subprocess or shell execution;
- donor repository packages.

Architecture tests MUST enforce the dependency direction.

### REQ-012 — Donor parity

At minimum, parity tests MUST preserve:

#### sdk-tool

- immutable JSON-compatible contracts;
- provider-neutral `ReadAuthority`;
- strict JSON settings parsing;
- deterministic coordinator/service behavior;
- workflow discovery remains non-executable evidence;
- pure Python index behavior and safety;
- thin tool registration;
- architecture boundaries.

#### dev-intel-tool

- complete path-chain revalidation;
- symlink/reparse rejection;
- hard-link rejection;
- size revalidation after snapshot;
- depth omission reporting;
- conventional extensionless files;
- deterministic detector ordering;
- malformed-manifest diagnostics;
- Git fsmonitor disabling;
- remote credential redaction;
- exact evidence-capacity behavior;
- serialized output compaction.

#### mcp-tool

- streaming traversal deadline and visited-entry limits;
- Git metadata directory and worktree-file validation;
- isolated Git configuration;
- disabled external diff and text conversion;
- bounded stdout and stderr;
- structured corrective diagnostics.

Each adopted behavior MUST be traced in `source-harvest.md` to an exact donor revision, source path, destination, and parity test.

### REQ-013 — Documentation and implementation claims

Update `SPEC.md`, README, and operations documentation only after implementation and verification prove the new surface.

The full product roadmap remains target state. The first slice MUST not claim implementation of `inspect_change`, `get_code_context`, remote evidence, semantic providers, provider harvesting, Govern, or Work workflow orchestration.

## Public error contract

Structural Discover failures MUST return or raise a stable error containing:

- `code`;
- `message`;
- `field` where applicable;
- `reason`;
- accepted range or constraint where applicable;
- one or more corrective actions;
- `retryable`.

Errors MUST NOT expose stack traces, secrets, donor paths, provider modules, arbitrary environment values, or protected content.

## Out of scope

- `inspect_change`;
- `get_code_context`;
- Serena or another semantic provider;
- persistent indexes or caches;
- embeddings or vector retrieval;
- GitHub, GitLab, connectors, or remote evidence;
- provider harvesting or admission execution;
- OpenAPI semantic linking beyond artifact discovery;
- governance evaluation;
- reviews, audits, or debugging workflows;
- Work planning, proposal, verification execution, or mutation;
- new Work policy rules;
- new runtime dependencies.

## Acceptance criteria

1. **Given** the checked-in detailed product specification, **when** future Discover phases are planned, **then** D0–D8 scope, boundaries, dependencies, acceptance criteria, and donor strategy are present without being represented as current implementation.
2. **Given** a deterministic fixture repository beneath `C:\Projects`, **when** `inspect_project` runs twice with identical configuration and state, **then** the serialized substantive responses are equal.
3. **Given** a project containing supported manifests, scripts, instructions, contracts, source files, tests, and Git metadata, **when** inspection completes within budget, **then** all applicable response sections contain evidence-backed results with confidence and provenance.
4. **Given** excluded directories, symlinks, junctions, reparse points, and multiply linked files, **when** inspection runs, **then** unsafe entries are not traversed or read and omissions are explicit.
5. **Given** any valid configured budget is exhausted, **when** inspection runs, **then** the response remains schema-valid, partial, and explicit about each exhausted limit and counter.
6. **Given** an invalid path or budget, **when** the tool is called, **then** it returns a structural Discover error without an HR policy code.
7. **Given** a Python project, **when** structural indexing runs, **then** top-level project code is not executed and bounded module, symbol, import, inheritance, call, and diagnostic evidence is returned.
8. **Given** hostile local Git configuration, **when** Git evidence is collected, **then** fsmonitor, external diff, text conversion, prompts, paging, and network effects remain disabled.
9. **Given** the assembled FastMCP server, **when** tools are listed, **then** `inspect_project` is present and existing Work schemas are unchanged.
10. **Given** donor repositories are absent, **when** kis-mcp is installed and verified, **then** Discover builds and all tests pass.
11. **Given** architecture tests, **when** imports are inspected, **then** Discover has no dependency on Work adapters, Work policy, quarantine, network, process execution, or donor packages.
12. **Given** the final branch, **when** scope and canonical repository verification run, **then** both pass on the current state.

## Risks and recovery

| Risk | Control |
|---|---|
| Repository traversal escapes or exposes excessive content | Canonical identity, ReadAuthority, no-follow traversal, explicit budgets, exclusions, and negative tests |
| Donor code introduces incompatible policy or product assumptions | Source-harvest register, adaptation review, no runtime dependency, and parity tests |
| Public response grows without control | Stable envelope, result budgeter, compaction, and output-size tests |
| Heuristics overstate certainty | Provenance, confidence, unknowns, and explicit relationship types |
| Python index is mistaken for complete semantic resolution | Static/pure labeling, diagnostics, limits, and deferred semantic-provider phase |
| Shared server composition conflicts with parallel provider-lifecycle work | One narrow registration seam and explicit integration ownership |
| Target roadmap is mistaken for current capability | Separate target specification, current `SPEC.md`, and implementation-status verification |

Recovery is branch abandonment or revert. The slice introduces no migration, persistent index, remote state, provider installation, or repository mutation.

## Requirement traceability

| Requirements | Planned task | Primary evidence |
|---|---|---|
| REQ-001, REQ-013 | Task 1 | target specification and documentation checks |
| REQ-002, REQ-003 | Task 2 | contract, schema, and configuration tests |
| REQ-004, REQ-005 | Task 3 | identity, ReadAuthority, scanner, exclusion, and hardening tests |
| REQ-006 | Task 4 | detector and verification-discovery fixture tests |
| REQ-007 | Task 5 | Python index safety and structural fixture tests |
| REQ-008 | Task 6 | Git and worktree fixture tests |
| REQ-009 | Task 7 | service, evidence-reference, determinism, and compaction tests |
| REQ-010, REQ-011 | Task 8 | tool registration, public contract, and architecture tests |
| REQ-012 | Tasks 2–8 | source-harvest register and parity tests |
| REQ-013 | Task 9 | current-state documentation and full verification |
