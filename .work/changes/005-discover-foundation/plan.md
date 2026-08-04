# Discover Foundation and inspect_project Implementation Plan

> **For agentic workers:** Execute this plan task-by-task in `C:\Projects\kis-mcp\.work\worktrees\005-discover-foundation`. Keep `scope.json`, `tasks.md`, `source-harvest.md`, tests, and current implementation claims synchronized.

**Goal:** Adopt the complete Discover roadmap and implement one deterministic, bounded, read-only `inspect_project` workflow using the proven sdk-tool analysis/project-intelligence architecture, dev-intel repository-inspection parity, and selected mcp-tool hardening.

**Architecture:** Add one provider-neutral `kis_mcp.discover` package. Immutable contracts and JSON settings feed a central `ReadAuthority`; scanner, detector, Git, verification-discovery, and pure Python-index services return normalized evidence to an `InspectProjectService`; a thin `register_discover_tools(...)` binder adds one public tool to the existing FastMCP composition root. Discover does not import Work adapters or policy implementation.

**Tech stack:** Python 3.11+, standard library, dataclasses, `ast`, fixed local Git subprocess templates, JSON Schema, FastMCP 3.4.4, pytest, existing PowerShell and Python repository verification.

## Global constraints

- Work only inside the declared worktree and `scope.json` paths.
- Use TDD for executable behavior: failing focused test, smallest implementation, focused pass, applicable regression pass.
- Treat `docs/DISCOVER-MODULE-PRODUCT-SPEC.md` as target-state authority and this plan as D0/D1 scope.
- Preserve the current Desktop Commander proxy, Work tool schemas, quarantine, and the closed HR-001/HR-002/HR-003 decision set.
- Add no runtime dependency.
- Do not import or locate donor repositories at runtime.
- Keep server integration to one narrow Discover registration seam because `006-provider-state-atomicity` shares `src/kis_mcp/server.py`.
- Update `docs/development/discover-foundation/source-harvest.md` after every donor adaptation.
- Do not update current implementation claims in `SPEC.md`, README, or operations documentation until the final verified implementation exists.

---

## Task 1: Finalize target documentation and roadmap traceability

**Requirements:** REQ-001, REQ-013

**Files:**

- Create: `docs/DISCOVER-MODULE-PRODUCT-SPEC.md`
- Create: `docs/development/discover-foundation/source-harvest.md`
- Modify: `docs/PLATFORM-CONCEPT.md`
- Modify: `.work/changes/005-discover-foundation/spec.md`
- Modify: `.work/changes/005-discover-foundation/plan.md`
- Modify: `.work/changes/005-discover-foundation/tasks.md`
- Test: documentation/source checks through existing verifier and focused repository searches

- [x] Adapt the approved Discover module specification to the `kis-mcp` identity and Work trust boundary.
- [x] Preserve the complete D0–D8 roadmap.
- [x] Pin sdk-tool, dev-intel-tool, and mcp-tool donor revisions and accepted/rejected scope.
- [x] Link the detailed Discover specification from `docs/PLATFORM-CONCEPT.md`.
- [x] Verify every referenced repository path and relative documentation link exists.
- [x] Verify target-state statements are not represented as current implementation in `SPEC.md` or settings.
- [x] Run the existing documentation and repository verifier applicable before executable changes.

**Checkpoint:** The product roadmap, bounded slice, donor strategy, and deferred phases are independently reviewable before code changes.

---

## Task 2: Add Discover contracts, portable schemas, and JSON settings

**Requirements:** REQ-002, REQ-003, REQ-012

**Files:**

