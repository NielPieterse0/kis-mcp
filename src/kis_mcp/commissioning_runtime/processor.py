from __future__ import annotations

from typing import Any

from kis_mcp.commissioning.classifier import classify_change
from kis_mcp.commissioning.evidence import MergedChangeResolver
from kis_mcp.commissioning.intake import CommissioningIntakeService
from kis_mcp.commissioning.models import ClassificationState
from kis_mcp.commissioning.projection import project_classification_state
from kis_mcp.commissioning.settings import PostMergeCommissioningSettings


class CommissioningCandidateProcessor:
    def __init__(self, settings: PostMergeCommissioningSettings) -> None:
        self.settings = settings

    async def __call__(
        self,
        repository: str,
        pull_number: int,
        invoker: Any,
    ) -> dict[str, Any]:
        evidence = await MergedChangeResolver(invoker, self.settings).resolve(
            repository,
            pull_number,
        )
        classification = classify_change(evidence, self.settings)
        intake = await CommissioningIntakeService(invoker).intake(
            evidence,
            classification,
        )
        target = next(
            (
                item
                for item in self.settings.targets
                if item.repository.casefold() == evidence.repository.casefold()
            ),
            None,
        )
        if target is None:
            raise RuntimeError("commissioning target disappeared after evidence resolution")
        await project_classification_state(
            invoker,
            project_id=target.project_id,
            evidence=evidence,
            classification=classification,
            intake=intake,
        )
        return {
            "pull_number": pull_number,
            "source_issue": evidence.source_issue,
            "change_id": evidence.change_id,
            "merge_sha": evidence.merge_sha,
            "classification": classification.state.value,
            "ambiguous_risk_triggers": list(
                classification.ambiguous_risk_triggers
                if classification.state is ClassificationState.BLOCKED_AMBIGUOUS
                else ()
            ),
            "commissioning_keys": [
                item.commissioning_key for item in classification.obligations
            ],
            "issue_numbers": [item.issue_number for item in intake],
        }


__all__ = ["CommissioningCandidateProcessor"]
