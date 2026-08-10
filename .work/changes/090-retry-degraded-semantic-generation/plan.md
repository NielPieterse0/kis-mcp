# Retry Degraded Semantic Generation Plan

**Goal:** Let Discover recover automatically after transient Serena failure without changing deterministic fallback behavior.

**Design:** Reuse the existing persisted-generation path. After loading semantic metadata from a matching generation, return it only when it is reusable. A configured provider plus degraded semantic status makes the generation stale-for-semantic purposes and falls through to the existing refresh path.

## Task 1 — RED regression

- Add a fail-once semantic provider with a stable provider fingerprint and call counter.
- First `get()` must persist degraded semantic fallback.
- Second `get()` must currently demonstrate the defect by reusing that degraded generation instead of calling the recovered provider.

## Task 2 — Minimal fix

- Change only persisted-generation reuse logic in `ProjectIntelligenceService.get()`.
- Keep ready-provider and null-provider reuse unchanged.
- Reuse the existing refresh/persistence/supersession path; add no new cache or schema.

## Task 3 — Verification and commissioning

- Run focused Discover persistence tests and governed scope check.
- Run canonical `scripts\verify.ps1`.
- Integrate into clean `main`, restart `kis-dev`, and rerun the exact previously failing fresh-runtime Discover scenario.
- Re-run provider smoke and final repository/runtime audit.
- Publish exact verified `main` and governed-clean 090.
