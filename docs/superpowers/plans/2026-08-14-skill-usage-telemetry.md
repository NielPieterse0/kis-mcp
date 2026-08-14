# Skill Usage Telemetry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add privacy-preserving, version-attributed skill usage telemetry to KIS and expose bounded evidence for downstream effectiveness evaluation.

**Architecture:** Extend existing `RuntimeObservability` for live evidence and add a bounded SQLite-backed `SkillTelemetryStore` under KIS external state. Skills operations record observed events; a separate explicit outcome tool records reported application/completion only when tied to a prior observed load.

**Tech Stack:** Python 3, FastMCP middleware/tools, `contextvars`, stdlib `sqlite3`, pytest, existing KIS Control Center and verification scripts.

## Global Constraints

- Do not record prompts, skill/file contents, credentials, secrets, raw search queries, or arbitrary tool arguments.
- Loads are not applications; application/completion evidence is explicit and labeled reported.
- Every skill-specific longitudinal record includes immutable snapshot/hash attribution where available.
- Missing token/tool/retry metrics remain null/not observable.
- Preserve HR-001, HR-002, HR-003 and existing Skills authority boundaries.
- Durable detail is capped at 20,000 redacted events; report groups are capped at 100 rows.

---

### Task 1: Boundary correlation and live skill activity

**Files:**
- Modify: `src/kis_mcp/runtime_observability.py`
- Modify: `src/kis_mcp/middleware.py`
- Modify: `src/kis_mcp/control_center/snapshot.py`
- Test: `tests/test_runtime_observability.py`
- Test: `tests/test_middleware.py`

**Interfaces:**
- Produces `current_request_id() -> str | None` and bounded `SkillActivityRecord` evidence.
- `BoundaryObservabilityMiddleware` reserves one request ID before dispatch and clears it afterwards.

- [ ] **Step 1: Add failing live-observability tests**

Assert that skill activity retains only structured identity/metrics, is newest-first and bounded, and that request correlation is visible only during a boundary call.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `python -m pytest tests/test_runtime_observability.py tests/test_middleware.py -q`
Expected: failures for missing skill activity/correlation APIs.

- [ ] **Step 3: Implement minimal live primitives**

Add a request-ID `ContextVar`, request reservation/set/reset helpers, `SkillActivityRecord`, `record_skill_activity(...)`, and `recent_skill_activity` in the snapshot. Update boundary middleware to reserve/set/reset exactly once per call.

- [ ] **Step 4: Keep Control Center bounded**

Include `recent_skill_activity[:max_recent_calls]` in `_bounded_observability()`; do not add payload fields or a second observability registry.

- [ ] **Step 5: Run focused tests and commit**

Run the two focused files, then `git diff --check`.
Commit: `feat: correlate live skill activity`

### Task 2: Durable redacted telemetry store

**Files:**
- Create: `src/kis_mcp/skills/telemetry.py`
- Test: `tests/skills/test_telemetry.py`
- Modify: `tests/skills/test_architecture.py`

**Interfaces:**
- `SkillTelemetryStore(path: Path, max_events: int = 20000, max_report_rows: int = 100)`
- `record(event: SkillTelemetryEvent) -> None`
- `has_observed_load(skill_id, activation_id, snapshot_id, content_sha256, project_id) -> bool`
- `report(skill_id=None, project_id=None, content_sha256=None) -> SkillTelemetryReport`

- [ ] **Step 1: Add failing persistence/retention/privacy tests**

Cover service recreation, deterministic oldest-row pruning, nullable metrics, observed-load lookup, grouped counts, and absence of sensitive payload columns.

- [ ] **Step 2: Run telemetry tests and confirm RED**

Run: `python -m pytest tests/skills/test_telemetry.py -q`
Expected: import/module failure before production code exists.

- [ ] **Step 3: Implement SQLite store**

Create one table of redacted events with indexes on skill/hash/project/activation. Use a bounded SQLite timeout and transaction; prune oldest rows after each insert. Store only the design contract fields.

- [ ] **Step 4: Implement grouped report**

Return separate counters for discovery/load/resource/evaluate/mutation/applied/completed/failed plus duration and optional metric sample counts. Do not calculate a combined score.

- [ ] **Step 5: Run tests, architecture check, and commit**

Run `python -m pytest tests/skills/test_telemetry.py tests/skills/test_architecture.py -q`.
Commit: `feat: persist bounded skill telemetry`

### Task 3: Instrument Skills operations and expose reporting

**Files:**
- Modify: `src/kis_mcp/skills/models.py`
- Modify: `src/kis_mcp/skills/service.py`
- Modify: `src/kis_mcp/skills/tools.py`
- Modify: `src/kis_mcp/skills/platform.py`
- Modify: `src/kis_mcp/gateway/composition.py`
- Modify: `tests/skills/test_service.py`
- Modify: `tests/skills/test_tools.py`

**Interfaces:**
- Existing operations record observed events after success and error-class events on failure.
- `record_skill_outcome(...)` validates a matching prior observed load before writing reported evidence.
- `skill_telemetry_report(...)` returns bounded grouped rows with explicit observable sample counts.

- [ ] **Step 1: Add failing service/tool tests**

Prove immutable hash/snapshot attribution for load/read/evaluate, no raw search query retention, optional activation/project correlation, rejection of unattributed outcomes, and separate reported completion counts.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `python -m pytest tests/skills/test_service.py tests/skills/test_tools.py -q`.
Expected: failures for missing telemetry injection and public operations.

- [ ] **Step 3: Inject the store and instrument operations**

Construct the store from `Path(runtime.state_root) / "telemetry" / "skills.sqlite3"` through the platform entrypoint. Use `time.perf_counter_ns()` for duration and `current_request_id()` for boundary correlation.

- [ ] **Step 4: Add explicit attribution/report tools**

Add `record_skill_outcome` and `skill_telemetry_report`; extend `load_skill` and `read_skill_file` only with optional `activation_id`/`project_id`. Preserve corrective `SKILLS_*` errors.

- [ ] **Step 5: Run Skills tests and commit**

Run `python -m pytest tests/skills -q` and `git diff --check`.
Commit: `feat: instrument skills usage telemetry`

### Task 4: Documentation and repository verification

**Files:**
- Modify: `docs/SKILLS-MODULE-PRODUCT-SPEC.md`
- Modify: `docs/OPERATIONS.md`
- Test/update any exact tool-surface assertions selected by verification.

- [ ] **Step 1: Document operational/query semantics**

Explain observed versus reported evidence, correlation fields, retention, privacy exclusions, report interpretation, and the downstream `chatgpt-skill` effectiveness boundary.

- [ ] **Step 2: Run policy and surface checks**

Run `node scripts/check-tool-surface.mjs`, `node scripts/check-tool-surface.mjs --drift`, and any selected detail checks.

- [ ] **Step 3: Run repository verification**

Run `pwsh -NoProfile -File scripts/verify.ps1`.

- [ ] **Step 4: Review exact change and fix findings**

Run KIS change inspection plus architecture/test-quality/safety-security review against the exact working tree/commit.

- [ ] **Step 5: Commit closeout documentation**

Commit: `docs: document skill telemetry operations`
