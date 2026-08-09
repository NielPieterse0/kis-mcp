"""Bounded read-only repository discovery for kis-mcp."""


def discover_capability_contributions():
    """Load Discover capability descriptors lazily to preserve module boundaries."""
    from .platform import discover_capability_contributions as _contributions

    return _contributions()


__all__ = ["discover_capability_contributions"]
