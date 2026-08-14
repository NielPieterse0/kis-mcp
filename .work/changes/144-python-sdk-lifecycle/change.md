# Change: Python Sdk Lifecycle

- **Change ID**: `144-python-sdk-lifecycle`
- **Risk Profile**: lean

## Outcome

Make the MCP Python SDK lifecycle truthful by disabling the uncomposed platform-library descriptor in checked-in settings and documenting/testing that it is retained only as staged development metadata, not a mounted runtime provider.

## Scope and acceptance

- Set the checked-in Python SDK provider settings to `enabled=false`.
- Retain the exact source/package pins and explicit descriptor for development/test use.
- Keep the Python SDK absent from the platform runtime registry and mounted provider surface.
- Document that re-enabling requires a separate runtime-provider design; do not mount a Python module as a `FastMCP` server.
- Preserve explicit enabled-state readiness/version tests without probing the disabled checked-in configuration.

## Implementation and verification

- Implementation: disabled the checked-in provider setting and replaced the historical deferred-composition wording with an explicit staged/disabled lifecycle decision.
- Focused checks: `tests/providers` passed 273/273 under Python 3.13. The isolated legacy provider test module still exposes a pre-existing import-order circularity when run alone; suite execution is green.
- Review findings: required `api-contracts` review passed with no blocking findings; reviewer confirmed the disabled staged-library classification is truthful and non-breaking.
- Residual risk: live post-landing verification must confirm provider status/capability discovery continue to omit `mcp-python-sdk` on a fresh runtime.
- Closeout state: implementation complete; review, exact-head CI, landing, and live verification pending.
