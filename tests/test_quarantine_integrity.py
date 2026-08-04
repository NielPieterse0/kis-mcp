from __future__ import annotations

import io
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from kis_mcp.quarantine_integrity import (
    PayloadHashLimitError,
    PayloadHashLimits,
    payload_sha256,
)


def _limits(**overrides: object) -> PayloadHashLimits:
    values: dict[str, object] = {
        "max_entries": 100,
        "max_bytes": 1_000,
        "max_depth": 20,
        "max_duration_seconds": 5.0,
    }
    values.update(overrides)
    return PayloadHashLimits(**values)


def test_payload_hash_enforces_entry_limit(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    (root / "one.txt").write_text("one", encoding="utf-8")
    (root / "two.txt").write_text("two", encoding="utf-8")

    with pytest.raises(PayloadHashLimitError) as captured:
        payload_sha256(root, limits=_limits(max_entries=2))

    assert captured.value.code == "QUARANTINE_INTEGRITY_ENTRY_LIMIT"
    assert captured.value.entries == 3


def test_payload_hash_enforces_byte_limit(tmp_path: Path) -> None:
    target = tmp_path / "payload.bin"
    target.write_bytes(b"12345")

    with pytest.raises(PayloadHashLimitError) as captured:
        payload_sha256(target, limits=_limits(max_bytes=4))

    assert captured.value.code == "QUARANTINE_INTEGRITY_BYTE_LIMIT"
    assert captured.value.bytes_read == 5


def test_payload_hash_enforces_depth_limit(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    child = root / "child"
    child.mkdir(parents=True)
    (child / "value.txt").write_text("value", encoding="utf-8")

    with pytest.raises(PayloadHashLimitError) as captured:
        payload_sha256(root, limits=_limits(max_depth=1))

    assert captured.value.code == "QUARANTINE_INTEGRITY_DEPTH_LIMIT"
    assert captured.value.depth == 2


def test_payload_hash_enforces_duration_limit(tmp_path: Path) -> None:
    target = tmp_path / "payload.bin"
    target.write_bytes(b"data")
    calls = 0

    def clock() -> float:
        nonlocal calls
        calls += 1
        return 0.0 if calls == 1 else 2.0

    with pytest.raises(PayloadHashLimitError) as captured:
        payload_sha256(
            target,
            limits=_limits(max_duration_seconds=1.0),
            clock=clock,
        )

    assert captured.value.code == "QUARANTINE_INTEGRITY_DURATION_LIMIT"


def test_payload_hash_uses_iterative_traversal_for_deep_trees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeEntry:
        def __init__(self, value: int) -> None:
            self.name = str(value)
            self.path = str(value)

    class FakeScanner:
        def __init__(self, entries: list[FakeEntry]) -> None:
            self._entries = entries

        def __enter__(self) -> FakeScanner:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self):
            return iter(self._entries)

    def fake_lstat(path: os.PathLike[str] | str) -> SimpleNamespace:
        depth = int(Path(path).name)
        mode = stat.S_IFREG if depth == 1_500 else stat.S_IFDIR
        return SimpleNamespace(st_mode=mode, st_file_attributes=0)

    def fake_scandir(path: os.PathLike[str] | str) -> FakeScanner:
        depth = int(Path(path).name)
        return FakeScanner([FakeEntry(depth + 1)])

    monkeypatch.setattr(os, "lstat", fake_lstat)
    monkeypatch.setattr(os, "scandir", fake_scandir)
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: io.BytesIO(b"x"))

    digest = payload_sha256(
        Path("0"),
        limits=_limits(max_entries=2_000, max_depth=2_000),
    )

    assert len(digest) == 64
