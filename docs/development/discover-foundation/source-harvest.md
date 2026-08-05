# Discover Source Harvest Register

## Purpose

This register records the exact donor implementation evidence used by `005-discover-foundation`.

Donor repositories are source material only. `kis-mcp` MUST contain its own adapted implementation, contracts, configuration, and tests. Production code MUST NOT import, execute, install, or locate sibling repositories at runtime.

## Donor priority

1. `sdk-tool` — primary architecture and implementation donor.
2. `dev-intel-tool` — repository-inspection parity and hardening donor.
3. `mcp-tool` — selected traversal, Git, and diagnostic hardening donor.

## sdk-tool

### Pinned evidence

| Source | Revision | Purpose |
|---|---|---|
| `feat/phase2-project-intelligence` | `fd1e6a7ab3dac31463aaf1340656df41542f446b` | Complete Phase 1 analysis plus Phase 2 workflow discovery, Python project intelligence, verification boundaries, contracts, and tests |
| `main` | `9832a1f` | Progressive tool discovery and governance-contract baseline |
| `feat/skill-catalogue-serena-plan` | `a058464742bf5c05b4f902bb8e0ee08ff5ba06fa` | Bounded skill catalogue and Serena semantic-provider design |

### Adaptation matrix

| Donor path or concept | kis-mcp destination | Adopted behavior | Required parity evidence |
|---|---|---|---|
| `src/sdk_tool/core/read_authority.py` | `src/kis_mcp/discover/read_authority.py` | Provider-neutral inspect, enumerate, and relative bounded read contract | Read-authority unit tests; no Work adapter imports |
| `src/sdk_tool/core/contracts.py` | `src/kis_mcp/discover/service.py`, `src/kis_mcp/discover/tools.py` | Immutable service ownership, thin tool metadata, and backend-neutral construction | Service orchestration and registration tests |
| `src/sdk_tool/analysis/contracts.py` | `src/kis_mcp/discover/contracts.py`, `contracts/discover/**` | Immutable JSON-compatible evidence, diagnostics, results, limits, and errors | Serialization and JSON-schema tests |
| `src/sdk_tool/analysis/settings.py` | `src/kis_mcp/discover/settings.py`, `src/kis_mcp/config.py` | Strict JSON-backed limits and exact-key validation | Configuration positive and negative tests |
| `src/sdk_tool/analysis/registry.py` and availability model | Later Discover provider registry | Installed, configured, ready, and exposed state separation | Deferred to provider-registry slice |
| `src/sdk_tool/analysis/coordinator.py` | `src/kis_mcp/discover/service.py`, `budgeting.py` | Coordinator-owned normalization, deterministic aggregation, limits, partial results, and errors | Determinism, partial-result, and compaction tests |
| `src/sdk_tool/analysis/adapters/python_ast.py` | `src/kis_mcp/discover/python_index.py` or a focused parser module | Pure Python parsing without import or execution | Safety, syntax, symbol, import, node-limit, and deterministic ordering tests |
| `src/sdk_tool/project_intelligence/workflows.py` | `src/kis_mcp/discover/verification.py` | Repository workflow discovery with `discovered_only` authority and `execution_available=false` | Python, Node, PowerShell, CI, malformed input, ordering, and limit tests |
| `src/sdk_tool/project_intelligence/python_index.py` | `src/kis_mcp/discover/python_index.py` | Modules, symbols, imports, inheritance, calls, cycles, syntax diagnostics, and limits | Project-index fixture tests; no execution tests |
| `src/sdk_tool/tools/project_workflows.py` | `src/kis_mcp/discover/tools.py` | Thin public binder delegating to an owning service | Architecture and registration tests |
| `tests/test_phase2_modularity_boundaries.py` | `tests/discover/test_architecture.py` and shared architecture tests | Discover remains pure, backend-neutral, and separate from Work | AST import-boundary tests |
| `docs/integrations/SERENA.md` | Product roadmap only | Read-only semantic sidecar strategy behind normalized contracts | Deferred to D3 evaluation |

### Explicitly rejected from this slice

- sdk-tool product identity and standalone runtime;
- duplicate FastMCP or official MCP backend hosts;
- sdk-tool Work or verification policy model;
- verification worker and process execution;
- broad analysis compatibility tool catalogue;
- semantic-provider integration;
- skill catalogue implementation;
- provider installation or tunnel code.

## dev-intel-tool

### Pinned evidence

