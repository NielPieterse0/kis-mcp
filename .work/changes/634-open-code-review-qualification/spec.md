# Change Specification: Open Code Review Qualification

- **Change ID**: `634-open-code-review-qualification`
- **Issue**: #534
- **Status**: Active
- **Complexity**: Medium
- **Risk triggers**: `external_action`, `security`

## Outcome

Qualify Open Code Review (OCR) as a hermetic read-only advisory adapter. Record reproducible evidence and a terminal adopt/not-adopt decision without product integration.

## Authority and scope

- Issue #534 owns the qualification and its non-adoption-by-default boundary.
- `AGENTS.md` owns repository workflow, isolation, scope, and evidence routing.
- Owned implementation is limited to `scripts/qualification/open-code-review/**`, its focused test, and this change record.
- Product reviewer code, settings, policy, authority documents, GitHub workflows, credentials, and merge authority are excluded.

## Requirements

- **REQ-001**: Pin an exact OCR package/version and package integrity; never use `latest` as benchmark identity.
- **REQ-002**: Run only from disposable/generated state, expose no GitHub credentials, run no `ocr init`, and grant no mutation or posting authority.
- **REQ-003**: Select a representative historical KIS corpus covering security, architecture, API/contract, test-quality, documentation/authority, clean, and large-change evidence.
- **REQ-004**: Treat OCR output only as candidate evidence and never fabricate metrics when OCR cannot execute.
- **REQ-005**: Compare OCR with current KIS reviewers only when the hermetic runtime preflight succeeds; otherwise fail closed and mark quality metrics not measurable.
- **REQ-006**: Qualification itself never authorizes product adoption. A materially successful result would require a separate adapter issue.

## Acceptance

1. Exact package/runtime/corpus provenance is machine-readable and reproducible.
2. Hermetic execution either succeeds without forbidden side effects or fails closed with explicit evidence.
3. Incremental-finding and reviewer-discourse metrics are reported only from successful OCR runs.
4. The final decision distinguishes operational incompatibility from a claim about OCR review quality.
5. No excluded product or authority path changes.

## Recovery and out of scope

Remove this qualification-only script/change record by reverting the change. OCR product integration, policy exceptions, Application Control changes, credential provisioning, and a new external adapter are out of scope.
