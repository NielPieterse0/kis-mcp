# Tasks: Discover Foundation and inspect_project

## Task 1 — Product specification and roadmap

- [x] Adapt the approved Discover module product specification to `kis-mcp`.
- [x] Preserve the complete D0–D8 roadmap.
- [x] Establish sdk-tool as the primary donor.
- [x] Record dev-intel-tool and mcp-tool parity sources.
- [x] Link the detailed specification from `docs/PLATFORM-CONCEPT.md`.
- [x] Validate documentation links, target/current separation, and baseline verification.

## Task 2 — Contracts, schemas, and settings

- [x] Write failing immutable-contract tests.
- [x] Implement versioned Discover contracts and structural errors.
- [x] Write failing strict-settings tests.
- [x] Add JSON-backed Discover limits and exclusions.
- [x] Add portable Discover schemas and drift tests.
- [x] Run focused contract/configuration verification.

## Task 3 — Identity, ReadAuthority, and scanner

- [x] Write failing path, identity, link, hard-link, and read-revalidation tests.
- [x] Implement provider-neutral `ReadAuthority`.
- [x] Write failing traversal-budget and deterministic-order tests.
- [x] Implement bounded streaming scanner.
- [x] Run focused scanner and hardening verification.

## Task 4 — Repository and verification discovery

- [x] Write detector fixture matrix.
- [x] Port repository, manifest, framework, instruction, CI, and contract detectors.
- [x] Write workflow-discovery parity tests.
- [x] Port non-executable verification discovery.
- [x] Run focused detector and verification tests.

## Task 5 — Pure Python structural Code Atlas

- [x] Write non-execution and sanitization tests.
- [x] Write modules, symbols, imports, inheritance, calls, cycles, and syntax tests.
- [x] Write node, file, record, and duration limit tests.
- [x] Port bounded Python project index.
- [x] Run focused Python index verification.

## Task 6 — Local Git evidence

- [x] Write normal and linked-worktree metadata tests.
- [x] Write hostile Git configuration tests.
- [x] Implement fixed-template bounded Git reader.
- [x] Verify remote redaction, timeouts, and output truncation.
- [x] Run focused Git verification.

## Task 7 — inspect_project service and budgeting

- [x] Write complete fixture-response tests.
- [x] Write deterministic-output tests.
- [x] Write evidence-reference integrity tests.
- [x] Write output-compaction and exact-capacity tests.
- [x] Implement service orchestration and result budgeter.
- [x] Run focused service verification.

## Task 8 — MCP registration and architecture

- [x] Write thin-binder and tool-catalogue tests.
- [x] Write plane dependency and prohibited-import tests.
- [x] Implement `register_discover_tools(...)`.
- [x] Integrate one call into `build_server()` with current composition-root coordination.
- [x] Add donor-independent installation/import test.
- [x] Run focused registration and architecture verification.

## Task 9 — Documentation, review, verification, and PR

- [ ] Update current implementation claims only after verification.
- [ ] Complete source-harvest parity traceability.
- [ ] Review the final diff against authority, scope, donors, and security boundaries.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 validate`.
- [ ] Run `pwsh -NoProfile -File scripts/change-workflow.ps1 check`.
- [ ] Run the focused Discover suite through the locked `C:\Projects\.kis-mcp\python-env` environment.
- [ ] Run `pwsh -File scripts/verify.ps1`.
- [ ] Run Git whitespace and declared-scope checks.
- [ ] Commit and push without force.
- [ ] Create a draft pull request for review.
- [ ] Do not merge until reviewed.
