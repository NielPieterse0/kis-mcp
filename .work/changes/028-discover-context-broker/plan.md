# Discover Context Broker Implementation Plan

> Execute task-by-task in this isolated worktree. Use test-driven development, review each task against `spec.md`, and run the locked repository verification before publication.

**Goal:** Implement deterministic `get_code_context` contracts and a bounded local Context Broker without modifying public registration or shared runtime composition.

**Architecture:** Reuse `ReadAuthority`, `RepositoryScanner`, `PythonProjectIndexer`, and `GitReader` to produce bounded metadata. Rank files, modules, symbols, and relationships in a pure ranking module, then read excerpts only for retained files and compact the immutable response under the explicit serialized-character budget.

**Tech Stack:** Python 3.11 dataclasses and standard library, JSON Schema draft 2020-12, pytest, existing Discover scanner/read/Git/Python adapters, repository PowerShell verification.

## Global constraints

- No direct filesystem traversal outside the existing scanner.
- No direct subprocess import outside `git_reader.py`.
- No network, target-code imports, target-code execution, mutation, tests/builds/package managers, arbitrary commands, credentials, endpoints, or persistent index state.
- Use only paths declared in `scope.json`.
- Serialize full `verify.ps1` runs because the editable Python environment is shared.

### Task 1: Request, result, and schema contracts

**Files:** `context_contracts.py`, request/response schemas, `test_context_contracts.py`.

- [ ] Add failing tests for required project/task/budget fields, positive bounds, deterministic JSON, fingerprint validation, omissions, provenance, and schema validity.
- [ ] Implement immutable request, budget, file, module, symbol, relationship, unknown, omission, and response records.
- [ ] Implement exact JSON identity and strict draft-2020-12 schemas.
- [ ] Run focused contract/schema tests and commit.

### Task 2: Deterministic task-term and relevance ranking

**Files:** `context_ranking.py`, `test_context_determinism.py`.

- [ ] Add failing fixtures for snake-case, kebab-case, dotted symbols, path terms, category intent, test intent, contract intent, instruction intent, and stable tie-breaking.
- [ ] Implement deterministic tokenization, stop-word filtering, category boosts, path/module/symbol scoring, relationship scoring, and stable sorting.
- [ ] Prove identical inputs produce identical substantive ranking and fingerprints.
- [ ] Run focused ranking tests and commit.

### Task 3: Bounded broker composition

**Files:** `context_broker.py`, `test_context_broker.py`.

- [ ] Add failing repository fixtures for directly named files/symbols, connected imports/calls/inheritance, instructions, tests, contracts, unreadable/unsupported evidence, Git degradation, and explicit omissions.
- [ ] Compose scanner, Python index, and Git summary using existing authority/settings.
- [ ] Rank metadata before reading content.
- [ ] Read only retained paths and extract bounded line-aware excerpts around matched terms or selected symbols.
- [ ] Select connected relationships and normalize provider/provenance evidence.
- [ ] Compact deterministically under `max_chars`, preserving the minimum valid response and reporting all omissions.
- [ ] Run focused broker, determinism, schema, and architecture tests and commit.

### Task 4: Review, verification, publication, and cleanup

- [ ] Run `change-workflow.ps1 check`.
- [ ] Run `git diff --check`.
- [ ] Review specification compliance, ranking quality, output-budget correctness, schema references, safe-read boundaries, failure handling, determinism, and scope.
- [ ] Run the full Discover test suite.
- [ ] Run the full locked `scripts/verify.ps1` suite.
- [ ] Complete tasks and closeout, push, open a PR, verify exact-head mergeability, merge, close governance, and clean local and remote branches/worktrees.
