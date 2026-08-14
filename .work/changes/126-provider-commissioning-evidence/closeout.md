# Closeout: Provider Commissioning Evidence

## Implemented scope

- Added provider-neutral exact-identity commissioning evidence under the configured KIS state root.
- DBHub identity binds provider revision, entry-point hash, row/tool settings, and registered database bindings without storing credential values.
- Docker Hub identity binds provider revision, entry-point hash, auth metadata, and expected tool surface without storing credential values.
- Successful supervised commissioning persists evidence only after live tool discovery succeeds; unchanged evidence is idempotent.
- DBHub/Docker Hub readiness reconstructs historical `live_verified` state after restart while `upstream_connected` and `tools_discovered` remain current-process evidence.
- Current product and operator documentation are reconciled.

## Verification

- RED: three new persistence/restart tests initially failed because `kis_mcp.providers.commissioning` did not exist; 18 existing provider tests passed.
- GREEN: 21/21 focused DBHub/Docker Hub integration tests pass.
- GREEN: 77/77 affected provider/platform/runtime tests pass after implementation and manual-review correction.
- Python compilation passed for all changed provider modules.
- `git diff --check` passed.
- Change 126 scope check passed.
- Ruff could not run because the locked current environment does not contain the `ruff` module; no dependency installation was performed.

## Review

- Default review backend failed independently with upstream HTTP 502.
- Explicit Codex CLI review backend failed with `AGENT_BACKEND_FAILED:CodexCliError`.
- Exact-diff manual architecture/API review found one blocking contract defect: adding a seventh commissioning key would cause provider runtime normalization to discard the entire commissioning map. The redundant key was removed and regression assertions now enforce the existing six-field contract.
- Manual review found no remaining blocking issue after the correction and affected-suite rerun.

## Concurrent repository state

- Global claim validation is currently blocked by an unrelated overlap between stale change 122 and concurrent change 127. Change 126 does not overlap either claim, and its own scope check passes.
- No change 127 file or claim was modified by this slice.

## Post-merge commissioning correction

- PR #181 landed the reviewed commissioning-evidence implementation in cumulative queue main `b6b9dd8f58163e2c97aa992a9a6c546ffb34cc70`.
- Live supervised commissioning then exposed BUG-202: DBHub's descriptor builder reports binding-local names such as `college_results_execute_sql`, while the exact identity intentionally records final public KIS names such as `db_college_results_execute_sql`.
- The evidence writer's exact equality check remains unchanged. The correction maps DBHub builder-local names to the final public provider namespace before evidence persistence; Docker Hub behavior is unchanged.
- RED: the new naming-layer regression failed because the normalization helper did not exist.
- GREEN: the regression and historical-evidence tests pass, and a supervised pre-publication run persisted DBHub evidence at exact public tool identity while Docker Hub remained idempotently verified.

## Pending landing/commissioning

- Publish the BUG-202 correction from the still-active change 126 claim under SPEC-136, pass fresh exact-head and cumulative queue CI, and land it on current `main`.
- Re-run supervised DBHub/Docker Hub commissioning from landed primary `main`, then construct a fresh KIS process/readiness instance to verify matching persisted evidence reconstructs historical commissioning across restart/process replacement.
- Close BUG-202, issue #143, SPEC-136, and their Project items only after that landed live commissioning evidence succeeds.
