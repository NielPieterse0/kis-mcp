from __future__ import annotations

from kis_mcp.models import DecisionKind, InvocationEffects
from kis_mcp.paths import PathValidationError
from kis_mcp.policy import ThreeRulePolicy


POLICY = ThreeRulePolicy(
    project_boundary=r"C:\Projects",
    quarantine_root=r"C:\Projects\.kis-mcp\quarantine",
)


def test_allows_write_inside_project_boundary() -> None:
    decision = POLICY.evaluate(
        InvocationEffects(write_paths=(r"C:\Projects\kis-mcp\README.md",))
    )
    assert decision.kind is DecisionKind.ALLOW


def test_blocks_prefix_collision_outside_boundary() -> None:
    decision = POLICY.evaluate(
        InvocationEffects(write_paths=(r"C:\Projects-old\artifact.txt",))
    )
    assert decision.kind is DecisionKind.BLOCK
    assert decision.rule_id == "HR-001"


def test_blocks_write_when_effective_link_target_is_outside(
    monkeypatch,
) -> None:
    def resolve(path: str, *, base: str, follow_final: bool) -> str:
        if path.endswith("linked.txt") and follow_final:
            return r"C:\Windows\linked.txt"
        return path

    monkeypatch.setattr("kis_mcp.policy.resolve_windows_effective_path", resolve)
    decision = POLICY.evaluate(
        InvocationEffects(write_paths=(r"C:\Projects\link\linked.txt",))
    )
    assert decision.kind is DecisionKind.BLOCK
    assert decision.rule_id == "HR-001"


def test_entry_mutation_resolves_parent_not_final_target(monkeypatch) -> None:
    calls: list[bool] = []

    def resolve(path: str, *, base: str, follow_final: bool) -> str:
        calls.append(follow_final)
        return path

    monkeypatch.setattr("kis_mcp.policy.resolve_windows_effective_path", resolve)
    decision = POLICY.evaluate(
        InvocationEffects(entry_paths=(r"C:\Projects\link-entry",))
    )
    assert decision.kind is DecisionKind.ALLOW
    assert calls == [False]


def test_unresolvable_write_path_is_not_mislabeled_hr001(monkeypatch) -> None:
    def fail(_path: str, *, base: str, follow_final: bool) -> str:
        raise PathValidationError("unresolved")

    monkeypatch.setattr("kis_mcp.policy.resolve_windows_effective_path", fail)
    decision = POLICY.evaluate(InvocationEffects(write_paths=("malformed",)))
    assert decision.kind is DecisionKind.ALLOW
    assert decision.rule_id is None


def test_unresolvable_delete_path_is_a_structural_error(monkeypatch) -> None:
    def fail(_path: str, *, base: str, follow_final: bool) -> str:
        raise PathValidationError("unresolved")

    monkeypatch.setattr("kis_mcp.policy.resolve_windows_effective_path", fail)
    decision = POLICY.evaluate(InvocationEffects(delete_paths=("malformed",)))
    assert decision.kind is DecisionKind.BLOCK
    assert decision.rule_id is None
    assert decision.code == "INVALID_INVOCATION_PATH"


def test_blocks_external_network_intent() -> None:
    decision = POLICY.evaluate(InvocationEffects(external_network=True))
    assert decision.kind is DecisionKind.BLOCK
    assert decision.rule_id == "HR-002"


def test_transforms_delete_inside_boundary_to_quarantine() -> None:
    decision = POLICY.evaluate(
        InvocationEffects(delete_paths=(r"C:\Projects\kis-mcp\obsolete.txt",))
    )
    assert decision.kind is DecisionKind.QUARANTINE
    assert decision.rule_id == "HR-003"


def test_blocks_unresolved_permanent_delete_intent_under_hr003() -> None:
    decision = POLICY.evaluate(InvocationEffects(unresolved_delete=True))
    assert decision.kind is DecisionKind.BLOCK
    assert decision.rule_id == "HR-003"
    assert decision.code == "HR-003_QUARANTINE_REQUIRED"


def test_blocks_delete_outside_boundary_as_hr001() -> None:
    decision = POLICY.evaluate(
        InvocationEffects(delete_paths=(r"C:\Windows\system32\artifact.txt",))
    )
    assert decision.kind is DecisionKind.BLOCK
    assert decision.rule_id == "HR-001"


def test_allows_invocation_without_prohibited_intent() -> None:
    decision = POLICY.evaluate(InvocationEffects())
    assert decision.kind is DecisionKind.ALLOW


def test_policy_has_no_fourth_decision_kind() -> None:
    assert {item.value for item in DecisionKind} == {"allow", "block", "quarantine"}
