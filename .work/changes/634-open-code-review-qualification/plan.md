# Open Code Review Qualification Plan

**Outcome:** Produce a reproducible go/no-go qualification for issue #534 without adding OCR to KIS.

**Sources:** #534, `AGENTS.md`, current KIS reviewer evidence, pinned OCR package metadata, and observed runtime controls.

**Constraints:** isolated read-only execution; exact package pin; no `ocr init`; no GitHub/LLM credentials unless explicitly required by an approved adapter; no product/settings/policy changes; no fabricated benchmark metrics.

## Tasks

1. **Establish bounded change and provenance**
   - Confirm clean verified `main`, claim #534, allocate the isolated change, and project complexity/risk classification.
   - Record exact OCR package/platform package versions and integrity from the local npm cache.

2. **Implement reproducible qualification decision**
   - Add `scripts/qualification/open-code-review/qualify.py` and focused tests.
   - Require exact pinning, non-empty corpus, and fail-closed handling when OCR cannot execute.

3. **Exercise the hermetic runtime gate**
   - Install only from the approved local npm cache into disposable state.
   - Probe the native binary without credentials or repository mutation.
   - Attempt only an equally bounded fallback that does not widen network or policy authority.

4. **Benchmark only if preflight succeeds**
   - Run the representative corpus through KIS, OCR advisory, and combined candidate review.
   - Measure validated findings, false/unsupported findings, misses, duration/cost, triage cost, large-change coverage, and discourse-vs-independent-review value.
   - If preflight fails, mark these metrics `not_measurable`; do not synthesize review output.

5. **Verify and close**
   - Record evidence and decision, run focused checks and governance scope checks, obtain required independent reviews, publish/verify/merge, reconcile Work, and clean generated state/worktree safely.
