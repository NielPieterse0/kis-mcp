# Change: Runtime Startup Policy Fingerprint

- **Change ID**: `147-runtime-startup-policy-fingerprint`
- **Development level**: Small
- **Source**: #216 / parent #215

## Outcome

Make fresh `kis-dev` and `kis-op` startup evidence use the same canonical policy fingerprint as the serving Python runtime.

## Scope and acceptance

- Replace raw policy-file byte hashing in `start-chatgpt.ps1` with canonical parsed-JSON hashing matching `gateway.foundation.policy_fingerprint`.
- Fail closed if fingerprint calculation fails or does not produce a 64-character lowercase SHA-256 digest.
- Preserve all other startup, tunnel, credential, and readiness behavior.
- Add focused regression coverage proving the raw-file hash path is no longer used.

## Verification

- Red test reproduced the raw-file hashing defect before implementation.
- `tests/test_startup_scripts.py`: 31 passed.
- Startup + operational-status focused suite: 49 passed.
- PowerShell parser: PASS for `scripts/start-chatgpt.ps1`.
- Launcher canonical digest: `c8f561a07c9170130f832e4858a27f4e3622c8352d1e8f9acc9829c207a8ec96`, exactly matching live `kis_health`.

## Review

- Base code-quality review: PASS; diff is limited to launcher fingerprint calculation plus regression test.
- Canonicalization matches the runtime exactly: UTF-8 parsed JSON, sorted keys, compact separators, SHA-256.
- Failure handling remains fail-closed before startup evidence is written.
- Advisory review backend was attempted twice; the default attempt timed out and explicit `codex-cli` returned `AGENT_BACKEND_FAILED:CodexCliError` (tracked separately by #210). No backend failure is represented as review success.

## Local governance limitation

Canonical `change-workflow new` is currently blocked by unrelated pre-existing active-claim conflicts involving changes 140/142/145. Exact inspection confirmed this change owns only `scripts/start-chatgpt.ps1`, `tests/test_startup_scripts.py`, and its own change evidence. The worktree was therefore created from exact synchronized `main` using the same emergency manual-worktree evidence mode already in use by change 146.
