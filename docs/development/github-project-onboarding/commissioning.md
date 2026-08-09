# GitHub Projects Commissioning

## Commissioned target

`kis-mcp` uses the existing GitHub user Project `NielPieterse0/#1`, titled `KIS Work Management`.

Repository routing remains:

- project ID: `kis-mcp`
- repository: `NielPieterse0/kis-mcp`
- Work Management binding: `github-default`
- Project owner type: `user`
- Project number: `1`

The required `Status` single-select options are `Todo`, `In Progress`, and `Done`.

## Supervised operating mode

After commissioning, `features.reconciliation` is `enabled`. `intake` and `review_import` remain `read_only`, `programme_status` remains `enabled`, and every automation flag remains `false`.

Remote mutation remains explicit: `project_management_reconcile` requires `apply=true` and a non-empty idempotency key. No delete/archive operation or unrestricted GraphQL surface is added.

## Live provider compatibility

Official GitHub MCP `v1.8.0` returns Project item list/get records using REST-shaped fields including integer `id`, `node_id`, `content_type`, `fields`, and content `html_url`. `add_project_item` may return the GraphQL node ID as `id` and the numeric Project item ID as `item_id`.

KIS therefore normalizes the numeric Project item ID to digit text for its provider-neutral string contract and prefers that value for follow-up Project writes. GraphQL node IDs are not sent as `update_project_item.item_id`.

## 085 commissioning evidence

GitHub issue `#102` (`085: Commission GitHub Projects writes`) is the first tracked commissioning item. Live evidence established:

- Project #1 was open and initially empty;
- issue #102 was added once to Project #1;
- a node-ID update was rejected because `item_id` must be numeric;
- the numeric Project item ID represented as digit text was accepted;
- issue #102 reached `Status=In Progress`;
- focused live-shape and existing Project adapter tests pass.

The final high-level `project_management_reconcile` apply/replay/conflict proof is performed only after the running KIS instance has loaded the landed `reconciliation=enabled` configuration and compatibility fix.
