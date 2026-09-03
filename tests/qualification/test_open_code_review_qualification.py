import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[2] / "scripts" / "qualification" / "open-code-review" / "qualify.py"
spec = importlib.util.spec_from_file_location("ocr_qualification", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def payload(**runtime):
    return {
        "package": {"name": "@alibaba-group/open-code-review", "version": "1.11.2"},
        "runtime": runtime,
        "corpus": [{"id": "case-1", "source": "abc123", "category": "security"}],
    }


def test_blocked_runtime_is_not_adopted():
    result = module.decide(payload(executable=False, successful_reviews=0))
    assert result["decision"] == "not_adopted"
    assert result["product_integration_authorized"] is False
    assert result["metrics"]["status"] == "not_measurable"
    assert result["metrics"]["incremental_validated_findings"] is None


def test_blocked_runtime_cannot_fabricate_reviews():
    try:
        module.decide(payload(executable=False, successful_reviews=1))
    except ValueError as exc:
        assert "blocked runtime" in str(exc)
    else:
        raise AssertionError("blocked runtime accepted fabricated successful review")


def test_version_is_exactly_pinned():
    accepted = module.decide(
        payload(executable=True, successful_reviews=1, incremental_validated_findings=1)
    )
    assert accepted["decision"] == "adapter_candidate"

    for version in ("latest", "1.11.1", "1.11.3", "2.0.0"):
        value = payload(executable=True, successful_reviews=1, incremental_validated_findings=1)
        value["package"]["version"] = version
        try:
            module.decide(value)
        except ValueError as exc:
            assert "pinned" in str(exc)
        else:
            raise AssertionError(f"unpinned OCR version accepted: {version}")


def test_executable_runtime_without_incremental_findings_is_not_adopted():
    result = module.decide(
        payload(executable=True, successful_reviews=1, incremental_validated_findings=0)
    )
    assert result["decision"] == "not_adopted"
    assert result["product_integration_authorized"] is False
    assert result["metrics"]["status"] == "measured"
    assert result["metrics"]["incremental_validated_findings"] == 0


def test_blocked_runtime_rejects_even_zero_fabricated_incremental_metric():
    try:
        module.decide(
            payload(executable=False, successful_reviews=0, incremental_validated_findings=0)
        )
    except ValueError as exc:
        assert "blocked runtime" in str(exc)
    else:
        raise AssertionError("blocked runtime accepted a fabricated incremental metric")


def test_executable_runtime_without_successful_review_is_not_adopted():
    result = module.decide(
        payload(executable=True, successful_reviews=0, incremental_validated_findings=1)
    )
    assert result["decision"] == "not_adopted"
    assert result["product_integration_authorized"] is False