- Create: `src/kis_mcp/discover/__init__.py`
- Create: `src/kis_mcp/discover/contracts.py`
- Create: `src/kis_mcp/discover/errors.py`
- Create: `src/kis_mcp/discover/settings.py`
- Create: `contracts/discover/evidence.schema.json`
- Create: `contracts/discover/inspect-project-request.schema.json`
- Create: `contracts/discover/inspect-project-response.schema.json`
- Modify: `src/kis_mcp/config.py`
- Modify: `settings/kis-mcp.settings.json`
- Modify: `tests/test_config.py`
- Modify: `tests/test_public_contracts.py`
- Create: `tests/discover/test_contracts.py`
- Create: `tests/discover/test_settings.py`
- Create: `tests/discover/test_schema_contracts.py`

### 2.1 Write failing immutable-contract tests

Test:

- stable enum/value sets for confidence, trust, freshness, evidence kind, and provenance;
- frozen dataclasses reject mutation;
- all public `to_json_dict()` results contain only JSON-compatible values;
- evidence IDs and references are non-empty and valid;
- response top-level keys exactly match REQ-002;
- `schema_version=1` and `tool="inspect_project"` are fixed;
- structural errors include code, message, reason, field, correction, and retryable state;
- donor paths, `Path`, exceptions, mapping proxies, tuples, and enums do not leak into serialized output.

Run:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-o cache_dir=C:\Projects\.kis-mcp\pytest-cache'
uv run --offline --no-sync python -m pytest tests/discover/test_contracts.py -q
```

Expected: import failure because the Discover package does not exist.

### 2.2 Implement the smallest complete contract set

Adapt sdk-tool immutable contract and JSON-conversion patterns. Keep public contracts in `discover/contracts.py`; do not put Discover domain records into Work `models.py` unless a record is genuinely shared by another plane.

Required public records:

- `ProjectIdentity`;
- `EvidenceSource`, `Provenance`, `EvidenceItem`;
- `EvidenceBudget`, `TruncationState`;
- topology, manifest, verification, Git, diagnostic, finding, recommendation, unknown, and handoff records;
- `InspectProjectRequest` and `InspectProjectResponse`;
- `DiscoverError` or equivalent stable structural error.

### 2.3 Write failing settings tests

Test exact-key JSON parsing for:

- all limits listed in REQ-003;
- positive integer validation rejecting booleans, zero, negatives, unknown keys, and missing keys;
- configured exclusions and supported filenames/extensions;
- request budgets that may narrow but not broaden configured maxima;
- policy JSON remains byte/content unchanged by Discover settings.

Run:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-o cache_dir=C:\Projects\.kis-mcp\pytest-cache'
uv run --offline --no-sync python -m pytest tests/discover/test_settings.py tests/test_config.py -q
```

Expected: failure because Discover settings are absent.

### 2.4 Implement JSON-backed settings

Add one `discover` object under `settings/kis-mcp.settings.json`. Parse it into an immutable `DiscoverSettings` from `RuntimeConfig`. Keep authorization out of `policy/kis-mcp.policy.json`.

### 2.5 Add portable schemas and drift tests

Schemas MUST use draft 2020-12, stable required fields, and `additionalProperties: false` for envelopes. Add positive and negative fixtures. Extend the existing public-contract verifier only where required to include `contracts/discover/**`.

### 2.6 Verify

Run:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-o cache_dir=C:\Projects\.kis-mcp\pytest-cache'
uv run --offline --no-sync python -m pytest `
  tests/discover/test_contracts.py `
  tests/discover/test_settings.py `
  tests/discover/test_schema_contracts.py `
  tests/test_config.py `
  tests/test_public_contracts.py -q
```

Update `source-harvest.md` with sdk-tool contract/settings donor paths and test names.

**Checkpoint:** Public fields, settings, limits, and structural errors are fixed before traversal code exists.

---

## Task 3: Implement ProjectIdentity, ReadAuthority, and hardened scanner

**Requirements:** REQ-004, REQ-005, REQ-012

**Files:**

- Create: `src/kis_mcp/discover/read_authority.py`
- Create: `src/kis_mcp/discover/scanner.py`
- Create: `tests/discover/conftest.py`
- Create: `tests/discover/test_identity.py`
- Create: `tests/discover/test_read_authority.py`
- Create: `tests/discover/test_scanner.py`
- Create: `tests/discover/test_scanner_hardening.py`

