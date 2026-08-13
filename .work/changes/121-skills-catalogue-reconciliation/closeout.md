# Closeout: Skills Catalogue Reconciliation

## Implemented scope

- Canonical Skills discovery remains rooted only at `C:\Projects\.agents\skills`; production settings require `kis-mcp` explicitly.
- Valid shared skills without private KIS capability metadata remain listable/loadable and are omitted only from enhanced capability contributions.
- Missing/invalid canonical `kis-mcp` fails the Skills startup path specifically.
- The repository-local `.agents/skills/kis-mcp` package is removed; a verified seven-file recovery copy is retained at `C:\Projects\.kis-mcp\temp\121-repo-local-kis-mcp-backup`.
- GitHub Actions may create a minimal `kis-mcp` canonical fixture only when the external canonical catalogue is absent; local/production verification still requires the real canonical skill.

## Validation evidence

- RED: five core regression tests failed on the original metadata exception / missing `required_skills`; the CI bootstrap test failed before verifier provisioning was implemented.
- GREEN: affected Skills/capability/repository-scope suite completed 100% with exit code 0.
- Real canonical catalogue smoke: 46 discovered Skills, 29 enhanced contributions, `kis-mcp` and `bayesian-modeler` both discoverable.
- `register_platform_skills` smoke: `SkillsService`, 46 cards, 29 enhanced contributions.
- PR-context change governance: 111 claims, `ok: true`.
- Local canonical verification passes line endings, configuration, interpreter, dependencies, and syntax before pre-existing historical active-claim topology blocks the aggregate local gate.
- A full pytest attempt reached 100% with no displayed failures but a spawned child did not exit; it is not counted as passing evidence. Exact-head GitHub Canonical Verification remains the full-suite gate.

## Review

- Blocking finding: deleting repo-local `kis-mcp` would otherwise leave GitHub Actions without the newly required canonical skill because the existing workflow seeds its ephemeral root from repo-local packages.
- Resolution: add CI-only canonical fixture provisioning to `scripts/verify.ps1`; keep active change 120's workflow untouched.
- No unresolved Skills correctness or capability-classification finding remains.

## Landing and commissioning

- Base: `73156f3bfa70936f1b4d3b79fbe73548a1dba9d1`.
- Exact-head CI / merge / tracking refresh: pending.
- `kis-op` restart/smoke: pending.
- Post-merge documentation reconciliation remains required only for exact merge/commissioning evidence and any stale authority wording outside 121 ownership.
