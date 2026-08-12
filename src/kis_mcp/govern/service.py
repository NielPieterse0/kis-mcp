from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from .contracts import (
    AuthorityReference,
    GovernanceCapability,
    GovernanceEvidence,
    GovernanceFinding,
    OwnershipDeclaration,
    RepositoryGovernanceReport,
)
from .settings import GovernanceSettings

_PATH = re.compile(r"`([^`]+)`")
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*_[a-z0-9_]+$")

_CAPABILITIES = (
    GovernanceCapability("authority-order", "Authority order", "Validate the declared repository authority chain."),
    GovernanceCapability("documentation-ownership", "Documentation ownership", "Parse canonical documentation ownership declarations."),
    GovernanceCapability("owner-reference-integrity", "Owner reference integrity", "Report missing concrete canonical-owner documents."),
    GovernanceCapability("duplicate-owner", "Duplicate owner", "Detect one normalized topic declared with conflicting canonical owners."),
    GovernanceCapability("duplicate-current-fact", "Duplicate current fact", "Detect exact long-form current facts duplicated across canonical owner documents."),
    GovernanceCapability("current-implementation-drift", "Current implementation drift", "Compare exact current-operation claims with supplied implementation identifiers."),
)


class GovernanceService:
    def __init__(self, settings: GovernanceSettings) -> None:
        self.settings = settings

    def list_capabilities(self) -> tuple[GovernanceCapability, ...]:
        enabled = set(self.settings.enabled_rules)
        return tuple(item for item in _CAPABILITIES if item.rule_id in enabled)

    def inspect(
        self,
        evidence: GovernanceEvidence,
        *,
        rule_ids: tuple[str, ...] | None = None,
    ) -> RepositoryGovernanceReport:
        selected = self._selected_rules(rule_ids)
        authority = _authority_order(evidence.agents_text or "")
        ownership = _ownership(evidence.agents_text or "")
        findings: list[GovernanceFinding] = []
        unknowns: list[str] = []

        if "authority-order" in selected and not authority:
            findings.append(_finding("authority-order", "error", "Repository authority order is missing", "AGENTS.md", "No ordered authority references were parsed from the `Authority order` section.", ("AGENTS.md:## Authority order",), "Declare one ordered authority chain in AGENTS.md."))
        if "documentation-ownership" in selected and not ownership:
            findings.append(_finding("documentation-ownership", "warning", "Documentation ownership table is missing", "AGENTS.md", "No documentation ownership declarations were parsed.", ("AGENTS.md:## Documentation ownership and routing",), "Declare one canonical owner for each governed information class."))
        if "owner-reference-integrity" in selected:
            findings.extend(self._missing_owner_findings(evidence, authority, ownership))
        if "duplicate-owner" in selected:
            findings.extend(_duplicate_owner_findings(ownership))
        if "duplicate-current-fact" in selected:
            findings.extend(self._duplicate_fact_findings(evidence, ownership))
        if "current-implementation-drift" in selected:
            drift, drift_unknown = self._implementation_drift(evidence, ownership)
            findings.extend(drift)
            unknowns.extend(drift_unknown)

        bounded = findings[: self.settings.max_findings]
        return RepositoryGovernanceReport(
            project=evidence.project,
            authority_order=authority[: self.settings.max_authority_documents],
            ownership=ownership[: self.settings.max_authority_documents],
            findings=tuple(bounded),
            unknowns=tuple(sorted(set(unknowns))),
            truncated=len(findings) > len(bounded)
            or len(authority) > self.settings.max_authority_documents
            or len(ownership) > self.settings.max_authority_documents,
        )

    def describe_finding(self, evidence: GovernanceEvidence, finding_id: str) -> GovernanceFinding:
        if not isinstance(finding_id, str) or not finding_id.strip():
            raise ValueError("finding_id must be a non-empty string")
        for finding in self.inspect(evidence).findings:
            if finding.finding_id == finding_id:
                return finding
        raise KeyError(f"Unknown governance finding: {finding_id}")

    def _selected_rules(self, rule_ids: tuple[str, ...] | None) -> frozenset[str]:
        enabled = frozenset(self.settings.enabled_rules)
        if rule_ids is None:
            return enabled
        if not rule_ids or any(not isinstance(item, str) or not item for item in rule_ids):
            raise ValueError("rule_ids must be a non-empty tuple of strings when supplied")
        requested = frozenset(rule_ids)
        unknown = requested - enabled
        if unknown:
            raise ValueError(f"Governance rule is not enabled: {', '.join(sorted(unknown))}")
        return requested

    def _missing_owner_findings(
        self,
        evidence: GovernanceEvidence,
        authority: tuple[AuthorityReference, ...],
        ownership: tuple[OwnershipDeclaration, ...],
    ) -> list[GovernanceFinding]:
        referenced = {item.path for item in authority if _is_concrete_path(item.path)}
        referenced.update(item.owner for item in ownership if _is_concrete_path(item.owner))
        missing = set(evidence.missing_paths)
        return [
            _finding(
                "owner-reference-integrity", "error", "Canonical authority reference is missing", path,
                f"The declared canonical path `{path}` was not available in bounded repository evidence.",
                (f"AGENTS.md declares `{path}`", f"missing:{path}"),
                "Restore the declared owner or update AGENTS.md to the actual canonical owner.",
            )
            for path in sorted(referenced & missing)
        ]

    def _duplicate_fact_findings(
        self,
        evidence: GovernanceEvidence,
        ownership: tuple[OwnershipDeclaration, ...],
    ) -> list[GovernanceFinding]:
        owner_paths = {item.owner for item in ownership if _is_concrete_path(item.owner)}
        paragraphs: dict[str, list[str]] = defaultdict(list)
        for path, text in evidence.documents:
            if path not in owner_paths:
                continue
            for paragraph in _paragraphs(text, self.settings.min_duplicate_paragraph_chars):
                paragraphs[_normalize_paragraph(paragraph)].append(path)
        findings: list[GovernanceFinding] = []
        for normalized, paths in sorted(paragraphs.items()):
            unique = sorted(set(paths))
            if len(unique) < 2:
                continue
            findings.append(
                _finding(
                    "duplicate-current-fact", "warning", "Long-form fact is duplicated across canonical owners", unique[0],
                    f"The same normalized paragraph appears in {', '.join(unique)}.",
                    tuple(f"{path}:{normalized[:120]}" for path in unique),
                    "Keep the governed fact in one canonical owner and replace other copies with a scoped summary or reference.",
                    confidence="medium",
                )
            )
        return findings

    def _implementation_drift(
        self,
        evidence: GovernanceEvidence,
        ownership: tuple[OwnershipDeclaration, ...],
    ) -> tuple[list[GovernanceFinding], list[str]]:
        if evidence.implementation_identifiers is None:
            return [], ["CURRENT_IMPLEMENTATION_IDENTIFIERS_UNAVAILABLE"]
        current_owner = _current_truth_owner(ownership)
        if current_owner is None:
            return [], ["CURRENT_IMPLEMENTATION_OWNER_UNDECLARED"]
        documents = dict(evidence.documents)
        text = documents.get(current_owner)
        if text is None:
            return [], [f"CURRENT_IMPLEMENTATION_OWNER_UNREADABLE:{current_owner}"]
        section = _section(text, "Current implementation boundary")
        claims = sorted({value for value in _PATH.findall(section) if _IDENTIFIER.fullmatch(value)})
        missing = [value for value in claims if value not in evidence.implementation_identifiers]
        return [
            _finding(
                "current-implementation-drift", "warning", "Current implementation claim lacks implementation evidence", current_owner,
                f"`{identifier}` is claimed in the current implementation boundary but is absent from supplied implementation identifiers.",
                (f"{current_owner}:`{identifier}`", "implementation-identifiers:absent"),
                "Reconcile the current specification with implementation evidence; update the canonical owner or restore the implementation.",
                confidence="medium",
            )
            for identifier in missing
        ], []


