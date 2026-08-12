# Closeout: NIM Sub-agent Models

## Implemented scope

- Added a separate allowlisted NVIDIA benchmark catalog; production `nano`, `super`, and `ultra` profiles remain unchanged.
- Added a portable bounded benchmark request path through the existing approved NVIDIA external connector.
- Added fixed correctness/security capability scoring, 1-3 run repetition, and a 30-second suitability latency gate.
- Kept the benchmark out of the direct tool profile; capability discovery classifies it as eligible `external` + `read_only`.
- Pinned the NVIDIA base URL to `https://integrate.api.nvidia.com/v1` and kept credentials process-scoped/redacted.

## Validation evidence

- Focused implementation suite: passing after final hardening.
- Full repository verifier: one complete pass with pytest exit 0 plus configuration, interpreter, dependencies, syntax, line endings, change-governance, and three-rule checks passing.
- Final frozen-tree repository verifier: passed before merge; integrated exact-head verification on `e9abc26388660ade117f055e11ccd1aaee34c941` also passed after current `main` was absorbed.
- Diff scope check: passing; only 095-owned paths changed.

## Review

- Successful NVIDIA Nano code-quality review identified an external-boundary concern plus disabled-state test coverage.
- Resolution: external-boundary findings were reconciled against the authoritative approved-connector architecture; benchmark is explicitly external, not Work networking. Base URL pinning and disabled-state coverage were added as defense in depth.
- Two later Nano review attempts failed before producing findings (`NvidiaNimError`); they are runtime failures, not review approvals or findings.
- Codex review invocation exceeded the tool wait before returning a verdict; no Codex verdict is claimed.

## Git and merge

- Branch: `change/095-nim-subagent-models`
- Worktree: `.work/worktrees/095-nim-subagent-models`
- Base: `3eaf50d15282614a90a825e9878254a1e713bb31`
- Implementation commit: `619d1e67b2110d51cc4c79f9fa9104d1528b9627`; integrated verified head: `e9abc26388660ade117f055e11ccd1aaee34c941`.
- Pull request: #105, merged by the governed exact-head operation; remote 095 branch deleted at the verified head.
- Cleanup: permitted after this metadata-only closure lands; unrelated worktrees remain untouched.

## Live benchmark evidence

- `nano-text`: initial 4.471s pass; two-run validation 11.558s pass and 7.836s structured-quality failure. Rejected for inconsistent output contract.
- `minimax-m3`: 19.993s, 17.815s, and 25.986s; all three runs structured and passed concrete correctness + security checks. Qualified for production-profile consideration.
- `laguna-xs`, `deepseek-flash`, and `deepseek-pro`: hosted endpoint HTTP failures. Rejected.
- `glm-5.2`: exceeded transport timeout. Rejected.
- `step-3.7-flash`: 34.239s with invalid response. Rejected.
- Baseline evidence: Nano Omni passed at 12.697s; Super exceeded 40s and failed; Ultra passed at 13.984s but remains variance-prone from prior live evidence.

## Residual items

- Only MiniMax M3 met the new-candidate three-sample promotion bar. Production promotion is intentionally a separate bounded change; 095 itself does not alter production reviewer profiles.