| Source | Revision | Purpose |
|---|---|---|
| repository baseline | `26d1a2f` | Current repository intelligence implementation |
| inspect hardening | `ae73081` | Hardened scanner, Git, output, and release contract behavior |
| change-impact intelligence | `a6af216bf09c59c659b16697673c2149d6fdbea1` | Ordered analyzers, architecture components, local Python and JavaScript/TypeScript dependencies, change impact, test targeting, and validation strategy |

### Adaptation matrix

| Donor path or concept | kis-mcp destination | Adopted behavior | Required parity evidence |
|---|---|---|---|
| `src/dev_intel_tool/repository.py` | `src/kis_mcp/discover/scanner.py` | Deterministic snapshot, complete path-chain checks, reparse rejection, regular-file and hard-link controls, omission reasons | Symlink, junction, hard-link, depth, file, directory, and byte-limit tests |
| `src/dev_intel_tool/detectors.py` | `src/kis_mcp/discover/detectors.py` | Languages, manifests, frameworks, workspaces, package managers, entry points, instructions, CI, and verification detection | Fixture matrix and detector ordering tests |
| `src/dev_intel_tool/git_reader.py` | `src/kis_mcp/discover/git_reader.py` | Fixed read-only local Git templates, isolated config, fsmonitor disabling, remote redaction, bounded output | Git and non-Git fixture tests; hostile config tests |
| `src/dev_intel_tool/inspection.py` | `src/kis_mcp/discover/service.py`, `budgeting.py` | Evidence linking, findings, recommendations, assumptions, unknowns, confidence, truncation, and output compaction | Evidence reference tests; exact-capacity and serialized-output tests |
| `src/dev_intel_tool/models.py` | `src/kis_mcp/discover/contracts.py` | Project map and response vocabulary where compatible with the approved Discover schema | Contract schema tests |
| `tests/test_hardening.py` | `tests/discover/test_scanner_hardening.py`, `test_git_reader.py`, `test_budgeting.py` | Proven negative and edge-case behavior | Ported or stronger parity tests |
| schema snapshot tests | `contracts/discover/**`, `tests/discover/test_schema_contracts.py`, `tests/discover/test_independent_install.py` | Stable public schema and donor-independent import behavior | Contract drift and isolated import tests |

### Explicitly rejected from this slice

- standalone policy and server identity;
- GitHub connector request processing;
- remote network evidence;
- installer and tunnel implementation;
- direct runtime dependency or editable install;
- product-specific finding language that conflicts with the approved kis-mcp contract.

## mcp-tool

### Pinned evidence

| Source | Revision | Purpose |
|---|---|---|
| stable `main` | `246fb10` | Mature filesystem and Git operation patterns |
| later branch review | `31a915f` | Structured Git precondition diagnostics reviewed as a pattern, not treated as stable donor code |

### Adaptation matrix

| Donor path or concept | kis-mcp destination | Adopted behavior | Required parity evidence |
|---|---|---|---|
| `src/mcp_tool/filesystem.py` | `src/kis_mcp/discover/scanner.py` | Streaming `os.scandir()` traversal, deadline, visited-entry and scanned-byte ceilings, path and reparse validation | Deadline, entry, byte, and link tests |
| `src/mcp_tool/git_tools.py` | `src/kis_mcp/discover/git_reader.py` | Git metadata directory and worktree-file validation, isolated environment, disabled external diff/textconv, bounded stdout/stderr | Worktree metadata and hostile configuration tests |
| structured precondition diagnostics | `src/kis_mcp/discover/errors.py` or contracts | Stable code, reason, field, accepted range, and corrective action | Public error contract tests |
| dedicated-operation preference | Discover/Work handoff contract | Verification evidence does not become arbitrary executable authority | Handoff tests |

### Explicitly rejected from this slice

- mutation tools;
- command runner and process execution;
- Git or GitHub mutation;
- worktree creation, merge, or cleanup;
- downloads and file-producing exports;
- browser or database execution;
- mcp-tool policy rules and capability catalogue;
- external provider and tunnel code.

## Implemented parity checkpoint: Task 2

