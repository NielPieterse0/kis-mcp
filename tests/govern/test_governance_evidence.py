from __future__ import annotations

from types import SimpleNamespace

from kis_mcp.discover.errors import DiscoverError
from kis_mcp.govern.evidence import GovernanceEvidenceCollector
from kis_mcp.govern.settings import GovernanceSettings


class _ReadAuthority:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = files
        self.reads: list[str] = []

    def resolve_project(self, value: str):
        return SimpleNamespace(canonical_path=value)

    def read_relative_text(self, project: str, label: str, *, max_bytes: int):
        self.reads.append(label)
        if label not in self.files:
            raise DiscoverError(
                code="DISCOVER_FILE_NOT_FOUND",
                message="missing",
                reason="missing",
            )
        return SimpleNamespace(content=self.files[label])


def _settings() -> GovernanceSettings:
    return GovernanceSettings(
        enabled=True,
        max_authority_documents=8,
        max_file_bytes=10000,
        max_findings=20,
        min_duplicate_paragraph_chars=80,
        enabled_rules=("authority-order",),
    )


def test_collector_reads_only_bounded_concrete_authority_documents() -> None:
    agents = """## Authority order
1. `AGENTS.md`
2. `SPEC.md`
3. `docs/TRUST-MODEL.md`

## Documentation ownership and routing
| Information | Canonical owner |
|---|---|
| Module docs | the applicable `docs/*-MODULE-PRODUCT-SPEC.md` |
| Runtime state | `C:\\Projects\\.kis-mcp` |
"""
    reader = _ReadAuthority({"AGENTS.md": agents, "SPEC.md": "spec"})
    collector = GovernanceEvidenceCollector(
        read_authority=reader, settings=_settings(), identifiers_provider=lambda _path: {"tool_one"}
    )
    evidence = collector.collect(r"C:\Projects\demo")

    assert reader.reads == ["AGENTS.md", "SPEC.md", "docs/TRUST-MODEL.md"]
    assert evidence.missing_paths == ("docs/TRUST-MODEL.md",)
    assert dict(evidence.documents)["SPEC.md"] == "spec"
    assert evidence.implementation_identifiers == frozenset({"tool_one"})
    assert all("*" not in path for path, _text in evidence.documents)


def test_missing_agents_is_recorded_without_broad_repository_scan() -> None:
    reader = _ReadAuthority({})
    evidence = GovernanceEvidenceCollector(
        read_authority=reader, settings=_settings()
    ).collect(r"C:\Projects\demo")

    assert reader.reads == ["AGENTS.md"]
    assert evidence.agents_text is None
    assert evidence.missing_paths == ("AGENTS.md",)
    assert evidence.documents == ()
