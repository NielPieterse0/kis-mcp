# Change: Registered Project Schema Utf8

- **Change ID**: `235-registered-project-schema-utf8`
- **Risk Profile**: lean

## Outcome

Decode registered Project schema GitHub CLI JSON and HTTP output as UTF-8 on Windows without changing unrelated registered Git or GitHub command capture.

## Scope and acceptance

- Decode the Project schema client's `gh api` stdout/stderr explicitly as strict UTF-8.
- Production registered Project commissioning must use that schema-specific runner; injected runners remain unchanged.
- Do not alter generic registered Git/GitHub command capture or saved-view parsing semantics.
- Live acceptance requires all canonical views ready after landing.

## Implementation and verification

- Implementation notes: reproduced Windows `cp1252` decode failure with the exact saved-view request; production commissioning now uses a schema-specific runner that captures bytes and performs strict UTF-8 decoding in KIS.
- Red evidence: the routing/decoding regressions failed before implementation; an added invalid-byte regression exposed Python's Windows reader-thread behavior and drove the stronger raw-byte capture design.
- Focused checks: 4 targeted tests passed; 90 affected commissioner/wrapper/schema/service tests passed; `git diff --check` and change-scope check passed.
- Review findings: exact-commit code-quality review was clean. Exact-commit test-quality NIM output asserted four gaps contradicted by tests present in the same evidence; those findings were rejected by exact-diff inspection. Independent Codex adjudication hit its output limit, triggering the required manual exact-diff fallback. Fallback confirmed direct coverage for valid UTF-8 decode, invalid UTF-8 fail-closed behavior, production default-runner routing, custom-runner preservation, and existing saved-view malformed/pagination fail-closed behavior; no blocking test gap remains.
- Residual risk: strict UTF-8 intentionally fails closed on genuinely invalid provider output.
- Closeout state: implementation verified locally; publication and live commissioning pending.
