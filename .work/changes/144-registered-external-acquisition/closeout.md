# Closeout: Registered External Acquisition

## Status

Implementation, provider alignment, durable documentation, current-main integration, and pre-merge review are complete under issue #214 / change 144. This change is independent of Project Tasks issue #215 / PR #221.

## Implemented KIS boundary

- Added strict schema-versioned `settings/external-acquisition.settings.json` for registered-project/profile/recipe authorization and request budgets.
- Added strict external-acquisition settings/result contracts and durable `docs/EXTERNAL-ACQUISITION-MODULE-PRODUCT-SPEC.md`.
- Added `kis_acquire_registered_evidence` as an approval-gated discoverable external virtual operation with fixed project/profile/recipe/hash/parameters/approved fields.
- KIS derives the consumer recipe only from central project registration plus configured project-relative authority, resolves containment, verifies exact recipe SHA-256, strips `approved`, and delegates only the normalized request.
- Added fixed `import-isolate` host adapter and strict credential-value-free provenance/result validation.
- Existing registered-GitHub virtual approval/dispatch behavior remains independent; unrelated virtual families cannot opt into schema-bound approval.
- Ordinary Work HR-002 is unchanged; no generic URL/HTTP/Firecrawl-target passthrough is exposed.

## Provider dependency and exact alignment

The companion provider work landed first:

- Repository: `NielPieterse0/import-isolate`
- Issue: #2 — completed
- PR: #3 — merged
- Exact provider PR head: `c478b8b5a4f9251a0b98630d63e08d12f78b03f3`
- Landed provider main merge: `800a8c78162bf8c3d079a01199d2afb7c65598b9`
- Exact provider verification: run `31792940963` — success
- Verification included JSON contract parsing, registered PowerShell syntax, six focused boundary tests, and the full 126-test Windows repository baseline.

Landed provider behavior preserves existing HTTP recipe v1 and adds Firecrawl recipe v2. The registered provider boundary independently re-verifies project/profile/recipe/hash identity against provider policy, permits only the existing profile-authorized Firecrawl `search` / `scrape` / `map` path, and returns the strict result shape mirrored by KIS. KIS and the landed provider require the same result fields, enums, hashes, credential-reference shape, and provider-relative artifact-path semantics.

## KIS verification and review

Test-first RED history was preserved before the acquisition implementation existed. Focused tests cover strict settings, registered project/profile/recipe authorization, immutable hash checks, parameter allowlisting, approval handling, provider result identity, registered-GitHub compatibility, rogue virtual-family rejection, and provider diagnostic secret-reflection prevention.

Canonical Verification on implementation head `c6969d45516bf089dbaa2c668faa0715cc59dd10` succeeded in run `31792735771`. Earlier failing runs found only two test-fixture defects; both were corrected without weakening production checks. Manual architecture/security/API review found and corrected:

- provider child stderr/stdout could have been reflected to callers on failure — now only a bounded exit-code error is exposed, with regression coverage;
- KIS result JSON Schema did not encode the runtime's provider-relative path restriction — now aligned with the landed provider contract;
- provider acquisition-recipe schema identity was initially changed while adding Firecrawl v2 — provider PR #3 preserved the prior `$id` for compatibility.

No blocking review finding remains.

## Current-main integration

After Project Tasks PR #221 landed, current `main` advanced from the #214 branch base to `1303fad3940e3fc1bf10d61fdc888590fc996056`. Comparison found zero path overlap between those 54 intervening commits and #214's implementation surface.

GitHub then generated synthetic merge commit `38c7fdb216f46e3847ed127ab4b1fa2862bb300f` with exact parents:

1. current `main` `1303fad3940e3fc1bf10d61fdc888590fc996056`;
2. #214 head `c7471c4db076e8c77644b3623315ee463550f8e0`.

That exact combined tree was promoted onto `change/144-registered-external-acquisition` before final documentation/closeout commits. Final Canonical Verification must succeed on the resulting branch head; no earlier successful head is sufficient merge evidence.

## Live commissioning

Live KIS/Firecrawl commissioning is not claimed in this chat host because the `kis-op` / `kis-dev` execution namespace is currently unavailable. In addition, the landed provider's new script/tool paths alter the `import-isolate` security fingerprint, so real Firecrawl intake requires a fresh local `Invoke-ContainmentTests.ps1 -ForceBuild` result for provider main `800a8c78162bf8c3d079a01199d2afb7c65598b9` before `Import-WebEvidence.ps1` can pass its own live containment gate.

This is an execution-environment commissioning gate, not a contract ambiguity: both repositories' checked-in interfaces and exact-head verification are aligned. Stale containment evidence or unavailable runtime state must not be represented as successful live commissioning.

## Git and merge

- Branch: `change/144-registered-external-acquisition`
- Pull request: #230
- Provider dependency: landed and verified
- Final KIS exact-head verification: pending this closeout head
- Merge: pending exact-head success
- Post-merge registered default-branch refresh / runtime commissioning / worktree cleanup: pending available KIS local execution surface
