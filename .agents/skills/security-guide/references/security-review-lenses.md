# Security Review Lenses

Load only the sections relevant to entry points, trust boundaries, and sensitive sinks observed in the scoped code.

## Access Control

Trace identity from authentication through every object lookup and state-changing action. Verify subject, tenant, role, ownership, delegation, and resource state at the enforcement point. Look for identifiers accepted from the request, repository methods without subject constraints, confused-deputy service calls, and background work that loses user context.

## Injection And Interpretation

Identify where untrusted text becomes a query, command, template, expression, path, header, log record, or structured document. Verify contextual encoding or parameterization at the final interpreter. Validation for one grammar does not protect another grammar.

## Browser And Markup

Trace untrusted data into HTML, script, URL, CSS, and DOM contexts. Verify context-appropriate escaping, safe URL schemes, state-changing request protection, origin policy, cookie attributes, and whether active output is stored and later rendered elsewhere.

## Server-Side Requests

Trace user influence over scheme, host, port, resolved address, redirects, proxy behavior, and request headers. String checks against hostnames are not sufficient when alternate address forms, DNS rebinding, redirects, or parser disagreement remain possible. Prefer a narrow destination allowlist and verify after resolution and redirect decisions.

## Files, Paths, And Archives

Trace filenames and paths through decoding, normalization, canonicalization, link handling, and final open or extraction. Check absolute paths, traversal, alternate separators, symlinks or reparse points, archive entries, overwrite behavior, size limits, and active content served after upload.

## Deserialization

Identify the parser, accepted types, object construction behavior, schema validation, size and depth limits, and whether input can select classes, callbacks, templates, or code paths. Safe parsing still requires authorization and semantic validation after decoding.

## Secrets And Cryptography

Do not copy secret values. Check source control exposure, logging, error output, fixtures, client bundles, rotation path, key separation, randomness, nonce reuse, algorithm or mode misuse, and whether comparison leaks material timing information. Prefer established repository primitives over custom cryptography.

## State And Concurrency

Look for check-then-act gaps, replay, duplicate processing, idempotency failures, stale authorization, raceable quota or balance updates, and partial failure that leaves privileged state inconsistent. Establish transaction and retry boundaries before claiming a race.

## CI And Build Inputs

Treat branch names, commit messages, issue text, artifact names, generated metadata, and external contribution content as untrusted. Trace them into build commands, templates, paths, logs, and privileged jobs. Review permission scope and secret availability, but do not infer current hosted settings from repository YAML alone.

## Finding Refutation

Before reporting, test the candidate against reachability, environment, framework guarantees, caller validation, sink context, authorization checks, test-only status, and attacker prerequisites. A dangerous name, stale comment, or regex hit is not enough.