### 3.1 Build deterministic fixture helpers

Fixture repositories MUST be created beneath a permitted test root under `C:\Projects` or through the repository's existing Windows-path test abstraction. Do not weaken production path checks to support temporary test locations.

### 3.2 Write failing identity and authority tests

Cover:

- canonical directory identity;
- missing path and file path;
- outside-root and prefix-collision rejection;
- NUL, UNC, device, and traversal forms;
- repository-relative sanitized labels;
- symlink, junction, and reparse-point rejection at every component;
- regular-file checks;
- read-time size and identity revalidation;
- hard-link rejection where supported;
- extensionless conventional files;
- denied names and generated-path exclusions.

### 3.3 Implement provider-neutral ReadAuthority

Adapt sdk-tool `ReadAuthority` and `ReadOnlyFilesystem` seams while replacing sdk-tool policy ownership with immutable Discover settings and kis-mcp project identity.

Required operations:

```python
inspect(path)
enumerate_files(root, ...)
read_relative_text(root, label, ...)
```

Use sanitized labels in results; absolute paths remain internal except canonical project identity where the public contract explicitly permits it.

### 3.4 Write failing traversal-budget tests

Cover:

- deterministic ordering independent of filesystem enumeration order;
- maximum files;
- maximum directories;
- maximum depth;
- visited-entry ceiling;
- aggregate candidate bytes;
- traversal deadline;
- excluded path reporting;
- unsafe entry reporting;
- exact capacity is not truncation;
- first omitted entry sets the applicable truncation reason.

### 3.5 Implement streaming scanner

Combine dev-intel safety behavior with mcp-tool streaming `os.scandir()` traversal. Use `follow_symlinks=False`, explicit stack/queue ordering, monotonic deadlines, and bounded counters.

### 3.6 Verify

Run:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-o cache_dir=C:\Projects\.kis-mcp\pytest-cache'
uv run --offline --no-sync python -m pytest `
  tests/discover/test_identity.py `
  tests/discover/test_read_authority.py `
  tests/discover/test_scanner.py `
  tests/discover/test_scanner_hardening.py -q
