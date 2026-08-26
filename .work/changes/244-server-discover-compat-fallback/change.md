# Change: Server Discover Compat Fallback

- **Change ID**: `244-server-discover-compat-fallback`
- **Risk Profile**: lean

## Outcome

Make MCP 2026 server/discover compatibility fallback protocol-aware, quiet for expected legacy-provider rejection, and still fail visibly for unexpected discovery errors.

## Scope and acceptance

- Keep FastMCP 4 `server/discover` auto-negotiation as the modern authority.
- Treat Serena's known handshake-era compatibility path as explicit `legacy_compatibility` protocol evidence.
- Avoid the misleading FastMCP non-conformant-discover debug block by selecting the pinned Serena provider's known legacy negotiation mode directly, without process-global log suppression.
- Preserve unexpected discovery errors and startup failures unchanged.
- Surface negotiated protocol mode/version in Serena readiness details.

## Implementation and verification

- Implementation notes: extended provider startup state with bounded protocol mode/version evidence. Because pinned Serena 1.6.1 is a known handshake-era provider, its client is constructed explicitly with FastMCP `mode="legacy"`; the gateway-wide modern `server/discover` authority is unchanged. Protocol evidence is recorded only on the outer shared-client connection generation, never on nested proxy entries.
- Focused checks: `uv run --frozen python -m pytest tests/providers/test_client_runtime.py tests/providers/test_context7_serena_providers.py -q` passes 16/16 after the architecture fix.
- Review findings: initial architecture review rejected process-global log filtering, prose-only fallback classification, and nested protocol-state republishing. The implementation was redesigned to remove log suppression entirely, select the known Serena compatibility mode at client construction, preserve unexpected connection failures unchanged, and publish protocol evidence only for the outer connection generation. Follow-up Codex architecture review found no evidence-backed architecture violation.
- Residual risk: Serena remains intentionally pinned to handshake-era compatibility until its provider version is upgraded to conformant MCP 2026 discovery; other providers and the KIS gateway remain on modern auto-discovery semantics.
- Closeout state: focused verification 16/16, governed scope check, `git diff --check`, and follow-up architecture review are clean; commit/publication pending.
