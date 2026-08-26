# Lossless Legacy Transfer Ledger Implementation Plan

> **For agentic workers:** Execute this plan task-by-task and keep the declared scope current.

**Goal:** Produce deterministic requirement-level traceability proving lossless transfer of all #497 legacy obligations into #475/#488-#496, with MCP 2026 re-baselining and retained deferred triggers explicit.

**Architecture:** Add historical audit evidence only. `ledger.json` is deterministic machine-readable traceability; `audit.md` explains methodology/findings. Neither becomes current product authority.

**Tech Stack:** KIS Work/GitHub reads, local MCP 2026 Markdown corpus, JSON, locked repository Python, governed change/verification workflow.

## Global constraints

- Stay inside `scope.json`; do not modify runtime/source/product authority.
- Preserve source issue intent but do not revive withdrawn/unapproved or obsolete protocol prescriptions.
- Treat MCP 2026-07-28 specification/schema as normative for MCP-facing rows.
- Require current evidence for `implemented_verify`, objective triggers for `future_triggered`, and explicit rationale for `superseded_2026`/`not_required`.
- Do not alter, stop, restart, or commission `kis-op` as part of this documentation-only change.

---

### Task 1: Build and verify traceability

**Files:**
- Add: `docs/development/audits/2026-08-26-lossless-legacy-transfer/ledger.json`
- Add: `docs/development/audits/2026-08-26-lossless-legacy-transfer/audit.md`

- [x] Prove exact 84 legacy + five retained Deferred source coverage.
- [x] Normalize material requirements and controlled dispositions.
- [x] Re-baseline MCP-facing rows and record #475 current evidence.
- [x] Detect duplicate ownership and withdrawn/obsolete authority conflicts.
- [ ] Run governed scope, focused data/docs checks, full repository verification and independent review.
- [ ] Publish exact head, pass canonical CI/merge-readiness, merge, reconcile #497, and clean safely.