| Donor | Source behavior adapted | kis-mcp implementation | Passing evidence |
|---|---|---|---|
| `sdk-tool` `fd1e6a7` | Immutable JSON-compatible analysis records and fixed public envelope ownership | `src/kis_mcp/discover/contracts.py`, `src/kis_mcp/discover/errors.py` | `tests/discover/test_contracts.py::test_evidence_contract_is_immutable_and_json_compatible`; `test_inspect_project_response_has_exact_versioned_envelope`; `test_all_planned_d0_d1_record_types_are_immutable_and_serializable` |
| `sdk-tool` `fd1e6a7` | Strict JSON-backed positive limits and request-side narrowing | `src/kis_mcp/discover/settings.py`, `src/kis_mcp/config.py`, `settings/kis-mcp.settings.json` | `tests/discover/test_settings.py`; `tests/test_config.py::test_invalid_discover_settings_are_rejected` |
| `sdk-tool` `fd1e6a7` | Portable strict schema envelopes | `contracts/discover/evidence.schema.json`, `inspect-project-request.schema.json`, `inspect-project-response.schema.json` | `tests/discover/test_schema_contracts.py` |
| kis-mcp authority | Discover structural failures remain separate from the three Work rules | `src/kis_mcp/discover/errors.py` | `tests/discover/test_contracts.py::test_structural_error_is_corrective_and_not_a_work_policy_decision`; existing `tests/test_public_contracts.py` regression suite |

Intentional adaptation differences:

- Discover limits live in the existing `settings/kis-mcp.settings.json`; no new policy extension was added.
- The first public contract is `inspect_project`, not sdk-tool's compatibility `analysis_*` surface.
- Temporal request IDs and timestamps are deferred until a workflow requires them; deterministic repository evidence is primary.
- The public response preserves empty target-state sections so later phases can extend behavior without changing top-level identity.

## Implemented parity checkpoint: Task 3

| Donor | Source behavior adapted | kis-mcp implementation | Passing evidence |
|---|---|---|---|
| `sdk-tool` `fd1e6a7` | One provider-neutral repository read boundary with immutable project identity | `src/kis_mcp/discover/read_authority.py` | `tests/discover/test_identity.py`; `tests/discover/test_read_authority.py` |
| `dev-intel-tool` `ae73081` | Component-by-component link/reparse rejection, regular-file validation, bounded safe open, identity revalidation, configured decoding, and optional hard-link rejection | `src/kis_mcp/discover/read_authority.py` | size-change, missing-file, hard-link, relative-path, and link-chain tests in `tests/discover/test_read_authority.py` |
| `dev-intel-tool` `26d1a2f` | Deterministic repository labels, configured file selection, exclusions, and category hints | `src/kis_mcp/discover/scanner.py` | `tests/discover/test_scanner.py::test_scanner_recurses_deterministically_and_reports_exclusions` |
| `mcp-tool` `146ee76` | Streaming `os.scandir` traversal, monotonic deadline, visited-entry ceiling, explicit depth/directory/file/byte limits, and Windows hard-link metadata fallback | `src/kis_mcp/discover/scanner.py` | `tests/discover/test_scanner.py`; `tests/discover/test_scanner_hardening.py` |

Intentional adaptation differences:

- The project boundary is supplied by kis-mcp runtime configuration; it is not copied from donor policy objects.
- File extensions, conventional filenames, exclusions, encodings, limits, and hard-link handling are controlled by `settings/kis-mcp.settings.json`.
- Configured exclusions are reported but do not imply truncation; unsafe or budget-omitted evidence does.
- Scanner output contains sanitized repository-relative labels and never reads project file contents.
- Discover failures use `DISCOVER_*` structural codes and never create an additional Work policy rule.

## Implemented parity checkpoint: Task 4

| Donor | Source behavior adapted | kis-mcp implementation | Passing evidence |
|---|---|---|---|
| `dev-intel-tool` `26d1a2f` | Language, manifest, framework, package-manager, workspace, entry-point, instruction, documentation, CI, contract-artifact, module, diagnostic, and unknown-state detection | `src/kis_mcp/discover/detectors.py` | `tests/discover/test_detectors.py` |
| `sdk-tool` `fd1e6a7` | Python, uv, pytest, unittest, Node package-script, PowerShell, and GitHub Actions workflow discovery | `src/kis_mcp/discover/verification.py` | `tests/discover/test_verification_discovery.py` |
| `sdk-tool` `fd1e6a7` | Discovered commands remain evidence-only with `authority="discovered_only"` and `execution_available=false` | `src/kis_mcp/discover/verification.py` | `test_discovers_python_node_powershell_and_ci_without_execution` |
| kis-mcp settings authority | Candidate count, file bytes, scanner selection, manifest suffixes, conventional filenames, and exclusions are JSON-controlled | `settings/kis-mcp.settings.json`, `src/kis_mcp/discover/settings.py` | `tests/discover/test_settings.py`; candidate-narrowing and scanner tests |

