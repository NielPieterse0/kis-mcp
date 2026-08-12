# Closeout: NIM Sub-agent Models

## Implemented scope

- Added a separate allowlisted NVIDIA benchmark catalog; production `nano`, `super`, and `ultra` profiles remain unchanged.
- Added a portable bounded benchmark request path through the existing approved NVIDIA external connector.
- Added fixed correctness/security capability scoring, 1-3 run repetition, and a 30-second suitability latency gate.
- Kept the benchmark out of the direct tool profile; capability discovery classifies it as eligible `external` + `read_only`.
- Pinned the NVIDIA base URL to `https://integrate.api.nvidia.com/v1` and kept credentials process-scoped/redacted.

## Validation evidence

- Focused implementation suite: passing after final hardening.
- Full repository verifier: final post-merge closeout run passed with 653 tests passing, 2 expected skips, pytest exit 0, plus configuration, interpreter, dependencies, 247-file syntax, line endings, change-governance, and three-rule checks passing.
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
- Cleanup: the 095 worktree and merged local branch are absent; `kis-op` is running from `C:\Projects\kis-mcp` current `main`. Unrelated 096 worktrees remain untouched.

## Live benchmark evidence

- First closeout run: `nano-text` showed inconsistent structured output; `minimax-m3` completed three structured quality-passing samples; `laguna-xs`, `deepseek-flash`, and `deepseek-pro` returned hosted HTTP failures; `glm-5.2` exceeded the transport timeout; `step-3.7-flash` returned an invalid response. Baseline Nano and Ultra passed while Super exceeded the benchmark timeout.
- Independent repeat in the same commissioning window confirmed the variance rather than a stable promotion result: `nano-text` completed 3/3 calls but only 2/3 passed the structured-quality contract (8.906s, 10.094s, 16.059s); `minimax-m3` produced two structured quality-passing runs (14.773s and 16.981s) followed by an HTTP failure, so only 2/3 runs succeeded.
- The independent first-screen measurements were: baseline Nano 8.486s pass; baseline Super 40.130s transport failure; baseline Ultra 10.960s pass; `nano-text` 7.367s pass; `minimax-m3` 5.667s pass; `laguna-xs` 0.459s HTTP failure; `deepseek-flash` 0.206s HTTP failure; `deepseek-pro` 0.257s HTTP failure; `glm-5.2` 40.201s transport failure; `step-3.7-flash` 27.565s invalid response.
- Combined evidence therefore does not establish any experimental alias as sufficiently reliable for automatic production-profile promotion. Production `nano`, `super`, and `ultra` remain unchanged.

## Residual items

- Any future production-profile promotion must be a separate bounded change with fresh repeated evidence. MiniMax M3 is the strongest experimental candidate observed, but its later 2/3 success repeat demonstrates upstream/reliability variance that must be resolved before promotion.
