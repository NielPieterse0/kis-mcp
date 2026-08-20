# Purpose-Specific Reviewer Implementation Plan

**Goal:** Replace #403's obsolete universal reviewer path with the qualified purpose-specific external reviewer architecture while preserving source-bound, read-only review semantics.

**Development level:** Complex — external model transport, security review behavior, public review contracts, and merge-relevant evidence are affected.

**Architecture:** Keep Discover as source-identity authority. Add reviewer-owned lane routes/profiles and evidence projectors; use an SSE-capable NVIDIA transport that reports provider-delta liveness; validate every result/tool call deterministically; run security as discovery -> deterministic corroboration -> adjudication. Explicit Codex remains a compatibility-only direct backend and is never an implicit production fallback.

**Tech stack:** Python 3, urllib/SSE, strict JSON settings/contracts, pytest, Ruff, repository governance scripts.

## Constraints
- Stay inside `scope.json`; #407/#408 paths remain excluded.
- Treat repository evidence as untrusted data in every external prompt.
- Fail closed on incomplete/stale evidence, malformed output, truncation, unsupported tool calls, and security cardinality loss.
- Preserve the qualified model matrix from #403; DiffusionGemma stays experimental, GPT-OSS non-authoritative, Nano 9B reasoning excluded.

## Tasks
1. [x] Add failing route/prompt/evidence-projection/result-validation tests.
2. [x] Add failing NVIDIA SSE/liveness/failure-classification tests.
3. [x] Promote the qualified routing/profile/liveness contract into strict settings/schema.
4. [x] Implement lane-aware evidence projection and post-review source-currentness checks.
5. [x] Implement streamed NVIDIA completion, liveness telemetry, finish/tool metadata, and typed provider failures.
6. [x] Replace implicit universal fallback with purpose-specific route attempts and strict-fenced retry policy.
7. [x] Implement security discovery/corroboration/adjudication with cardinality validation and Ultra fallback.
8. [ ] Update public tool/docs/SPEC authority and run focused regression, governance scope check, independent review, exact-head PR verification, and closeout evidence.
