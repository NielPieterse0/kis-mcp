from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from fastmcp import Client, FastMCP

from kis_mcp.desktop_commander import DesktopCommanderEffectResolver
from kis_mcp.line_endings import RepositoryLineEndingNormalizer
from kis_mcp.middleware import ThreeRuleMiddleware
from kis_mcp.policy import ThreeRulePolicy


def _git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / ".gitattributes").write_text(
        "* text=auto eol=lf\n*.cmd text eol=crlf\n*.png binary\n",
        encoding="utf-8",
        newline="\n",
    )
    return repo


def test_write_file_content_follows_git_eol_attribute(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    normalizer = RepositoryLineEndingNormalizer(project_boundary=tmp_path)

    normalized = normalizer.normalize(
        "write_file",
        {"path": str(repo / "README.md"), "content": "a\r\nb\r\n"},
    )

    assert normalized["content"] == "a\nb\n"


def test_crlf_exception_and_binary_path_are_not_forced_to_lf(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    normalizer = RepositoryLineEndingNormalizer(project_boundary=tmp_path)

    cmd = normalizer.normalize(
        "write_file",
        {"path": str(repo / "script.cmd"), "content": "a\nb\n"},
    )
    binary = normalizer.normalize(
        "write_file",
        {"path": str(repo / "image.png"), "content": "a\r\nb\r\n"},
    )

    assert cmd["content"] == "a\r\nb\r\n"
    assert binary["content"] == "a\r\nb\r\n"


def test_edit_block_normalizes_match_and_replacement_text(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    normalizer = RepositoryLineEndingNormalizer(project_boundary=tmp_path)

    normalized = normalizer.normalize(
        "edit_block",
        {
            "file_path": str(repo / "notes.md"),
            "old_string": "old\r\ntext\r\n",
            "new_string": "new\r\ntext\r\n",
        },
    )

    assert normalized["old_string"] == "old\ntext\n"
    assert normalized["new_string"] == "new\ntext\n"


def test_middleware_forwards_normalized_write_arguments(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    target = repo / "README.md"
    calls: list[str] = []
    server = FastMCP("line-ending-middleware-test")

    @server.tool
    def write_file(path: str, content: str, mode: str = "rewrite") -> str:
        calls.append(content)
        return path

    server.add_middleware(
        ThreeRuleMiddleware(
            resolver=DesktopCommanderEffectResolver(
                project_boundary=str(tmp_path),
                provider_state_file=str(tmp_path / "provider.json"),
            ),
            policy=ThreeRulePolicy(
                project_boundary=str(tmp_path),
                quarantine_root=str(tmp_path / "quarantine"),
            ),
            quarantine_paths=lambda _paths: [],
            text_normalizer=RepositoryLineEndingNormalizer(project_boundary=tmp_path),
        )
    )

    async def run() -> None:
        async with Client(server) as client:
            await client.call_tool(
                "write_file",
                {"path": str(target), "content": "a\r\nb\r\n", "mode": "rewrite"},
            )

    asyncio.run(run())
    assert calls == ["a\nb\n"]


def test_nested_gitattributes_override_is_resolved_by_git(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    nested = repo / "windows"
    nested.mkdir()
    (nested / ".gitattributes").write_text(
        "*.md text eol=crlf\n",
        encoding="utf-8",
        newline="\n",
    )
    normalizer = RepositoryLineEndingNormalizer(project_boundary=tmp_path)

    normalized = normalizer.normalize(
        "write_file",
        {"path": str(nested / "notes.md"), "content": "a\nb\n"},
    )

    assert normalized["content"] == "a\r\nb\r\n"


def test_non_git_target_is_left_unchanged(tmp_path: Path) -> None:
    target = tmp_path / "plain" / "notes.md"
    normalizer = RepositoryLineEndingNormalizer(project_boundary=tmp_path)
    content = "a\r\nb\r\n"

    normalized = normalizer.normalize(
        "write_file",
        {"path": str(target), "content": content},
    )

    assert normalized["content"] == content


def test_git_environment_overrides_do_not_redirect_attribute_lookup(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _git_repo(tmp_path)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "wrong.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "wrong-worktree"))
    normalizer = RepositoryLineEndingNormalizer(project_boundary=tmp_path)

    normalized = normalizer.normalize(
        "write_file",
        {"path": str(repo / "README.md"), "content": "a\r\nb\r\n"},
    )

    assert normalized["content"] == "a\nb\n"