Intentional adaptation differences:

- Root `pyproject.toml` has deterministic project-name precedence over sibling ecosystem manifests.
- Recognized manifests are not counted as source-language files.
- Evidence IDs include a stable hash suffix so punctuation-normalized names such as C, C#, and C++ cannot collide.
- Package script contents are retained only as source evidence; public declarations expose fixed profile and argument identities and never execute them.
- Broad repository classification is internal to `inspect_project`; no additional public detector tools are introduced.

## Implemented parity checkpoint: Task 5

| Donor | Source behavior adapted | kis-mcp implementation | Passing evidence |
|---|---|---|---|
| `sdk-tool` `fd1e6a7` | Pure AST project indexing for modules, symbols, decorators, bases, imports, inheritance, calls, duplicate symbols, relative-import diagnostics, and import cycles | `src/kis_mcp/discover/python_index.py` | `tests/discover/test_python_index.py` |
| `sdk-tool` `fd1e6a7` | Partial results for syntax errors, node limits, semantic-record limits, and duration limits | `src/kis_mcp/discover/python_index.py` | syntax and limit tests in `tests/discover/test_python_index.py` |
| kis-mcp settings authority | Python nodes, semantic records, files, bytes, evidence diagnostics, and duration are bounded by `settings.discover.limits` | `settings/kis-mcp.settings.json`, `src/kis_mcp/discover/settings.py` | `test_index_limits_return_bounded_partial_results`; `test_index_duration_limit_is_configured_and_deterministic` |

Intentional adaptation differences:

- The index consumes the already authorized repository snapshot rather than independently enumerating files.
- Variable duration measurements are omitted from the public result so repeated identical input produces identical substantive output.
- The index reports explicit truncation reasons rather than one generic limit diagnostic.
- `ast.parse()` is the only Python-analysis mechanism; project modules are never imported or executed.

## Implemented parity checkpoint: Task 6

| Donor | Source behavior adapted | kis-mcp implementation | Passing evidence |
|---|---|---|---|
| `dev-intel-tool` `ae73081` | Fixed local Git templates, branch/head/status/remotes/history, credential redaction, global deadline, and isolated configuration | `src/kis_mcp/discover/git_reader.py` | `tests/discover/test_git_reader.py`; `tests/discover/test_git_hardening.py` |
| `mcp-tool` `146ee76` | Linked-worktree metadata validation, project-boundary enforcement, no-follow metadata reads, fixed environment controls, and bounded command output | `src/kis_mcp/discover/git_reader.py` | metadata, hostile configuration, timeout, fixed-command, and short-read tests |
| kis-mcp settings authority | Git timeout, output bytes, history count, and metadata bytes are JSON-configured | `settings/kis-mcp.settings.json`, `src/kis_mcp/discover/settings.py` | `tests/discover/test_settings.py`; Git limit tests |

Intentional adaptation differences:

- Git output is drained through bounded streaming threads rather than captured unbounded and sliced afterward.
- Tracked-file count is maintained while streaming NUL-delimited output, even when retained output is truncated.
- Only local read-only commands are present; no fetch, pull, push, config mutation, checkout, reset, or ref mutation template exists.
- `.git` directory or linked-worktree metadata is validated before Git is launched.
- Recent commits are included in the versioned `GitSummary` contract under the configured history limit.

## Implemented parity checkpoint: Task 7

| Donor | Source behavior adapted | kis-mcp implementation | Passing evidence |
|---|---|---|---|
| `sdk-tool` `fd1e6a7` | Coordinator-owned deterministic aggregation and partial-result handling | `src/kis_mcp/discover/service.py` | `tests/discover/test_inspect_project.py`; `test_inspect_project_determinism.py`; `test_inspect_project_compaction.py` |
| `dev-intel-tool` `26d1a2f` + `ae73081` | Evidence linking, findings, recommendations, assumptions, unknowns, confidence, truncation, and output compaction | `src/kis_mcp/discover/service.py`, `src/kis_mcp/discover/budgeting.py` | `tests/discover/test_budgeting.py`; service integrity and exact-capacity tests |
| kis-mcp authority | Invalid request budgets become corrective `DISCOVER_LIMIT_INVALID` errors, not Work-policy decisions | `src/kis_mcp/discover/service.py` | `tests/discover/test_inspect_project.py::test_invalid_request_limits_return_structural_discover_error` |

