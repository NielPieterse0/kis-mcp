# Change: File Materialization Explicit Resource

- **Change ID**: `649-file-materialization-explicit-resource`
- **Risk Profile**: lean

## Outcome

Prevent oversized dispatcher reads from implicitly returning ResourceLink attachments that trigger per-call ChatGPT materialization approval; retain exact-result resource identity for explicit retrieval.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Record the observable acceptance criteria for this bounded change here.

## Implementation and verification

- Implementation notes: oversized dispatcher results retain `resource_uri` and integrity/expiry metadata but no longer include an implicit MCP `ResourceLink`; exact retrieval remains available through an explicit resource read.
- Focused checks: capability execution suite 33/33 passed; regression proved implicit links are absent while explicit resource reads restore exact JSON.
- Review findings: code-quality review clean; API-contract review identified the intentional contract change, now reconciled in `SPEC.md` and verified against internal consumers.
- Residual risk: external clients that relied specifically on the implicit `ResourceLink` content item must switch to explicit `resource_uri` reads.
- Closeout state: pending final canonical verification, PR, exact-head CI, merge, and live ChatGPT reproduction.
