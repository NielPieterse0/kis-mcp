# Closeout: DB/Docker Commissioning Hardening

## Implemented scope

- Preserved DBHub `v1.2.0` / `1bed0b8bd8e6e3e625c83f571d12f748f2d7a0b0` and Docker Hub `ad806e2cab0489a296aec0f32f3d3eea807d65c2` exact pins.
- Kept DBHub read-only and Docker Hub credential-free/public; no PAT, mutation, Docker Engine, or arbitrary CLI authority was added.
- Removed only Docker Hub upstream `search` from the KIS public surface because the pinned provider rejects Docker Hub's current top-level `search_after` response field.
- Preserved the six live-verified Docker Hub repository/tag read operations.
- Changed commissioning stderr replay from terminating `Write-Error` to diagnostic stderr so a successful provider child exit remains successful.
- Reconciled `SPEC.md`, `docs/OPERATIONS.md`, focused tests, and historical change evidence with commissioned runtime truth.

## Validation evidence

- TDD red: focused provider tests failed exactly because Docker `search` was still exposed and commissioning used terminating `Write-Error`.
- TDD green: `tests/providers/test_dbhub_dockerhub_integration.py` passed `16/16`.
- One-shot commissioning: `scripts/commission-db-docker-providers.ps1` exited `0`; DBHub discovered two College tools and Docker Hub discovered exactly six public tools.
- Live Docker Hub reads: `checkRepository`, `checkRepositoryTag`, `getRepositoryInfo`, `getRepositoryTag`, `listRepositoriesByNamespace`, and `listRepositoryTags` all succeeded against public `library/alpine` evidence.
- DBHub live evidence: College `search_objects` and read-only `execute_sql` succeeded during commissioning, including a bounded SELECT against `runs`.
- Fresh post-merge `kis-op` runtime started from source revision `1e0e23f0061154c5ead057891c5ae81caadda203`; provider status reported DBHub and Docker Hub mounted/ready, Docker Hub exposed exactly six public operations with `search` absent, live `library/alpine` lookup succeeded, and `SELECT COUNT(*) FROM runs` returned `29`.
- Diff scope check: `scripts/change-workflow.ps1 check` passed with all changed paths inside declared change ownership.
- Canonical repository verification: `scripts/verify.ps1` passed; pytest reached 100% with two expected skips, 277 Python files syntax-checked, and configuration/dependencies/governance/HR-001/HR-002/HR-003 checks green.
## Review

- Codex CLI reviewer attempt failed at the configured backend boundary with `AGENT_BACKEND_FAILED:CodexCliError`; it returned no findings and is not counted as a completed review.
- NVIDIA NIM reviewer retry also failed at the configured backend boundary with `AGENT_BACKEND_FAILED:NvidiaNimError`; it returned no findings and is not counted as a completed review.
- The final bounded diff was therefore inspected directly and remains limited to the approved provider surface, commissioning behavior, tests, documentation, and change records; no third-party provider bytes or policy rules were changed.

## Git and merge

- Branch: `change/111-db-docker-commissioning-hardening`
- Worktree: `.work/worktrees/111-db-docker-commissioning-hardening`
- Verified local implementation commit: `1e0e23f0061154c5ead057891c5ae81caadda203`.
- Exact remote PR head: `11b8d180e99b14fad4c80995a3bdf527997bb2c8`; all 10 declared remote paths were previously verified blob-identical to the local implementation commit.
- Pull request #136 merged at the exact authorized head; GitHub `main` advanced to `34d6b3c49b801800bc45c59183650b4aebad40cc`.
- Local `main` is tree-equivalent at `1e0e23f0061154c5ead057891c5ae81caadda203`; the lifecycle reconciliation is published separately against the current GitHub default head rather than rewriting remote history.
- Remote review branch remains recoverably present at `11b8d180e99b14fad4c80995a3bdf527997bb2c8` until the lifecycle reconciliation is merged; exact-head branch deletion and governed local cleanup are its postconditions.

## Residual items

- Docker Hub upstream `search` remains hidden until an approved provider update or compatibility fix accepts the current `search_after` result shape.
- The pinned Docker Hub production dependency audit previously recorded 13 advisories, 0 critical and 9 high; exposure remains constrained to single-client stdio plus six public read operations.
- Docker Engine/runtime control is intentionally outside change 111.