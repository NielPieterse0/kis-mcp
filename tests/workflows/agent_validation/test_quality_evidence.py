from __future__ import annotations

from kis_mcp.workflows.agent_validation.evidence import normalize_quality_evidence


def test_mcp_2026_findings_are_normalized_into_reusable_evidence() -> None:
    cases = {
        "resource_namespaces": ({"rule": "resource-uri-namespace", "message": "Resource URI needs a namespace"}, ["discovery", "scaffold", "review"]),
        "mcp_tasks": ({"rule": "mcp-tasks", "message": "MCP task result is incomplete"}, ["scaffold", "task_execution", "completion"]),
        "required_instructions": ({"rule": "required-instructions", "message": "Required instruction is missing"}, ["scaffold", "task_execution", "review"]),
        "elicitation_safety": ({"rule": "elicitation-sensitive", "message": "Elicitation requests sensitive data"}, ["scaffold", "task_execution", "review"]),
        "sampling_retry": ({"rule": "sampling-retry", "message": "Sampling retry policy is missing"}, ["task_execution", "review"]),
        "tool_result_schema": ({"rule": "tool-result", "message": "Tool result does not match outputSchema"}, ["scaffold", "task_execution", "completion"]),
        "files_spec": ({"rule": "files-spec", "message": "Files spec migration requires resource_link"}, ["discovery", "scaffold", "review"]),
    }

    for expected, (diagnostic, expected_stages) in cases.items():
        evidence = normalize_quality_evidence(diagnostic)
        assert evidence["category"] == expected
        assert evidence["scope"] == "mcp_baseline"
        assert evidence["reuse_stages"] == expected_stages
        assert evidence["diagnostic"] == diagnostic


def test_unmatched_findings_remain_app_specific() -> None:
    diagnostic = {"rule": "figma-layer-name", "message": "Layer name is too long"}
    evidence = normalize_quality_evidence(diagnostic)

    assert evidence == {
        "category": "app_specific",
        "scope": "app_specific",
        "reuse_stages": ["review"],
        "diagnostic": diagnostic,
    }
