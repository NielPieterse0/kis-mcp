# NIM Sub-agent Models Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Measure experimental NVIDIA NIM reviewer candidates safely before production promotion.

**Architecture:** Extend the existing NVIDIA settings/client and code-review workflow with a separate benchmark allowlist and one discoverable external/read-only benchmark operation. Keep the existing production reviewer aliases untouched. Reuse the current NVIDIA provider instance and credential boundary; do not add another provider or local-network path.

**Tech Stack:** Python 3.13 locked project environment, FastMCP, NVIDIA OpenAI-compatible chat completions, pytest, repository change-governance workflow.

## Global constraints

- Stay inside `scope.json` and do not touch parallel changes 093/094.
- Do not alter HR-001 / HR-002 / HR-003 or credentials.
- Do not expose experimental models as production reviewer aliases before live smoke evidence.
- Keep benchmark output bounded and redacted.

### Task 1: Benchmark contract

- [x] Add strict benchmark configuration and candidate allowlist.
- [x] Add portable bounded NVIDIA benchmark request handling.
- [x] Add fixed correctness/security smoke scoring and latency suitability gate.
- [x] Register benchmark as discoverable external + read-only, not direct.

### Task 2: Deterministic verification

- [x] Add provider payload/configuration tests.
- [x] Add reviewer validation, scoring, failure-redaction, and repetition tests.
- [x] Verify composed capability exposure.
- [x] Run focused tests and scope check.
- [x] Run canonical repository verification.

### Task 3: Live benchmark and promotion decision

- [x] Land the benchmark seam without changing production aliases.
- [x] Commission the benchmark operation through a live KIS runtime without interrupting unrelated parallel work.
- [x] Run identical smoke probes against baseline and candidate aliases, with repeated validation for initially viable experimental candidates.
- [x] Reject candidates that fail the review-quality, reliability, or latency bar.
- [x] Close with no production-profile change because combined repeated evidence did not establish a robust experimental promotion candidate.

### Task 4: Closeout

- [x] Record verification/review/live benchmark evidence.
- [x] Restart `kis-op` from current `main` and confirm the merged local 095 worktree/branch are absent.
- [x] Prepare final reconciled closeout metadata for exact publication to remote `main`.
