# P1 Boundary Hardening Specification

## Status

Approved, implemented, integrated with current `main`, and reverified after pull-request review repair. Awaiting exact-head landing approval.

## Operator-approved hard-coded enforcement

On 2026-08-04 the operator explicitly approved continuing with the following code-level boundary checks:

- Git and shell effect resolution needed to prove HR-001, HR-002, or HR-003;
- process working-directory state used only to resolve subsequent concrete effects;
- GitHub search-query authorization that requires one approved repository scope and rejects scope-escaping query grammar;
- Discover Git metadata-graph validation that rejects reads escaping the configured project boundary.

This approval is limited to the six P1 findings in this specification. It does not authorize a fourth policy rule, a command or executable denylist, broader provider restrictions, or additional hard-coded blocks. Any new hard-coded block requires separate operator approval before implementation.

Approved implementation slice derived from the operator-requested P1 findings in the 2026-08-04 full review of `main`.

Development level: **Complex**. The change crosses the Work enforcement boundary, stateful provider sessions, Git configuration resolution, GitHub repository authorization, and Discover read authority. Incorrect behavior can bypass HR-001, HR-002, HR-003, or repository read scope.

## Outcome

Close all six P1 findings without adding a fourth policy rule, reducing ordinary tool availability, changing provider authentication, or modifying active Skills, Startup Hardening, Provider Runtime Composition, Supabase, policy, quarantine, or server-composition work.

## Requirements

### R1 — Parse complete Git invocation context

- Consume supported Git global options and their values before identifying the subcommand, including repeated `-C`, `--git-dir`, `--work-tree`, `--namespace`, and `-c` configuration overrides.
- Resolve the effective working directory and repository metadata locations used by the invocation.
- For local mutating operations, report every known mutated worktree or metadata path rather than only the caller-supplied `cwd`.
- Detect forced non-dry-run `git clean` as unresolved permanent-delete intent under the effective repository.
- Evaluate remote Git operations using the effective repository selected by global options.

### R2 — Preserve interactive process state

- Track process/session state by the provider process identifier returned from successful `start_process` calls.
- Track effective working directory and a bounded push-directory stack for supported directory-changing commands.
- Resolve subsequent `interact_with_process` commands against the stored working directory.
- Update state only after successful provider calls and remove state on explicit process exit/termination evidence.
- For statically recognized persistent startup shells, including `cmd /k` and PowerShell `-NoExit -Command`, retain the final startup working directory before later interactions are evaluated.
- Unknown or missing process identifiers must retain the existing allow-on-uncertainty behavior.

### R3 — Parse supported shell control syntax narrowly

- CMD parsing must recognize unescaped single `&`, `&&`, `||`, pipe, and simple parenthesized command groups.
- PowerShell parsing must recognize `;`, newline, `&&`, `||`, pipe, the invocation operator `&`, and statically resolvable simple script blocks.
- CMD caret escapes and PowerShell backtick escapes must prevent escaped separators from splitting commands.
- Sequential command segments must carry forward directory changes when later relative paths are resolved.
- The implementation must remain an exact parser for supported forms, not a broad executable denylist.

### R4 — Resolve actual Git network targets

- Push operations must prefer `remote.<name>.pushurl` over `remote.<name>.url`.
- Honor explicit `git push --repo=<repository>` and `--repo <repository>` targets.
- Apply branch `pushRemote`, `remote.pushDefault`, branch remote, and named-remote precedence for the operation.
- Read local `include.path` and statically matching local `includeIf` files that Git would load, while ignoring unsafe, external, missing, or unsupported include forms.
- When multiple effective URLs exist, any proven external URL establishes HR-002.

### R5 — Prove GitHub search repository scope without over-restricting search

- Parse the bounded Boolean/query structure needed to prove that exactly one effective repository constraint applies to the complete search expression.
- Require that the effective repository equals an approved repository.
- Reject additional `repo:`, `org:`, `user:`, or `owner:` scope qualifiers.
- Reject `OR` or `NOT` only when the expression can remove, negate, or bypass the approved repository constraint.
- Permit ordinary grouping and filters that remain subordinate to the approved repository, including `path:`, `language:`, `filename:`, `symbol:`, nested filter disjunctions, and safe exclusions such as `NOT path:tests`.
- Report parser/subset limitations as `unsupported_search_grammar`, separately from `repository_scope_violation`.
- Non-search repository-target authorization remains unchanged.

### R6 — Validate the Discover Git metadata graph
Before running Git, Discover must validate only metadata paths that the fixed read-only inspection will actually load or may traverse:

- effective Git directory and common directory;
- active worktree metadata/admin paths and index path;
- object directory and active alternate object databases when object traversal is required;
- local configuration files and only active include paths, including statically matching supported `includeIf` conditions;
- nested path components for links or reparse points on those active paths.

Every actively loaded or traversed path must remain inside the configured Discover read boundary. Passive values such as remote URLs, inactive conditional includes, disabled `config.worktree` files, and alternate records in an unborn repository must not cause rejection. Unsafe, invalid, or outside-boundary active metadata must return a stable unavailable Git diagnostic and no Git subprocess may run.

## Exclusions

- No new policy IDs or settings.
- No general shell AST, arbitrary script execution prediction, or runtime sandbox replacement.
- No environment-variable inference unless the provider invocation explicitly supplies a supported value.
- No provider login/authentication work.
- No P2 or P3 review findings.
- No active-slice cleanup or repair of the repository claim-validator recursion defect.

## Acceptance evidence

- New regression tests demonstrate each reported bypass fails before implementation and passes afterward.
- Existing negative tests continue to prove inert URLs, unknown commands, help/read-only forms, and unresolved effects remain allowed.
- Targeted Work, middleware, GitHub scope, and Discover Git suites pass.
- `scripts/change-workflow.ps1 check` passes for this change scope; the separately recorded recursive global `validate` defect may remain.
- Full `pwsh -File scripts/verify.ps1` passes on the final branch state.
- Final diff review finds no edits outside `scope.json` ownership and no unresolved Critical or Important findings.

## Recovery

The slice is isolated on `change/015-p1-boundary-hardening`. Recovery is branch reversion or PR closure; no migration or persistent operator data change is introduced.

## Governance baseline correction
The initial baseline exposed stale `active` claims for already-merged changes 005 and 008. Their merged GitHub state was verified, the records were changed to `closed`, and current change-governance verification passes. No live agent claim was altered.

