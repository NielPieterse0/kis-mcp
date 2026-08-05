from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ReviewBackend(Protocol):
    name: str

    def available(self) -> bool: ...

    def review(self, project_path: Path, prompt: str) -> str: ...


class EvidenceCollector(Protocol):
    def collect(self, path: Path) -> str: ...


__all__ = ["EvidenceCollector", "ReviewBackend"]
