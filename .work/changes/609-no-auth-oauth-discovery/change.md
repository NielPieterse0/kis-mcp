# Change: No Auth Oauth Discovery

- **Change ID**: `609-no-auth-oauth-discovery`
- **Risk Profile**: lean

## Outcome

Upgrade and pin the OpenAI tunnel-client integration to a release that treats all-404 no-auth OAuth discovery as optional while preserving malformed and 5xx discovery diagnostics.

## Scope and acceptance

- Use OpenAI tunnel-client v0.0.13 for both configured remote instances without interrupting the currently running kis-op process.
- Pin the executable version, extracted executable SHA-256, and published Windows amd64 release-archive SHA-256.
- Fail closed before tunnel startup if the configured executable is missing, has the wrong hash, or reports the wrong version.
- Preserve the upstream no-auth invariant: all protected-resource discovery candidates returning 404 are optional, while malformed or 5xx metadata remains diagnostic/degraded.

## Implementation and verification

- Implementation notes: settings now point to the side-by-side v0.0.13 installation; `tunnel-state.ps1` validates version/hash metadata and exposes a reusable executable preflight used by setup and startup.
- Focused checks: managed Python focused suite `tests/test_tunnel_scripts.py tests/test_remote_runtime.py` = 25 passed; runtime executable preflight reports version 0.0.13 and SHA-256 `83f08fb39b1c154747debd31b81b65dd4ee834cacf5a073b6301b2688699bc76`; release archive matched published SHA-256 `17113162b353906bbb884c3ed7620facba5cc72b5fdc94fd54fd7208c7166edb`.
- Review findings: independent kis-op/NVIDIA code-quality review completed with no actionable findings; all findings were informational.
- Residual risk: upstream tunnel-client behavior remains an external dependency; the repo now pins the known-good release and fails closed on drift.
- Closeout state: implementation and review complete; landing pending.
