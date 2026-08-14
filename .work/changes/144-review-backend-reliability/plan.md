# Review Backend Reliability Implementation Plan

**Goal:** Make advisory review failures diagnosable and retry-safe without weakening review gates.

**Architecture:** Keep retry classification at the reviewer boundary. Provider/tool adapters emit typed failures; the reviewer records redacted attempts and retries only allowlisted transient classes; change execution accepts only a structured completed reviewer result as success. Exhausted automation returns an explicit exact-diff manual fallback state.

**Tech Stack:** Python, pytest, NVIDIA NIM HTTP client, pinned Codex CLI wrapper, FastMCP workflow contracts.

## Global constraints

- Stay inside `scope.json`.
- Add regression tests before behavior changes.
- Keep attempt budget in checked-in JSON settings.
- Never treat failed, unavailable, disabled, invalid, or unstructured reviewer output as success.
- Do not persist prompt/provider secrets in diagnostics.

### Task 1: Typed backend boundaries

- [x] Force Codex subprocess text I/O to UTF-8 and type encoding failures.
- [x] Separate NVIDIA timeout, transport, retryable HTTP, terminal HTTP, and malformed response failures.

### Task 2: Bounded retry and fallback

- [x] Add strict `max_backend_attempts` settings with default/configured value 2.
- [x] Retry only classified transient failures.
- [x] Record safe per-attempt diagnostics and explicit exact-diff manual fallback after exhaustion.

### Task 3: Workflow truthfulness

- [x] Map only `status=completed` reviewer payloads to completed review steps.
- [x] Preserve failure payload/diagnostics while making orchestration incomplete.
- [x] Cover NVIDIA retry recovery, Codex timeout recovery, dual failure, and non-success reviewer payloads.

### Task 4: Verify and integrate

- [x] Focused and component suites pass on the reconciled branch head.
- [x] Scope and diff checks pass.
- [x] Required independent reviews were attempted and are explicitly unavailable/failed; manual exact-diff fallback evidence is recorded without claiming automated review success.
- [ ] Exact-head PR CI completes on the published head.
- [ ] Merge, issue/board completion reconciliation, and cleanup complete.
