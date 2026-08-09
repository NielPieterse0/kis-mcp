from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..evidence import EvidenceStore as SharedEvidenceStore
from ..evidence import EvidenceWriteDisposition
from .reviews import (
    ReviewArtifact,
    ReviewArtifactKind,
    ReviewEvidenceManifest,
)


@dataclass(frozen=True, slots=True)
class EvidenceWriteResult:
    kind: ReviewArtifactKind
    path: str
    disposition: EvidenceWriteDisposition
    sha256: str
    previous_sha256: str | None = None

    def to_json_dict(self) -> dict[str, str | None]:
        return {
            "kind": self.kind.value,
            "path": self.path,
            "disposition": self.disposition.value,
            "sha256": self.sha256,
            "previous_sha256": self.previous_sha256,
        }


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _content_bytes(content: str | bytes) -> bytes:
    if isinstance(content, str):
        return content.encode("utf-8")
    if isinstance(content, bytes):
        return content
    raise ValueError("evidence content must be text or bytes")


class ReviewEvidenceStore:
    def __init__(
        self,
        repository_root: Path,
        *,
        max_file_bytes: int = 1_048_576,
        max_total_bytes: int = 4_194_304,
    ) -> None:
        if isinstance(max_file_bytes, bool) or max_file_bytes <= 0:
            raise ValueError("max_file_bytes must be a positive integer")
        if isinstance(max_total_bytes, bool) or max_total_bytes <= 0:
            raise ValueError("max_total_bytes must be a positive integer")
        if max_total_bytes < max_file_bytes:
            raise ValueError("max_total_bytes must be at least max_file_bytes")
        self.repository_root = repository_root.resolve()
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self._shared_store = SharedEvidenceStore(
            self.repository_root,
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
            replace_fn=lambda source, destination: os.replace(source, destination),
        )

    @staticmethod
    def _artifact(
        manifest: ReviewEvidenceManifest,
        kind: ReviewArtifactKind,
    ) -> ReviewArtifact:
        if not isinstance(manifest, ReviewEvidenceManifest):
            raise ValueError("manifest must be ReviewEvidenceManifest")
        if not isinstance(kind, ReviewArtifactKind):
            raise ValueError("kind must be ReviewArtifactKind")
        for artifact in manifest.artifacts:
            if artifact.kind is kind:
                return artifact
        raise ValueError(f"manifest does not include {kind.value}")

    def _target(self, artifact: ReviewArtifact) -> Path:
        target = (self.repository_root / Path(artifact.path)).resolve(strict=False)
        try:
            target.relative_to(self.repository_root)
        except ValueError as exc:
            raise ValueError("evidence path escapes repository root") from exc
        return target

    def _review_total(self, manifest: ReviewEvidenceManifest) -> int:
        total = 0
        for artifact in manifest.artifacts:
            target = self._target(artifact)
            if target.is_file():
                total += target.stat().st_size
        return total

    def _preflight(
        self,
        manifest: ReviewEvidenceManifest,
        kind: ReviewArtifactKind,
        content: bytes,
        *,
        expected_sha256: str | None,
    ) -> EvidenceWriteResult:
        artifact = self._artifact(manifest, kind)
        if len(content) > self.max_file_bytes:
            raise ValueError("evidence content exceeds max_file_bytes")
        target = self._target(artifact)
        new_hash = _digest(content)
        if not target.is_file():
            current_size = self._review_total(manifest)
            if current_size + len(content) > self.max_total_bytes:
                raise ValueError("evidence bundle exceeds max_total_bytes")
            return EvidenceWriteResult(
                kind=kind,
                path=artifact.path,
                disposition=EvidenceWriteDisposition.CREATED,
                sha256=new_hash,
            )
        previous = target.read_bytes()
        previous_hash = _digest(previous)
        if previous_hash == new_hash:
            return EvidenceWriteResult(
                kind=kind,
                path=artifact.path,
                disposition=EvidenceWriteDisposition.UNCHANGED,
                sha256=new_hash,
                previous_sha256=previous_hash,
            )
        if expected_sha256 != previous_hash:
            return EvidenceWriteResult(
                kind=kind,
                path=artifact.path,
                disposition=EvidenceWriteDisposition.CONFLICT,
                sha256=new_hash,
                previous_sha256=previous_hash,
            )
        projected_total = self._review_total(manifest) - len(previous) + len(content)
        if projected_total > self.max_total_bytes:
            raise ValueError("evidence bundle exceeds max_total_bytes")
        return EvidenceWriteResult(
            kind=kind,
            path=artifact.path,
            disposition=EvidenceWriteDisposition.UPDATED,
            sha256=new_hash,
            previous_sha256=previous_hash,
        )

    def write_artifact(
        self,
        manifest: ReviewEvidenceManifest,
        kind: ReviewArtifactKind,
        content: str | bytes,
        *,
        expected_sha256: str | None = None,
    ) -> EvidenceWriteResult:
        payload = _content_bytes(content)
        result = self._preflight(
            manifest,
            kind,
            payload,
            expected_sha256=expected_sha256,
        )
        if result.disposition in {
            EvidenceWriteDisposition.UNCHANGED,
            EvidenceWriteDisposition.CONFLICT,
        }:
            return result
        artifact = self._artifact(manifest, kind)
        shared = self._shared_store.write_bytes(
            artifact.path,
            payload,
            expected_sha256=expected_sha256,
        )
        if shared.disposition is not result.disposition:
            raise RuntimeError("shared evidence preflight diverged from review evidence contract")
        return EvidenceWriteResult(
            kind=kind,
            path=artifact.path,
            disposition=shared.disposition,
            sha256=shared.sha256,
            previous_sha256=shared.previous_sha256,
        )

    def read_artifact(
        self,
        manifest: ReviewEvidenceManifest,
        kind: ReviewArtifactKind,
    ) -> bytes:
        artifact = self._artifact(manifest, kind)
        try:
            return self._shared_store.read_bytes(artifact.path)
        except ValueError as exc:
            raise ValueError("stored evidence exceeds max_file_bytes") from exc

    def write_bundle(
        self,
        manifest: ReviewEvidenceManifest,
        contents: Mapping[ReviewArtifactKind, str | bytes],
        *,
        expected_hashes: Mapping[ReviewArtifactKind, str] | None = None,
    ) -> dict[ReviewArtifactKind, EvidenceWriteResult]:
        if not contents:
            raise ValueError("contents must not be empty")
        normalized = {kind: _content_bytes(value) for kind, value in contents.items()}
        if sum(len(value) for value in normalized.values()) > self.max_total_bytes:
            raise ValueError("evidence bundle exceeds max_total_bytes")
        expected = dict(expected_hashes or {})
        preflight = {
            kind: self._preflight(
                manifest,
                kind,
                content,
                expected_sha256=expected.get(kind),
            )
            for kind, content in normalized.items()
        }
        if any(
            result.disposition is EvidenceWriteDisposition.CONFLICT
            for result in preflight.values()
        ):
            return {
                kind: (
                    result
                    if result.disposition is EvidenceWriteDisposition.CONFLICT
                    else EvidenceWriteResult(
                        kind=kind,
                        path=result.path,
                        disposition=EvidenceWriteDisposition.NOT_WRITTEN,
                        sha256=result.sha256,
                        previous_sha256=result.previous_sha256,
                    )
                )
                for kind, result in preflight.items()
            }
        projected_total = self._review_total(manifest)
        for kind, result in preflight.items():
            if result.disposition is EvidenceWriteDisposition.CREATED:
                projected_total += len(normalized[kind])
            elif result.disposition is EvidenceWriteDisposition.UPDATED:
                target = self._target(self._artifact(manifest, kind))
                projected_total -= target.stat().st_size
                projected_total += len(normalized[kind])
        if projected_total > self.max_total_bytes:
            raise ValueError("evidence bundle exceeds max_total_bytes")
        return {
            kind: self.write_artifact(
                manifest,
                kind,
                content,
                expected_sha256=expected.get(kind),
            )
            for kind, content in normalized.items()
        }


__all__ = [
    "EvidenceWriteDisposition",
    "EvidenceWriteResult",
    "ReviewEvidenceStore",
]