def _authority_order(text: str) -> tuple[AuthorityReference, ...]:
    section = _section(text, "Authority order")
    items: list[AuthorityReference] = []
    for line in section.splitlines():
        match = re.match(r"\s*(\d+)\.\s+(.*)", line)
        if not match:
            continue
        refs = _PATH.findall(match.group(2))
        if refs:
            items.append(AuthorityReference(int(match.group(1)), refs[0], _strip_markdown(match.group(2))))
    return tuple(sorted(items, key=lambda item: item.order))


def _ownership(text: str) -> tuple[OwnershipDeclaration, ...]:
    section = _section(text, "Documentation ownership and routing")
    rows: list[OwnershipDeclaration] = []
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0].casefold() == "information" or set(cells[0]) <= {"-", ":"}:
            continue
        refs = _PATH.findall(cells[1])
        owner = refs[0] if refs else _strip_markdown(cells[1])
        if cells[0] and owner:
            rows.append(OwnershipDeclaration(_strip_markdown(cells[0]), owner))
    return tuple(rows)


def _duplicate_owner_findings(ownership: tuple[OwnershipDeclaration, ...]) -> list[GovernanceFinding]:
    grouped: dict[str, list[OwnershipDeclaration]] = defaultdict(list)
    for item in ownership:
        grouped[_normalize_paragraph(item.topic)].append(item)
    findings: list[GovernanceFinding] = []
    for declarations in grouped.values():
        owners = sorted({item.owner for item in declarations})
        if len(owners) < 2:
            continue
        findings.append(_finding(
            "duplicate-owner", "error", "One information class has conflicting canonical owners", "AGENTS.md",
            f"`{declarations[0].topic}` maps to multiple owners: {', '.join(owners)}.",
            tuple(f"AGENTS.md:{item.topic}->{item.owner}" for item in declarations),
            "Choose one canonical owner and make all other documents reference it.",
        ))
    return findings