Intentional adaptation differences:

- One `inspect_project` service owns the complete local evidence response rather than exposing donor-compatible analysis tools.
- Result compaction is deterministic and preserves the versioned response identity, truncation reasons, and valid evidence references.
- Remote and semantic evidence remain explicit unknown/provider-unavailable states in this local foundation slice.

## Implemented parity checkpoint: Task 8

| Donor | Source behavior adapted | kis-mcp implementation | Passing evidence |
|---|---|---|---|
| `sdk-tool` `fd1e6a7` | Thin public binder delegating to an owning service | `src/kis_mcp/discover/tools.py` | `tests/discover/test_tool_registration.py` |
| `sdk-tool` `fd1e6a7` | Plane dependency and prohibited-import boundaries | `tests/discover/test_architecture.py` | Work, provider, donor, network, FastMCP, subprocess, and traversal boundary tests |
| donor-independent package requirement | Discover imports without sibling donor repositories | `src/kis_mcp/discover/**` | `tests/discover/test_independent_install.py` |
| kis-mcp composition root | Exactly one additive `inspect_project` registration while existing local tools remain present | `src/kis_mcp/server.py` | `test_build_server_adds_discover_without_changing_existing_local_tools` |

Intentional adaptation differences:

- FastMCP appears only in `discover/tools.py`; all discovery implementation remains framework-neutral.
- The public binder returns structured `DISCOVER_*` errors and does not add an HR code, policy rule, command allowlist, or provider restriction.
- The tool is annotated read-only, non-destructive, idempotent, and closed-world for its bounded local evidence scope.

## Implemented parity checkpoint: change-impact intelligence

| Donor | Source behavior adapted | kis-mcp implementation | Passing evidence |
|---|---|---|---|
| `dev-intel-tool` `a6af216` | Immutable analyzer context/output contracts, deterministic registration, and ordered pipeline aggregation | `src/kis_mcp/discover/analyzers/contracts.py`, `registry.py`, `pipeline.py` | `tests/discover/impact_parity/test_analyzer_pipeline.py` |
| `dev-intel-tool` `a6af216` | Repository map and bounded architecture-component grouping | `src/kis_mcp/discover/analyzers/repository_map.py`, `architecture.py` | `tests/discover/impact_parity/test_architecture_analyzer.py` |
| `dev-intel-tool` `a6af216` | Local Python imports plus static relative JavaScript/TypeScript `import`, `export-from`, and `require` resolution | `src/kis_mcp/discover/analyzers/dependencies.py` | `tests/discover/impact_parity/test_dependency_analyzer.py` |
| `dev-intel-tool` `a6af216` | Direct and bounded transitive reverse dependency impact, affected-test targeting, category evidence, and low-confidence task-token candidates | `src/kis_mcp/discover/analyzers/change_impact.py`, `src/kis_mcp/discover/impact_graph.py` | `tests/discover/impact_parity/test_change_impact_parity.py`; existing impact regression and determinism suites |

Intentional adaptation differences:

- The analyzer pipeline consumes existing kis-mcp `ReadAuthority`, repository snapshot, Python index, and verification contracts; donor policy, settings, runtime, and server objects are not imported.
- JavaScript and TypeScript parsing is static and local. Dynamic imports, package-resolution semantics, aliases, external modules, and unresolved paths remain explicit unknowns.
- Task-token matches are low-confidence heuristic candidates only and never become deterministic dependency edges.
- Public `inspect_impact` schema identity remains version 1; JavaScript/TypeScript dependency evidence uses existing dependant records and parser-confirmed affected-test provenance.
- Standalone donor runtime, GitHub execution, networking, installers, tunnel code, duplicate policy/settings authority, and product-specific wording remain excluded.

## Required independence test

The branch passes donor-independent import verification with `dev-intel-tool`, `sdk-tool`, and `mcp-tool` absent from the isolated interpreter module path. No production module imports, installs, executes, or locates those repositories.

## Adaptation recording rule

Each implementation task MUST update this register with:

- donor repository and exact revision;
- donor path;
- kis-mcp destination;
- behavior preserved;
- behavior intentionally changed;
- parity-test path and test name;
- unresolved difference or residual risk.
