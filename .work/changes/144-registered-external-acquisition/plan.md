# Registered External Acquisition Implementation Plan

## Delivery order

1. Preserve the separate #214 identity as change 144 and keep #215/PR #221 out of scope.
2. Define strict KIS authorization settings and mirrored `import-isolate` result contract.
3. Add acquisition settings/runtime/service/provider modules with registered-project and immutable-recipe validation.
4. Add `kis_acquire_registered_evidence` to the capability catalogue and explicitly extend virtual dispatch only for the `registered-acquisition` family.
5. Prove authorized, denied, malformed, hash-mismatch, provider-failure, receipt-validation, and registered-GitHub compatibility cases.
6. Reconcile against `import-isolate#2`, require its recipe-safe provider bridge to land first, then verify the exact provider contract from its landed main.
7. Publish exact KIS head, require canonical GitHub Actions, perform live allowed/denied commissioning, merge, reconcile #214, and clean the change.

## Constraints

- No arbitrary HTTP/URL/Firecrawl target fields on the KIS operation.
- No secret values in settings, arguments, logs, receipts, or Work metadata.
- No generic virtual-operation approval bypass; only explicit registered families may use schema-bound `approved=true`.
- Do not overlap #215/PR #221 documentation or Work Management ownership.
- Consumer recipe semantics remain outside KIS.
