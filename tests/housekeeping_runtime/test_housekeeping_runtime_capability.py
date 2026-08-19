from __future__ import annotations

from kis_mcp.capabilities.contracts import ExposureMode, OperationEffect
from kis_mcp.housekeeping_runtime.capability import housekeeping_capability_contribution


def test_housekeeping_capability_effects_and_approval_are_explicit() -> None:
    contribution = housekeeping_capability_contribution()
    operations = {item.name: item for item in contribution.operations}

    assert contribution.contribution_id == "housekeeping-runtime"
    assert all(
        item.exposure.mode is ExposureMode.DISCOVERABLE
        for item in operations.values()
    )
    assert operations["kis_housekeeping_status"].effects == (
        OperationEffect.READ_ONLY,
    )
    assert operations["kis_housekeeping_receipt"].effects == (
        OperationEffect.READ_ONLY,
    )
    apply = operations["kis_housekeeping_apply_receipt"]
    assert apply.effects == (OperationEffect.EXTERNAL,)
    assert apply.approval_required is True
