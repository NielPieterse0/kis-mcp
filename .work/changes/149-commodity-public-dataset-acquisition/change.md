# Change: Commodity Public Dataset Acquisition

- **Change ID**: `149-commodity-public-dataset-acquisition`
- **Risk Profile**: lean

## Outcome

Authorize Commodity to use the existing public-http-dataset registered acquisition profile for bounded weather and NYISO evidence recipes without widening ordinary Work network authority.

## Scope and acceptance

- Implement only the paths declared in `scope.json`.
- Keep the existing Firecrawl authorization unchanged.
- Authorize registered project `commodity` to use profile `public-http-dataset` only through approval-gated `commodity-*` recipes under `config\\acquisition-recipes`.
- Permit only the dynamic keys needed by the reusable Open-Meteo recipe: `latitude`, `longitude`, and `run`.
- Do not change HR-002 or claim provider-host authorization that belongs to `import-isolate`.

## Implementation and verification

- Implementation notes: added one KIS authorization profile entry; no runtime code or policy-core change.
- Focused checks: acquisition/dispatch tests passed (8/8); checked-in settings load and authorize the exact new profile; scope check and `git diff --check` passed.
- Review findings: safety/security review found no secret exposure. Its HR-002 concern is non-blocking because `docs/EXTERNAL-ACQUISITION-MODULE-PRODUCT-SPEC.md` defines this approval-gated external action as separate from ordinary Work; the omitted Firecrawl `query` key is intentional because profile parameters are profile-specific.
- Residual risk: `import-isolate` must separately permit the Open-Meteo and NYISO hosts before live capture can succeed.
- Closeout state: KIS-side implementation and focused verification complete; provider-policy dependency remains external to this change.
