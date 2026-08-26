# Lossless legacy requirement transfer audit

Date: 2026-08-26  
Work: #497  
Change: `241-lossless-legacy-transfer-ledger`  
Repository baseline: `582b90dba30aa2c3abfcd0692c1439b3426f1b61`

## Purpose

This is historical/verification evidence, not current product authority. It verifies that the legacy backlog consolidated by #475 and programmes #488-#496 did not disappear merely because source issues were superseded.

The machine-readable authority for this audit is `ledger.json`. Current product behavior remains governed by repository authority, source/contracts/tests, provider evidence, and live runtime evidence.

## Result

- 84 superseded legacy source issues are accounted for exactly once across #488-#496.
- Five retained Deferred sources (#476-#480) are accounted for separately and remain first-class triggered work.
- Combined source coverage is 89/89 unique sources with no source-to-programme duplication.
- 92 normalized material requirement rows were recorded.
- Controlled dispositions: 78 `implement_current`, 2 `implemented_verify`, 3 `superseded_2026`, 7 `future_triggered`, 2 `not_required`.
- Title-only source records #145 and #435 are explicitly evidence-limited; no missing body semantics were invented.

All machine invariants embedded in `ledger.json.validation` pass.
## Method

1. Read #497 and each programme issue #488-#496 as the destination contract.
2. Re-read the legacy GitHub issue bodies rather than treating programme summaries as requirement evidence.
3. Expand each source into one or more material outcome/invariant/acceptance/trigger rows.
4. Assign exactly one destination programme and one controlled disposition per requirement.
5. Re-baseline MCP-facing requirements against the local 2026-07-28 corpus rooted at `000-index.md`; `055-specification-schema-reference.md` is schema authority.
6. Require current evidence for `implemented_verify`, replacement rationale plus 2026 references for `superseded_2026`, and an objective activation condition for `future_triggered`.
7. Validate source-set equality, uniqueness, dispositions, owner presence and deferred-trigger completeness mechanically.

## #475 current baseline evidence

The live `kis-dev` instance and local/origin `main` all reported revision `582b90dba30aa2c3abfcd0692c1439b3426f1b61` during this audit.

Current repository evidence proves the bounded #475 baseline used by this ledger:

- `pyproject.toml` pins `fastmcp[tasks]==4.0.0b3`.
- `src/kis_mcp/mcp2026.py` installs `io.modelcontextprotocol/tasks` and defines optional long-running task configuration.
- `src/kis_mcp/gateway/composition.py` installs the Tasks extension on the composed gateway.
- `tests/test_mcp2026_tasks.py` proves synchronous fallback, task creation, same-service reconnect retrieval, and selected long-running tool registration.
- `tests/test_mcp2026_wire.py` proves JSON Schema 2020-12 wire schemas and modern `resource_link` tool content.
- `SPEC.md` explicitly keeps MCP task IDs transport-facing and KIS Work/receipt/fence identity authoritative.
## MCP 2026 re-baseline

Legacy MCP prescriptions are not current authority. The 2026 corpus materially changes several assumptions that appeared in older issues: request metadata/capabilities are per-request, `server/discover` is the modern discovery boundary, results carry `resultType`, MRTR replaces unsolicited server-to-client requests, subscriptions use `subscriptions/listen`, cache hints use `ttlMs`/`cacheScope`, and Tasks/OAuth client credentials are negotiated extensions.

Accordingly:

- #343 and #347 old FastMCP 3/MCP 2025 implementation prescriptions are `superseded_2026`; their intended safety/simplification outcomes remain preserved under #488.
- #366's durable spec-first governance rule is verified current, while its old FastMCP3/MCP2025 mapping is `superseded_2026`.
- #333's bounded current Tasks/stateless outcome is `implemented_verify`; process-restart/multi-worker task persistence remains `future_triggered` under #498 rather than being falsely claimed complete.
- #476-#480 remain deferred until their issue-owned objective triggers fire. Current ResourceLink type support alone does not activate #476 because live client compatibility/output pressure is still part of its trigger.

## Preserved deferred triggers

| Issue | Trigger summary |
|---|---|
| #476 | #475 landed plus either live ResourceLink/resource-read client proof or observed KIS output/truncation pressure. |
| #477 | Runtime supports end-to-end `subscriptions/listen` and live ChatGPT proves acknowledgment/correlation plus a requested notification. |
| #478 | Runtime exposes MRTR/input-required/elicitation without private hooks and live ChatGPT completes an elicitation-capable round trip. |
| #479 | #475 landed and the selected FastMCP stack exposes 2026 list/discovery cache metadata at the server boundary. |
| #480 | Operator approves unattended remote-provider OAuth need, or explicitly approves Supabase with standard client-credentials support. |

Additional trigger-preserved work discovered during normalization is #330 (Hyper-V capable host) and #333's restart-persistence remainder now owned by #498.
## Duplicate-owner and governance review

Three cross-programme relationships are intentional interfaces, not duplicate requirement ownership:

- #445: #490 owns underlying runner/action state evidence; #489 owns Work-front-door/tool-user visibility.
- #465: #493 owns repository/service registration; #489 consumes registered identity in Work Management.
- #450: #494 owns the user-facing communication/documentation style contract; #489 consumes it in Work workflows.

A material legacy-authority conflict was found and dispositioned: #444's exact four-tier work-selection proposal was explicitly withdrawn/unapproved and current `SPEC.md` deliberately excludes those tiers. It is therefore `not_required`, not `implement_current`. The later clarified #443 remains `implement_current` under #489 and requires exact ordering/interaction to be planned and evaluated against the current deterministic design before implementation.

#324 is similarly split rather than revived wholesale: the clean/disposable Windows execution outcome remains #495 work, while restoring its old VM/Actions-first architecture as normal execution authority is `not_required` because later approved architecture replaced that prescription.

## Open transfer state

This audit does **not** claim the programmes are implemented. The 78 `implement_current` requirements are now explicit bounded obligations owned by #488-#496. Their legacy issues may remain superseded because the requirement text, destination and disposition are preserved here.

Programme closeout must consume this ledger rather than treating superseded issue state as completion evidence. Any programme that changes a disposition must update authoritative Work and create new linked work when required by the Done-history rule; this audit remains immutable historical evidence after #497 closeout.