def _current_truth_owner(ownership: tuple[OwnershipDeclaration, ...]) -> str | None:
    for item in ownership:
        topic = item.topic.casefold()
        if "current implemented product architecture" in topic or "current product" in topic:
            return item.owner
    return None


def _section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start: int | None = None
    wanted = heading.casefold()
    collected: list[str] = []
    for index, line in enumerate(lines):
        if line.startswith("## ") and line[3:].strip().casefold() == wanted:
            start = index + 1
            break
    if start is None:
        return ""
    for line in lines[start:]:
        if line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected)


def _paragraphs(text: str, minimum: int) -> tuple[str, ...]:
    paragraphs: list[str] = []
    current: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            if current:
                paragraphs.append(" ".join(current)); current = []
            continue
        if in_fence or stripped.startswith("|") or stripped.startswith("#"):
            continue
        if not stripped:
            if current:
                paragraphs.append(" ".join(current)); current = []
            continue
        current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))
    return tuple(item for item in paragraphs if len(_normalize_paragraph(item)) >= minimum and not _boilerplate(item))


def _boilerplate(value: str) -> bool:
    folded = value.casefold()
    return (
        "authority boundary" in folded
        or folded.startswith("this document owns")
        or folded.startswith("this document is the canonical owner")
    )


def _normalize_paragraph(value: str) -> str:
    return " ".join(_strip_markdown(value).casefold().split())


def _strip_markdown(value: str) -> str:
    return value.replace("**", "").replace("`", "").strip()


def _is_concrete_path(value: str) -> bool:
    return bool(value) and not any(token in value for token in ("*", "<", ">", "$")) and ("/" in value or "." in value)


def _finding(
    rule_id: str, severity: str, title: str, path: str | None, observation: str,
    evidence: tuple[str, ...], remediation: str, *, confidence: str = "high",
) -> GovernanceFinding:
    seed = "|".join((rule_id, path or "", observation, *evidence))
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return GovernanceFinding(
        finding_id=f"gov-{rule_id}-{digest}", rule_id=rule_id, severity=severity,
        title=title, path=path, observation=observation, evidence=evidence,
        remediation=remediation, confidence=confidence,
    )


__all__ = ["GovernanceService"]
