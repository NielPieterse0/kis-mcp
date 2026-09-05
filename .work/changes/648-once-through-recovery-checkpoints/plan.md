# Once Through Recovery Checkpoints Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Add generic reversible once-through checkpoints with retained evidence revalidation, safe abort/exit, and explicit irreversible-boundary handling without changing the normal forward path.

**Architecture:** Describe the smallest complete approach.

**Tech Stack:** List only applicable tools and runtimes.

## Global constraints

- Stay inside `scope.json`.
- Add tests before behavior changes.
- Do not alter unrelated authority or policy.

---

### Task 1: Define the bounded change

**Files:**
- Modify:
- Test:

- [ ] Write the failing test or verification.
- [ ] Confirm the expected failure.
- [ ] Implement the smallest complete change.
- [ ] Confirm focused and repository verification pass.