```

Update `source-harvest.md` with sdk-tool, dev-intel, and mcp-tool scanner parity tests.

**Checkpoint:** No detector or parser may bypass ReadAuthority or scan paths directly.

---

## Task 4: Port repository detectors and non-executable verification discovery

**Requirements:** REQ-006, REQ-012

**Files:**

- Create: `src/kis_mcp/discover/detectors.py`
- Create: `src/kis_mcp/discover/verification.py`
- Create: `tests/discover/test_detectors.py`
- Create: `tests/discover/test_verification_discovery.py`
- Create: `tests/discover/fixtures/**` only when compact inline fixtures are insufficient

### 4.1 Write failing detector matrix tests

Cover supported donor evidence for:

- Python, JavaScript/TypeScript, .NET, Java/Kotlin, Go, Rust, C/C++, shell, PowerShell, SQL, and documentation file classification where applicable;
- `pyproject.toml`, lock files, `package.json`, workspace declarations, Cargo, Go, Gradle/Maven, .NET, CMake, Docker, and repository scripts;
- frameworks, package managers, and build systems supported by donor logic;
- likely entry points;
- `AGENTS.md`, README, architecture, operations, security, testing, and governance docs;
- GitHub Actions and other local CI configuration;
- OpenAPI, JSON Schema, GraphQL, Protobuf/gRPC, AsyncAPI, database, and MCP schema artifacts;
- malformed JSON/TOML/XML/YAML-like evidence returning diagnostics rather than unstructured failure;
- deterministic detector and result ordering.

### 4.2 Implement pure detectors

Adapt dev-intel detector tables and algorithms. Detectors consume scanner records and bounded authorized text, never raw project paths.

Each result MUST carry evidence source, provenance, confidence, and a sanitized repository-relative location.

### 4.3 Write failing workflow-discovery tests

Port sdk-tool Phase 2 behavior for:

- Python/uv/pytest/unittest evidence;
- Node scripts;
- PowerShell repository and verification scripts;
- GitHub Actions single-line and block `run` evidence;
- ignored generated/dependency trees;
- malformed `package.json` diagnostics;
- candidate limit and deterministic IDs;
- `authority="discovered_only"`;
- `execution_available=false`;
- no public command execution or executable path.

### 4.4 Implement verification discovery

Adapt sdk-tool `WorkflowDiscoveryService` into a Discover-owned verification inventory. Use fixed candidate profile/operation identities as evidence only. Do not create Work profiles in this slice.

### 4.5 Verify

Run:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-o cache_dir=C:\Projects\.kis-mcp\pytest-cache'
uv run --offline --no-sync python -m pytest `
  tests/discover/test_detectors.py `
  tests/discover/test_verification_discovery.py -q
```

Update `source-harvest.md` with detector and workflow-discovery source paths and parity tests.

**Checkpoint:** Repository classification and verification inventory are complete without process execution.

---

## Task 5: Port the bounded pure Python structural index

**Requirements:** REQ-007, REQ-012

**Files:**

- Create: `src/kis_mcp/discover/python_index.py`
- Create: `tests/discover/test_python_index.py`

### 5.1 Write failing safety tests

Cover:

- top-level file code that writes, raises, imports, or exits is never executed;
- the indexer never calls `exec`, `eval`, project imports, subprocesses, or network APIs;
- source is read only through `ReadAuthority`;
- syntax messages are bounded and omit source lines;
- absolute project paths do not appear in public records.

### 5.2 Write failing structural tests

Cover:

- `src` and package module naming;
- packages and `__init__.py`;
- classes, functions, async functions, methods, decorators, and bases;
- imports, aliases, relative levels, and internal classification;
- inheritance and bounded call edges;
- duplicate symbols;
- unresolved relative imports;
- internal import cycles;
- syntax errors producing partial results;
- deterministic ordering.

### 5.3 Write failing limit tests

Cover file, file-byte, node, structural-record, diagnostic, and duration limits. Partial results retain valid prior records and explicit truncation reasons.

### 5.4 Implement the index

Adapt sdk-tool `project_intelligence/python_index.py`. Keep it inside Discover rather than the general scanner. Use `ast.parse()` only.

### 5.5 Verify

Run:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-o cache_dir=C:\Projects\.kis-mcp\pytest-cache'
uv run --offline --no-sync python -m pytest tests/discover/test_python_index.py -q
```

Update `source-harvest.md` with exact sdk-tool path and parity tests.

**Checkpoint:** `inspect_project` can populate a bounded Python Code Atlas without a semantic provider.

---

## Task 6: Implement fixed-template local Git evidence

**Requirements:** REQ-008, REQ-012

**Files:**

- Create: `src/kis_mcp/discover/git_reader.py`
- Create: `tests/discover/test_git_reader.py`
- Create: `tests/discover/test_git_hardening.py`

### 6.1 Write failing repository metadata tests

Cover:

- normal `.git` directory;
- valid linked-worktree `.git` file;
- malformed, oversized, non-UTF-8, missing-target, linked, outside-root, and non-directory metadata targets;
- non-Git directory returns explicit unavailable summary;
- branch, detached head, status, tracked-file count, bounded log, and sanitized remote identity.

### 6.2 Write failing hostile configuration tests

Cover:

- fsmonitor hook is not invoked;
- external diff and text conversion are disabled;
- pager, prompt, editor, optional locks, and credential prompts are disabled;
- global/system configuration and credential helpers are isolated where practical;
- timeout and output truncation are explicit;
- credentials, query, and fragment are removed from remotes;
- no fetch, pull, push, config mutation, ref mutation, or index mutation occurs.

### 6.3 Implement Git reader

Adapt dev-intel fixed templates and mcp-tool metadata validation. Use one internal bounded runner with `shell=False`, direct arguments, monotonic timeout, and sanitized error records.

### 6.4 Verify

Run:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-o cache_dir=C:\Projects\.kis-mcp\pytest-cache'
uv run --offline --no-sync python -m pytest `
  tests/discover/test_git_reader.py `
  tests/discover/test_git_hardening.py -q
```

Update `source-harvest.md` with Git donor paths and parity tests.

**Checkpoint:** Local Git evidence is safe, bounded, and independent of repository configuration.

---

## Task 7: Compose InspectProjectService, evidence links, and output compaction

**Requirements:** REQ-009, REQ-012

**Files:**

- Create: `src/kis_mcp/discover/budgeting.py`
- Create: `src/kis_mcp/discover/service.py`
- Create: `tests/discover/test_budgeting.py`
- Create: `tests/discover/test_inspect_project.py`
- Create: `tests/discover/test_inspect_project_determinism.py`
- Create: `tests/discover/test_inspect_project_compaction.py`

### 7.1 Write failing service fixture tests

A representative fixture MUST contain:

- source and tests;
- manifests and locks;
- repository instructions and docs;
- CI and verification scripts;
- API/schema artifacts;
- generated and excluded paths;
- local Git state;
- a Python package suitable for structural indexing.

Assert all stable response sections, evidence links, confidence, assumptions, unknowns, Git summary, verification candidates, contract artifacts, and Code Atlas results.

### 7.2 Write failing determinism tests

Run identical inspection twice and compare a canonical substantive payload. Exclude or normalize declared temporal fields. Random filesystem enumeration order MUST not change results.

### 7.3 Write failing evidence-reference tests

Every finding, recommendation, relationship, and handoff evidence reference MUST resolve. Duplicate IDs and dangling references must fail internal validation before serialization.

### 7.4 Write failing compaction tests

Cover:

- exact evidence capacity does not set truncation;
- one item over capacity sets truncation;
- serialized output never exceeds the configured maximum;
- compaction retains the stable envelope;
- material findings retain referenced evidence;
- unknowns, confidence, and truncation reasons remain present;
- minimum-contract overflow returns a structural error.

### 7.5 Implement service and budgeter

The service owns orchestration, stable IDs, aggregation, deterministic ordering, response validation, confidence synthesis, unknowns, and recommendations. Scanners and detectors return domain records, not public envelopes.

### 7.6 Verify

Run:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-o cache_dir=C:\Projects\.kis-mcp\pytest-cache'
uv run --offline --no-sync python -m pytest `
  tests/discover/test_budgeting.py `
  tests/discover/test_inspect_project.py `
  tests/discover/test_inspect_project_determinism.py `
  tests/discover/test_inspect_project_compaction.py -q
```

Update `source-harvest.md` with dev-intel inspection/compaction parity tests.

**Checkpoint:** The complete internal workflow produces one stable bounded public response before MCP registration.

---

## Task 8: Register inspect_project and enforce plane boundaries

**Requirements:** REQ-010, REQ-011, REQ-012

**Files:**

- Create: `src/kis_mcp/discover/tools.py`
- Modify: `src/kis_mcp/server.py`
- Modify: `tests/test_architecture_boundaries.py`
- Modify: `tests/test_public_contracts.py`
- Create: `tests/discover/test_tool_registration.py`
- Create: `tests/discover/test_architecture.py`
- Create: `tests/discover/test_independent_install.py`

### 8.1 Write failing thin-binder tests

Assert:

- `register_discover_tools(...)` registers exactly `inspect_project`;
- the handler delegates to `InspectProjectService`;
- tool inputs match `InspectProjectRequest`;
- structural errors are normalized without HR codes;
- existing KIS and Desktop Commander tool schemas are unchanged;
- the binder contains no scanner, Git, AST, or budgeting decisions.

### 8.2 Write failing architecture tests

Use AST import inspection to prohibit:

- Work adapter, middleware, policy, quarantine, and provider-lifecycle imports from Discover;
- `subprocess` outside `git_reader.py`;
- network modules;
- FastMCP/backend imports outside `tools.py`;
- donor package imports;
- direct filesystem traversal outside `read_authority.py` and `scanner.py`.

### 8.3 Implement registration seam

Construct Discover settings and service from `RuntimeConfig` outside provider-specific Work logic. Add one call in `build_server()`.

Coordinate the final `server.py` diff with `006-provider-state-atomicity` before closeout.

### 8.4 Add independent-install test

Install or import kis-mcp from its own checkout with donor repository names excluded from `PYTHONPATH`. Assert Discover imports and focused tests pass without sibling lookups.

### 8.5 Verify

Run:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-o cache_dir=C:\Projects\.kis-mcp\pytest-cache'
uv run --offline --no-sync python -m pytest `
  tests/discover/test_tool_registration.py `
  tests/discover/test_architecture.py `
  tests/discover/test_independent_install.py `
  tests/test_architecture_boundaries.py `
  tests/test_public_contracts.py -q
```

**Checkpoint:** One public Discover workflow is integrated without changing Work behavior or dependency direction.

---

## Task 9: Current-state documentation, review, verification, and branch closeout

**Requirements:** REQ-013 and all acceptance criteria

**Files:**

- Modify only when proven: `SPEC.md`
- Modify only when proven: `README.md`
- Modify only when proven: `docs/OPERATIONS.md`
- Modify: `docs/development/discover-foundation/source-harvest.md`
- Create or update: `docs/development/discover-foundation/verification.md`
- Modify: `.work/changes/005-discover-foundation/tasks.md`
- Modify: `.work/changes/005-discover-foundation/closeout.md`

### 9.1 Update current implementation claims

State exactly what is implemented:

- local deterministic `inspect_project`;
- configured limits and exclusions;
- repository and verification discovery;
- local Git summary;
- bounded pure Python Code Atlas if implemented;
- no remote evidence, semantic provider, Govern evaluation, or Work execution.

Do not copy the full target roadmap into current-state documents. Link to the product specification.

### 9.2 Review the complete diff

Review against:

- `AGENTS.md` authority and three-rule boundary;
- change specification and scope;
- full Discover product specification;
- source-harvest register;
- donor parity tests;
- public schema and settings;
- parallel `004` and `006` scope ownership;
- security, secret, path, link, Git, output, and execution boundaries;
- documentation target/current distinction.

Record findings and fixes in `verification.md` or closeout.

### 9.3 Run change governance

```powershell
pwsh -NoProfile -File .\scripts\change-workflow.ps1 validate
pwsh -NoProfile -File .\scripts\change-workflow.ps1 check
```

### 9.4 Run focused Discover suite

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'C:\Projects\.kis-mcp\python-env'
$env:UV_CACHE_DIR = 'C:\Projects\.kis-mcp\uv-cache'
$env:PYTHONPYCACHEPREFIX = 'C:\Projects\.kis-mcp\python-cache'
$env:PYTEST_ADDOPTS = '-o cache_dir=C:\Projects\.kis-mcp\pytest-cache'
uv run --offline --no-sync python -m pytest tests/discover -q
```

### 9.5 Run complete repository verification

```powershell
pwsh -NoProfile -File .\scripts\verify.ps1
```

### 9.6 Inspect final Git state

- `git status --short` contains only declared files before staging;
- `git diff --check` passes;
- staged diff contains no donor dependency, generated state, secret, unrelated Work change, or line-ending-only churn;
- source-harvest entries reference passing tests;
- all tasks and closeout evidence are current.

### 9.7 Commit and publish for review

Create bounded commits by completed task where practical. Push `change/005-discover-foundation` without force. Create a draft pull request. Do not merge before review.

**Done when:** all acceptance criteria are evidenced on the final commit, the PR is open for review, and future D2–D8 work remains explicit rather than implied complete.
