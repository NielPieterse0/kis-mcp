# Change: Merge Readiness Unmanaged Result

- **Change ID**: `272-merge-readiness-unmanaged-result`
- **Risk Profile**: lean

## Outcome

Return typed unmanaged/not_found merge-readiness results for source issues without a Work record while preserving managed exact-head readiness behavior.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- An absent Work `record_id` returns a typed `status=unmanaged`, `managed=false`, `error_code=not_found` result instead of throwing.
- Managed readiness remains exact-head gated and returns explicit `ready`/`blocked` managed status.
- Malformed managed records that do include an identity remain validation errors rather than being silently treated as unmanaged.

## Implementation and verification

- Implementation notes: added an unmanaged branch at the merge-readiness tool boundary and explicit managed status fields on normal readiness results.
- Focused checks: `42 passed` across project-management, runtime surface, promotion-runtime, and merge-queue caller tests using the canonical managed uv environment.
- Full verification: canonical `scripts/verify.ps1` passed, including the full pytest suite, configuration, managed interpreter/dependencies, Python syntax, change governance, and exact policy verification.
- Review findings: code-quality review found no defects. API-contract review confirmed the additive response-shape change and requested caller/full-suite verification; both are covered, including a regression proving partial managed records remain validation errors.
- Residual risk: callers that ignored tool errors and only tested `ready` still fail closed (`ready=false`) for unmanaged sources; callers can now distinguish the unmanaged case via `status`/`managed`/`error_code`.
- Closeout state: implementation and verification complete; publication/landing pending.
