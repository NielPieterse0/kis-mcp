from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QualifiedProfile:
    alias: str
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    reasoning_budget: int
    enable_thinking: bool
    authoritative: bool = True


@dataclass(frozen=True, slots=True)
class ReviewerRoute:
    review_type: str
    primary: str
    backup: str
    projector: str
    fence: str


PROFILES: dict[str, QualifiedProfile] = {
    "lightning": QualifiedProfile(
        "lightning", "nvidia/nemotron-3.5-lightning-30b-a3b", 0.0, 1.0, 16384, 0, False
    ),
    "super": QualifiedProfile(
        "super", "nvidia/nemotron-3-super-120b-a12b", 0.0, 1.0, 16384, 0, False
    ),
    "ultra": QualifiedProfile(
        "ultra", "nvidia/nemotron-3-ultra-550b-a55b", 1.0, 0.95, 16384, 16384, True
    ),
    "nano-text": QualifiedProfile(
        "nano-text", "nvidia/nemotron-3-nano-30b-a3b", 0.0, 1.0, 8192, 0, False
    ),
    "nano-omni": QualifiedProfile(
        "nano-omni",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        0.0,
        1.0,
        16384,
        16384,
        True,
    ),
    "gpt-oss-20b": QualifiedProfile(
        "gpt-oss-20b", "openai/gpt-oss-20b", 0.0, 1.0, 8192, 0, False, False
    ),
}


ROUTES: dict[str, ReviewerRoute] = {
    "code-quality": ReviewerRoute(
        "code-quality", "super", "ultra", "changed-code-tests", 
        "Require a demonstrated failure mode or stated requirement; exclude generic style advice and unproven assumptions."
    ),
    "safety-security": ReviewerRoute(
        "safety-security", "lightning", "ultra", "security-boundary",
        "Require a concrete exploit mechanism; do not flag safe parameterization, argv execution, or TLS without evidence."
    ),
    "architecture": ReviewerRoute(
        "architecture", "ultra", "super", "architecture-boundary",
        "Require an explicit boundary, dependency-direction, state-ownership, lifecycle, layering, or coupling violation."
    ),
    "performance": ReviewerRoute(
        "performance", "super", "lightning", "hot-path",
        "Require a concrete runtime or startup mechanism; do not invent benchmark impact or unrelated findings."
    ),
    "test-quality": ReviewerRoute(
        "test-quality", "super", "nano-text", "tests-and-behavior",
        "Findings must concern tests or missing coverage; production code is behavior evidence only."
    ),
    "documentation": ReviewerRoute(
        "documentation", "lightning", "super", "docs-authority",
        "Identify inaccurate, stale, missing, or contradictory documentation against implementation authority."
    ),
    "api-contracts": ReviewerRoute(
        "api-contracts", "nano-omni", "super", "literal-contract",
        "Compare success keys literally key-by-key, then error behavior separately; name both contract sides."
    ),
    "correctness-discovery": ReviewerRoute(
        "correctness-discovery", "lightning", "super", "changed-code-tests",
        "Discover only concrete correctness failures supported by source-bound evidence."
    ),
    "finding-adjudication": ReviewerRoute(
        "finding-adjudication", "super", "ultra", "candidate-adjudication",
        "Adjudicate every supplied candidate exactly once; do not silently drop candidate cardinality."
    ),
    "plan-review": ReviewerRoute(
        "plan-review", "super", "nano-omni", "authority-plan",
        "Check authority, constraints, dependency order, verification, and explicit failure boundaries."
    ),
    "tool-coordinator": ReviewerRoute(
        "tool-coordinator", "super", "lightning", "tool-contract",
        "Use only exact allowlisted tool names and schema-valid arguments; never repair malformed tool names."
    ),
    "cheap-synthesis-routing": ReviewerRoute(
        "cheap-synthesis-routing", "nano-text", "gpt-oss-20b", "bounded-synthesis",
        "Return only the bounded synthesis/routing contract; this lane is not authoritative review evidence."
    ),
}

PUBLIC_REVIEW_TYPES = frozenset({"code-quality", "safety-security", "architecture", "performance", "test-quality", "documentation", "api-contracts"})


def route_for(review_type: str) -> ReviewerRoute:
    return ROUTES[review_type]


def profile_for(alias: str) -> QualifiedProfile:
    return PROFILES[alias]


__all__ = ["PROFILES", "PUBLIC_REVIEW_TYPES", "ROUTES", "QualifiedProfile", "ReviewerRoute", "profile_for", "route_for"]
