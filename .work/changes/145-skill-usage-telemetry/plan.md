# Skill Usage Telemetry Implementation Plan

**Goal:** Deliver bounded version-attributed operational telemetry for the shared Skills catalogue without widening KIS authority.

**Architecture:** Extend `RuntimeObservability` for bounded live evidence, add a stdlib SQLite store under KIS generated state, instrument the existing Skills service, and expose explicit outcome/report operations through progressive capability dispatch.

**Tech stack:** Python 3, FastMCP, `contextvars`, stdlib `sqlite3`, pytest, existing KIS capability composition and Control Center.

## Global constraints

- No prompts, skill/file contents, raw searches, credentials, secrets, or arbitrary tool arguments.
- Loads remain distinct from application/completion.
- Use package hash rather than resource-file hash for version attribution.
- Missing operational metrics remain null/not observable.
- Preserve HR-001, HR-002, HR-003 and the bounded direct profile.

### Task 1: Correlation and live evidence

- Add request-scoped correlation and bounded `SkillActivityRecord` evidence.
- Prove correlation cleanup and payload-free bounded retention.

### Task 2: Durable store

- Add bounded SQLite event persistence and deterministic pruning.
- Prove recreation, grouping, privacy schema, and exact-load attribution.

### Task 3: Skills instrumentation

- Instrument discovery/load/read/evaluate/create/improve success and error evidence.
- Add explicit attributed outcomes and grouped reporting.

### Task 4: Capability/commissioning truth

- Keep Skills operations discoverable long-tail, not direct-profile tools.
- Classify telemetry report as read-only and outcome attribution as local change.
- Exercise a real shared skill through capability dispatch and recover mutation smoke state through quarantine.

### Task 5: Documentation and closeout

- Reconcile current implementation and operator semantics in canonical documentation.
- Run scope check, focused tests, specialist reviews, and exact-head GitHub Actions verification.
- Land through registered KIS GitHub operations and reconcile source issue/work-management evidence.
