# Governance Boundary Audit — Change 226

## Result

Change 226 establishes one bounded Work-specific machine authority for the semantics in scope. No generic MRD/schema framework is introduced, and the withdrawn #444/Change 223 work-class tiers are absent from the canonical selection contract.

| Semantic area | Previous authority/duplication | Canonical owner after Change 226 | Downstream treatment |
|---|---|---|---|
| Managed fields, vocabulary, applicability, population | Project manifest, command settings, Python enums, programme prose | `settings/work-management/contracts/work-item-semantics.json` | Project field/type/options and Python value sets exact-validated |
| Work lifecycle states/transitions/readiness/claims/completion | command-plane JSON plus hard-coded lifecycle guards | `work-lifecycle-operations.json` | command-plane projection exact-validated; lifecycle guard evaluation consumes canonical guards |
| Next-work eligibility/ranking | `selection.py`, `project_commands.py`, command-plane queue | `work-selection.json` | both adapters use one shared evaluator/ranker with adapter evidence/reason profiles |
| GitHub Project field projection | `github-project-schema.json` | item semantics contract | manifest remains provider projection; canonical load rejects name/type/option drift |
| Saved-view layout/filter/display configuration | GitHub Project manifest | `github-project-schema.json` | remains provider-specific projection; schema status/commissioner retains bounded ownership |
| Operation effect classes | MCP contract prose/code | lifecycle operations contract plus existing operation map | canonical operation definitions exposed alongside existing exact tool effect map |
| Runtime feature/gate/evidence modes | Work settings | `github-projects.settings.json` | remains settings-owned operational configuration |
| Housekeeping scheduling/apply | generic false automation switches plus newer housekeeping runtime | `settings/housekeeping.settings.json` + housekeeping runtime | generic Work automation object removed; scheduler/receipt/apply remains explicit |

## Semantic completeness notes

- `Confidence` applicability and High/Medium/Low labels are established by the existing Work programme/schema. Current authority does not define evidence thresholds; the canonical contract therefore states the relative labels and explicitly records that no quantitative or qualitative threshold is defined.
- `Verification` remains repository/source verification. `Live Verification` is a separate #419 post-merge runtime/commissioning state and is not interchangeable with source verification.
- `Created` is provider-native evidence used for age ordering and is intentionally represented as an unmanaged canonical field rather than a managed Project field.
- Provider-native `Title` remains GitHub item structure rather than a managed Work Project field; saved views may display it without creating a second Work vocabulary.

## Automation disposition

- `scheduled_reconciliation` — superseded by the `kis-op` housekeeping scheduler.
- `safe_repair` — superseded by housekeeping preview → durable receipt → supervised unchanged-plan apply.
- `auto_add` — retired; explicit Work intake/reconciliation remains the named mechanism.
- `close_sync` — retired; completion/documentation reconciliation remains explicit and evidence-gated.
- `merge_sync` — retired; merge readiness/landing remains explicit governed delivery machinery.
- `review_extraction` — retired; review persistence/intake remains explicit with no background extractor.

No approved missing capability was found behind these six flags, so Change 226 does not create replacement background automation.

## Projection and compatibility boundaries

- `command-plane.settings.json` remains checked in for runtime compatibility, but repeated semantics are rejected when they drift from the canonical contracts.
- Python `RecordType`, `Priority`, `Effort`, `DeliveryStage`, `ChangeComplexity`, `DocumentationImpact`, and lifecycle-state values are exact-validated against canonical vocabulary/state sets.
- `github-project-schema.json` remains the desired provider projection. It now contains 28 managed fields; the final three are the #419 live-verification fields.
- Live GitHub Project mutation is not part of this change. Existing schema status/plan/registered-Project commissioner paths retain mutation authority.
- Current live saved-view drift remains commissioning evidence; repository tests do not claim live readiness.

## Known independent defect

The workflow package currently has a circular-import collection defect on untouched `main`: importing `tests/workflows/project_management/test_enhanced_tools.py` reaches `workflows.merge_queue` while `workflows.project_management` is partially initialized. The same failure reproduces on Change 226 and on clean `main`, so it is not treated as a Change 226 regression or fixed inside this scope.

## Residual authority

No in-scope duplicated normative rule remains without either a canonical owner or an explicit provider/settings projection boundary. Historical programme/change artifacts remain evidence only and are not rewritten as current authority.
